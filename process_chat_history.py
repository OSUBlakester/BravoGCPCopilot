#!/usr/bin/env python3
"""
Process Chat History - AI Extraction Script

This script processes old chat history (> 7 days) to extract user preferences,
facts, and patterns. It updates the chat_derived_narrative document.

Usage:
    # Process all users
    python3 process_chat_history.py --all-users
    
    # Process specific user
    python3 process_chat_history.py --account-id ACCOUNT_ID --user-id USER_ID
    
    # Dry run (don't save changes)
    python3 process_chat_history.py --all-users --dry-run
"""

import asyncio
import argparse
import sys
import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from server
from server import (
    load_chat_history,
    load_chat_derived_narrative,
    save_chat_derived_narrative,
    CHAT_HISTORY_ACTIVE_DAYS,
    firestore_db,
    FIRESTORE_ACCOUNTS_COLLECTION,
    FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION,
    genai,
    GEMINI_PRIMARY_MODEL
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ChatHistoryProcessor:
    """Process chat history to extract user insights"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.model = genai.GenerativeModel(GEMINI_PRIMARY_MODEL)
    
    async def extract_user_insights(self, messages: List[Dict]) -> Dict:
        """
        Use Gemini to extract user preferences, facts, and patterns from chat messages
        """
        if not messages:
            return {
                "extracted_facts": [],
                "narrative_text": "",
                "answered_questions": {}
            }
        
        # Prepare messages for analysis
        message_texts = []
        for msg in messages:
            timestamp = msg.get("timestamp", "")
            response = msg.get("response", "")
            question = msg.get("question", "")
            if response:
                if question:
                    message_texts.append(f"[{timestamp}] Q: {question} | A: {response}")
                else:
                    message_texts.append(f"[{timestamp}] {response}")
        
        messages_str = "\n".join(message_texts)
        
        # Build extraction prompt
        prompt = f"""Analyze this AAC user's chat history and extract key information about them.

CHAT HISTORY:
{messages_str}

Extract the following in JSON format:
{{
  "preferences": [
    {{"topic": "food", "value": "pizza", "confidence": "high", "mention_count": 2}},
    {{"topic": "music", "value": "jazz", "confidence": "medium", "mention_count": 1}}
  ],
  "personal_facts": [
    {{"fact": "Lives in Boston", "confidence": "high"}},
    {{"fact": "Has a dog named Max", "confidence": "medium"}}
  ],
  "common_greetings": ["Good morning", "Hello"],
  "common_phrases": ["Thank you", "I need help"],
  "answered_questions": {{
    "favorite_color": "blue",
    "favorite_food": "pizza"
  }},
  "narrative": "Brief 2-3 sentence summary of what we learned about this user from their chat history."
}}

Focus on:
- Stated preferences (favorite X, likes/dislikes)
- Personal information (name, location, family, pets)
- Patterns in communication
- Facts that would help personalize their AAC experience

Return ONLY valid JSON, no other text."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            # Extract JSON from response
            response_text = response.text.strip()
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            extracted_data = json.loads(response_text)
            
            # Convert to our format
            facts = []
            
            # Add preferences as facts
            for pref in extracted_data.get("preferences", []):
                facts.append({
                    "fact": f"Prefers {pref['value']} for {pref['topic']}",
                    "source_message_id": messages[-1].get("id") if messages else None,
                    "confidence": pref.get("confidence", "medium"),
                    "category": "preference",
                    "first_mentioned": messages[0].get("timestamp") if messages else None,
                    "mention_count": pref.get("mention_count", 1)
                })
            
            # Add personal facts
            for fact_item in extracted_data.get("personal_facts", []):
                facts.append({
                    "fact": fact_item["fact"],
                    "source_message_id": messages[-1].get("id") if messages else None,
                    "confidence": fact_item.get("confidence", "medium"),
                    "category": "personal_info",
                    "first_mentioned": messages[0].get("timestamp") if messages else None,
                    "mention_count": 1
                })
            
            return {
                "extracted_facts": facts,
                "narrative_text": extracted_data.get("narrative", ""),
                "answered_questions": extracted_data.get("answered_questions", {}),
                "recent_greetings": extracted_data.get("common_greetings", [])[:5],
            }
            
        except Exception as e:
            logging.error(f"Error extracting insights: {e}", exc_info=True)
            return {
                "extracted_facts": [],
                "narrative_text": "",
                "answered_questions": {}
            }
    
    async def process_user(self, account_id: str, aac_user_id: str) -> Dict:
        """Process chat history for a single user"""
        logging.info(f"\n{'='*60}")
        logging.info(f"Processing user: {account_id}/{aac_user_id}")
        logging.info(f"{'='*60}")
        
        # Load chat history
        chat_history = await load_chat_history(account_id, aac_user_id)
        
        if not chat_history:
            logging.info("No chat history found")
            return {"status": "skipped", "reason": "no_history"}
        
        logging.info(f"Found {len(chat_history)} chat messages")
        
        # Separate active vs old messages
        cutoff_date = datetime.now() - timedelta(days=CHAT_HISTORY_ACTIVE_DAYS)
        
        old_messages = []
        active_messages = []
        
        for msg in chat_history:
            try:
                msg_date = datetime.fromisoformat(msg.get("timestamp", "2000-01-01T00:00:00"))
                if msg_date < cutoff_date:
                    old_messages.append(msg)
                else:
                    active_messages.append(msg)
            except:
                active_messages.append(msg)  # If can't parse, treat as active
        
        logging.info(f"Old messages (>{CHAT_HISTORY_ACTIVE_DAYS} days): {len(old_messages)}")
        logging.info(f"Active messages (<{CHAT_HISTORY_ACTIVE_DAYS} days): {len(active_messages)}")
        
        if not old_messages:
            logging.info("No old messages to process")
            return {"status": "skipped", "reason": "no_old_messages"}
        
        # Extract insights from old messages
        logging.info("Extracting insights from old messages...")
        insights = await self.extract_user_insights(old_messages)
        
        # Load existing narrative
        narrative = await load_chat_derived_narrative(account_id, aac_user_id)
        
        # Merge insights
        narrative["last_updated"] = datetime.now().isoformat()
        narrative["source_message_count"] = len(old_messages)
        
        # Merge facts (avoid duplicates)
        existing_facts = {f["fact"]: f for f in narrative.get("extracted_facts", [])}
        for new_fact in insights["extracted_facts"]:
            fact_text = new_fact["fact"]
            if fact_text in existing_facts:
                # Update mention count
                existing_facts[fact_text]["mention_count"] += new_fact.get("mention_count", 1)
            else:
                existing_facts[fact_text] = new_fact
        
        narrative["extracted_facts"] = list(existing_facts.values())
        
        # Update narrative text
        if insights["narrative_text"]:
            if narrative.get("narrative_text"):
                narrative["narrative_text"] += " " + insights["narrative_text"]
            else:
                narrative["narrative_text"] = insights["narrative_text"]
        
        # Update answered questions
        narrative["answered_questions"].update(insights.get("answered_questions", {}))
        
        # Update recent greetings
        if insights.get("recent_greetings"):
            narrative["recent_greetings"] = insights["recent_greetings"]
        
        logging.info(f"\nExtracted Insights:")
        logging.info(f"  Facts: {len(narrative['extracted_facts'])}")
        logging.info(f"  Answered questions: {len(narrative['answered_questions'])}")
        logging.info(f"  Narrative: {narrative['narrative_text'][:100]}...")
        
        if self.dry_run:
            logging.info("\n[DRY RUN] Would save narrative (not saving)")
        else:
            success = await save_chat_derived_narrative(account_id, aac_user_id, narrative)
            if success:
                logging.info("✅ Narrative saved successfully")
            else:
                logging.error("❌ Failed to save narrative")
                return {"status": "error", "reason": "save_failed"}
        
        return {
            "status": "success",
            "facts_extracted": len(narrative['extracted_facts']),
            "messages_processed": len(old_messages)
        }
    
    async def process_all_users(self):
        """Process all users in all accounts"""
        logging.info("Processing all users...")
        
        # Get all accounts
        accounts_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION)
        accounts = await asyncio.to_thread(accounts_ref.stream)
        
        total_processed = 0
        total_skipped = 0
        total_errors = 0
        
        for account_doc in accounts:
            account_id = account_doc.id
            
            # Get all users in this account
            users_ref = account_doc.reference.collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
            users = await asyncio.to_thread(users_ref.stream)
            
            for user_doc in users:
                aac_user_id = user_doc.id
                
                try:
                    result = await self.process_user(account_id, aac_user_id)
                    
                    if result["status"] == "success":
                        total_processed += 1
                    elif result["status"] == "skipped":
                        total_skipped += 1
                    else:
                        total_errors += 1
                        
                except Exception as e:
                    logging.error(f"Error processing {account_id}/{aac_user_id}: {e}", exc_info=True)
                    total_errors += 1
        
        logging.info(f"\n{'='*60}")
        logging.info(f"SUMMARY")
        logging.info(f"{'='*60}")
        logging.info(f"Processed: {total_processed}")
        logging.info(f"Skipped: {total_skipped}")
        logging.info(f"Errors: {total_errors}")

async def main():
    parser = argparse.ArgumentParser(
        description="Process chat history to extract user insights",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--all-users",
        action="store_true",
        help="Process all users in all accounts"
    )
    
    parser.add_argument(
        "--account-id",
        help="Specific account ID to process"
    )
    
    parser.add_argument(
        "--user-id",
        help="Specific user ID to process (requires --account-id)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't save changes, just show what would be done"
    )
    
    args = parser.parse_args()
    
    processor = ChatHistoryProcessor(dry_run=args.dry_run)
    
    if args.all_users:
        await processor.process_all_users()
    elif args.account_id and args.user_id:
        result = await processor.process_user(args.account_id, args.user_id)
        logging.info(f"\nResult: {result}")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
