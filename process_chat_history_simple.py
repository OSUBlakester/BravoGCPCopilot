#!/usr/bin/env python3
"""
Lightweight Chat History Processor

Processes chat history to extract user insights without full server dependencies.
Run this after server initialization to process historical chat data.
"""

import asyncio
import argparse
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from google.cloud import firestore
import google.generativeai as genai
import os

# Load config
from config import CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
FIRESTORE_ACCOUNTS_COLLECTION = "accounts"
FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION = "users"
CHAT_HISTORY_ACTIVE_DAYS = 7
GEMINI_PRIMARY_MODEL = os.environ.get("GEMINI_PRIMARY_MODEL", "models/gemini-2.5-flash")

# Initialize Firestore
firestore_db = firestore.Client(project=CONFIG.get('gcp_project_id'))

# Initialize Gemini with API key
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logging.error("GOOGLE_API_KEY environment variable not set")
    sys.exit(1)
genai.configure(api_key=GOOGLE_API_KEY)

DEFAULT_CHAT_DERIVED_NARRATIVE = {
    "last_updated": None,
    "source_message_count": 0,
    "extracted_facts": [],
    "narrative_text": "",
    "recent_greetings": [],
    "recent_jokes": [],
    "answered_questions": {}
}

async def load_chat_history(account_id: str, aac_user_id: str) -> List[Dict]:
    """Load chat history from Firestore"""
    full_path = f"{FIRESTORE_ACCOUNTS_COLLECTION}/{account_id}/{FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION}/{aac_user_id}/chat_history"
    collection_ref = firestore_db.collection(full_path)
    docs = await asyncio.to_thread(collection_ref.stream)
    
    entries = []
    for doc in docs:
        entry_data = doc.to_dict()
        if entry_data:
            entry_data['id'] = doc.id
            entries.append(entry_data)
    
    return sorted(entries, key=lambda x: x.get('timestamp', ''), reverse=False)

async def load_chat_derived_narrative(account_id: str, aac_user_id: str) -> Dict:
    """Load chat-derived narrative"""
    full_path = f"{FIRESTORE_ACCOUNTS_COLLECTION}/{account_id}/{FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION}/{aac_user_id}/info/chat_derived_narrative"
    doc_ref = firestore_db.document(full_path)
    doc = await asyncio.to_thread(doc_ref.get)
    
    if doc.exists:
        return doc.to_dict()
    return DEFAULT_CHAT_DERIVED_NARRATIVE.copy()

async def save_chat_derived_narrative(account_id: str, aac_user_id: str, narrative_data: Dict) -> bool:
    """Save chat-derived narrative"""
    full_path = f"{FIRESTORE_ACCOUNTS_COLLECTION}/{account_id}/{FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION}/{aac_user_id}/info/chat_derived_narrative"
    doc_ref = firestore_db.document(full_path)
    await asyncio.to_thread(doc_ref.set, narrative_data)
    return True

class ChatHistoryProcessor:
    """Process chat history to extract user insights"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.model = genai.GenerativeModel(GEMINI_PRIMARY_MODEL)
    
    async def extract_user_insights(self, messages: List[Dict]) -> Dict:
        """Use Gemini to extract user preferences, facts, and patterns from chat messages"""
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
        
        messages_str = "\n".join(message_texts[-100:])  # Last 100 messages max
        
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
        
        # Extract insights from ALL messages for initial run
        messages_to_analyze = chat_history if not old_messages else old_messages
        
        if not messages_to_analyze:
            logging.info("No messages to process")
            return {"status": "skipped", "reason": "no_messages_to_analyze"}
        
        # Extract insights
        logging.info("Extracting insights from messages...")
        insights = await self.extract_user_insights(messages_to_analyze)
        
        # Load existing narrative
        narrative = await load_chat_derived_narrative(account_id, aac_user_id)
        
        # Merge insights
        narrative["last_updated"] = datetime.now().isoformat()
        narrative["source_message_count"] = len(messages_to_analyze)
        
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
        narrative["narrative_text"] = insights.get("narrative_text", "")
        narrative["answered_questions"] = insights.get("answered_questions", {})
        narrative["recent_greetings"] = insights.get("recent_greetings", [])
        
        logging.info(f"\nExtracted Insights:")
        logging.info(f"  Facts: {len(narrative['extracted_facts'])}")
        logging.info(f"  Answered questions: {len(narrative['answered_questions'])}")
        logging.info(f"  Narrative: {narrative['narrative_text']}")
        
        if self.dry_run:
            logging.info("\n[DRY RUN] Would save narrative (not saving)")
            logging.info(f"\nNarrative data:\n{json.dumps(narrative, indent=2)}")
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
            "messages_processed": len(messages_to_analyze)
        }

async def main():
    parser = argparse.ArgumentParser(description="Process chat history to extract user insights")
    
    parser.add_argument("--account-id", required=True, help="Account ID to process")
    parser.add_argument("--user-id", required=True, help="User ID to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    
    args = parser.parse_args()
    
    processor = ChatHistoryProcessor(dry_run=args.dry_run)
    result = await processor.process_user(args.account_id, args.user_id)
    logging.info(f"\nResult: {result}")

if __name__ == "__main__":
    asyncio.run(main())
