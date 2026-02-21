"""
Jokes Database System
Manages jokes storage, retrieval, and auto-tagging for the Bravo AAC application.
"""

import logging
import json
import asyncio
import os
import csv
import io
import random
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from google.cloud import firestore
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

# Configure Gemini API at module load time
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    logging.info(f"🤖 Configuring Gemini API at module load...")
    genai.configure(api_key=api_key)
    logging.info(f"✅ Gemini API configured successfully at module load")
else:
    logging.warning(f"⚠️  GOOGLE_API_KEY not set - auto-tagging will use fallback")

# Predefined tag taxonomy
TAG_CATEGORIES = {
    "location": [
        "home", "office", "school", "beach", "park", "restaurant", 
        "hospital", "car", "airplane", "outdoor", "indoor", "work"
    ],
    "time": [
        "winter", "spring", "summer", "fall", "morning", "afternoon", 
        "evening", "night", "holiday", "christmas", "thanksgiving", 
        "halloween", "easter", "new_year", "birthday"
    ],
    "category": [
        "food", "animals", "technology", "dad_joke", "pun", "wordplay",
        "short", "long", "story", "one_liner", "riddle", "knock_knock"
    ],
    "maturity": [
        "clean", "nsfw"
    ]
}

class JokesDatabase:
    """Firestore-backed jokes database with auto-tagging."""
    
    def __init__(self):
        logging.info("🎯 Initializing JokesDatabase...")
        try:
            self.db = firestore.Client()
            logging.info("✅ Firestore client initialized successfully")
        except Exception as e:
            logging.error(f"❌ Failed to initialize Firestore client: {e}", exc_info=True)
            raise
        self.collection = "jokes"  # Global collection
        logging.info(f"✅ Using Firestore collection: {self.collection}")
        
    async def add_joke(self, text: str, tags: Optional[List[str]] = None, 
                       source: str = "manual", auto_tag: bool = True, summary: Optional[str] = None) -> Dict[str, Any]:
        """Add a joke to the database with optional auto-tagging and summary generation."""
        try:
            logging.info(f"📝 add_joke called with text: {text[:50]}... auto_tag={auto_tag}, manual_tags={tags}")
            
            # Handle auto-tagging
            if auto_tag:
                logging.info("🏷️ Auto-tagging enabled, generating tags...")
                auto_generated_tags = await self._auto_tag_joke(text)
                logging.info(f"🏷️ Generated tags: {auto_generated_tags}")
                
                # Merge manual tags with auto-generated tags (remove duplicates)
                if tags:
                    combined_tags = list(set(tags + auto_generated_tags))
                    logging.info(f"🏷️ Merged manual + auto tags: {combined_tags}")
                    tags = combined_tags
                else:
                    tags = auto_generated_tags
            
            # Generate summary if not provided
            if not summary and auto_tag:
                logging.info("📝 Generating joke summary...")
                summary = await self._generate_joke_summary(text)
                logging.info(f"📝 Generated summary: {summary}")
            
            now = datetime.utcnow()
            joke_doc = {
                "text": text.strip(),
                "summary": summary or "Joke",  # Default fallback
                "tags": tags or [],
                "source": source,
                "enabled": True,
                "createdAt": now,
                "updatedAt": now,
                "use_count": 0
            }
            
            logging.info(f"💾 Preparing to save joke to Firestore...")
            
            # Add to Firestore (wrap in thread since Firestore client is synchronous)
            def _set_doc():
                logging.info(f"🔥 In thread: Adding document to collection '{self.collection}'")
                doc_ref = self.db.collection(self.collection).document()
                logging.info(f"🔥 In thread: Got doc_ref, calling set()...")
                doc_ref.set(joke_doc)
                logging.info(f"🔥 In thread: Document set successfully with ID: {doc_ref.id}")
                return doc_ref.id
            
            joke_id = await asyncio.to_thread(_set_doc)
            
            logging.info(f"✅ Successfully added joke with ID: {joke_id}")
            
            # Return JSON-serializable response (convert datetime to ISO format)
            return {
                "success": True,
                "joke_id": joke_id,
                "joke": {
                    "text": joke_doc["text"],
                    "summary": joke_doc["summary"],
                    "tags": joke_doc["tags"],
                    "source": joke_doc["source"],
                    "enabled": joke_doc["enabled"],
                    "createdAt": joke_doc["createdAt"].isoformat(),
                    "updatedAt": joke_doc["updatedAt"].isoformat(),
                    "use_count": joke_doc["use_count"]
                }
            }
        except Exception as e:
            logging.error(f"❌ Error adding joke: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def get_jokes_by_tags(self, location: Optional[str] = None, 
                               time_period: Optional[str] = None, 
                               limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get jokes matching location/time tags (prioritized), 
        fill with random jokes if needed.
        """
        try:
            def _fetch_tagged_jokes():
                # Start with enabled jokes only
                query = self.db.collection(self.collection).where("enabled", "==", True)
                
                # Build tag filter if provided
                required_tags = []
                if location:
                    required_tags.append(location)
                if time_period:
                    required_tags.append(time_period)
                
                # Fetch all enabled jokes
                docs = query.stream()
                all_jokes = []
                for doc in docs:
                    joke = {"id": doc.id}
                    joke_data = doc.to_dict()
                    
                    # Convert datetime objects to ISO format strings
                    if "createdAt" in joke_data and isinstance(joke_data["createdAt"], datetime):
                        joke_data["createdAt"] = joke_data["createdAt"].isoformat()
                    if "updatedAt" in joke_data and isinstance(joke_data["updatedAt"], datetime):
                        joke_data["updatedAt"] = joke_data["updatedAt"].isoformat()
                    
                    joke.update(joke_data)
                    all_jokes.append(joke)
                
                if not all_jokes:
                    return []
                
                # Prioritize jokes with matching tags
                if required_tags:
                    matching_jokes = [
                        joke for joke in all_jokes 
                        if any(tag in joke.get("tags", []) for tag in required_tags)
                    ]
                    
                    # If we have matching jokes, return them (up to limit)
                    if matching_jokes:
                        return matching_jokes[:limit]
                
                # Fallback: return random jokes
                import random
                return random.sample(all_jokes, min(limit, len(all_jokes)))
            
            return await asyncio.to_thread(_fetch_tagged_jokes)
        except Exception as e:
            logging.error(f"Error getting jokes: {e}")
            return []

    def _build_context_tags(self, location: str, people: str, activity: str) -> List[str]:
        """Build a list of context tags from current location, people, activity, and time."""
        def _tokenize(value: str) -> List[str]:
            return re.findall(r"[a-z0-9]+", value.lower()) if value else []

        context_tags = set()
        location_lower = (location or "").lower()
        people_lower = (people or "").lower()
        activity_lower = (activity or "").lower()

        # Add direct tokens from context
        for token in _tokenize(location_lower) + _tokenize(people_lower) + _tokenize(activity_lower):
            context_tags.add(token)

        # Map location keywords to known tags
        location_map = {
            "home": "home",
            "house": "home",
            "living": "home",
            "bedroom": "home",
            "school": "school",
            "class": "school",
            "office": "office",
            "work": "work",
            "park": "park",
            "beach": "beach",
            "restaurant": "restaurant",
            "cafe": "restaurant",
            "hospital": "hospital",
            "car": "car",
            "bus": "car",
            "truck": "car",
            "airport": "airplane",
            "plane": "airplane",
            "outside": "outdoor",
            "outdoor": "outdoor",
            "inside": "indoor",
            "indoor": "indoor"
        }
        for keyword, tag in location_map.items():
            if keyword in location_lower:
                context_tags.add(tag)

        # Map activity keywords to known tags
        activity_map = {
            "eat": "food",
            "eating": "food",
            "lunch": "food",
            "dinner": "food",
            "breakfast": "food",
            "snack": "food",
            "cook": "food",
            "bake": "food",
            "play": "games",
            "game": "games",
            "gaming": "games",
            "sports": "outdoor",
            "sport": "outdoor",
            "exercise": "outdoor",
            "walk": "outdoor",
            "movie": "indoor",
            "tv": "indoor",
            "show": "indoor",
            "computer": "technology",
            "phone": "technology",
            "tablet": "technology"
        }
        for keyword, tag in activity_map.items():
            if keyword in activity_lower:
                context_tags.add(tag)

        # Add time-of-year and time-of-day tags
        now = datetime.utcnow()
        month = now.month
        hour = now.hour

        if month in (12, 1, 2):
            context_tags.add("winter")
        elif month in (3, 4, 5):
            context_tags.add("spring")
        elif month in (6, 7, 8):
            context_tags.add("summer")
        else:
            context_tags.add("fall")

        if 5 <= hour < 12:
            context_tags.add("morning")
        elif 12 <= hour < 17:
            context_tags.add("afternoon")
        elif 17 <= hour < 21:
            context_tags.add("evening")
        else:
            context_tags.add("night")

        # Holiday tags (simple month-based heuristics)
        if month == 12:
            context_tags.update(["christmas", "holiday"])
        if month == 10:
            context_tags.update(["halloween", "holiday"])
        if month == 11:
            context_tags.update(["thanksgiving", "holiday"])
        if month == 1:
            context_tags.add("new_year")
        if month in (3, 4):
            context_tags.add("easter")

        return sorted(context_tags)

    async def get_contextual_jokes(self, location: str, people: str, activity: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return jokes using weighted random selection: 30% context-based, 70% random for variety."""
        try:
            context_tags = set(self._build_context_tags(location, people, activity))

            def _fetch_contextual_jokes():
                # PERFORMANCE: Fetch more than needed but not all jokes
                # Limit query to 100 jokes for faster retrieval (adjust if needed)
                query = self.db.collection(self.collection).where("enabled", "==", True).limit(100)
                docs = query.stream()

                all_jokes = []
                for doc in docs:
                    joke = {"id": doc.id}
                    joke_data = doc.to_dict()

                    if "createdAt" in joke_data and isinstance(joke_data["createdAt"], datetime):
                        joke_data["createdAt"] = joke_data["createdAt"].isoformat()
                    if "updatedAt" in joke_data and isinstance(joke_data["updatedAt"], datetime):
                        joke_data["updatedAt"] = joke_data["updatedAt"].isoformat()

                    joke.update(joke_data)
                    all_jokes.append(joke)

                if not all_jokes:
                    return []

                # Score each joke based on context tag matches
                if context_tags:
                    scored_jokes = []
                    for joke in all_jokes:
                        joke_tags = set(tag.lower() for tag in (joke.get("tags") or []))
                        match_count = len(context_tags.intersection(joke_tags))
                        scored_jokes.append({"joke": joke, "match_count": match_count})
                    
                    # Calculate weights: 30% from context matching, 70% from randomness
                    # Max match count determines normalization
                    max_matches = max((j["match_count"] for j in scored_jokes), default=0)
                    
                    # Assign weights: context_weight (0-0.3) + random_weight (0.7)
                    for item in scored_jokes:
                        if max_matches > 0:
                            context_weight = (item["match_count"] / max_matches) * 0.3
                        else:
                            context_weight = 0
                        random_weight = 0.7
                        item["weight"] = context_weight + random_weight
                    
                    # Normalize weights so they sum to 1.0
                    total_weight = sum(item["weight"] for item in scored_jokes)
                    if total_weight > 0:
                        for item in scored_jokes:
                            item["weight"] = item["weight"] / total_weight
                    
                    # Select jokes using weighted random sampling without replacement
                    selected = []
                    remaining_jokes = scored_jokes[:]
                    for _ in range(min(limit, len(remaining_jokes))):
                        if not remaining_jokes:
                            break
                        
                        # Weighted random selection
                        weights = [j["weight"] for j in remaining_jokes]
                        selected_item = random.choices(remaining_jokes, weights=weights, k=1)[0]
                        selected.append(selected_item["joke"])
                        remaining_jokes.remove(selected_item)
                        
                        # Recalculate weights for remaining jokes
                        if remaining_jokes:
                            total_weight = sum(j["weight"] for j in remaining_jokes)
                            if total_weight > 0:
                                for j in remaining_jokes:
                                    j["weight"] = j["weight"] / total_weight
                    
                    return selected
                
                # Fallback: if no context tags, return random selection
                return random.sample(all_jokes, min(limit, len(all_jokes)))

            return await asyncio.to_thread(_fetch_contextual_jokes)
        except Exception as e:
            logging.error(f"Error getting contextual jokes: {e}", exc_info=True)
            return []
    
    async def _auto_tag_joke(self, joke_text: str) -> List[str]:
        """Use LLM to automatically tag a joke with subject-based intelligence."""
        try:
            logging.info(f"🏷️ Starting auto-tagging for joke...")
            
            # Check if API is configured
            if not api_key:
                logging.warning("⚠️  GOOGLE_API_KEY not set. Using default tags.")
                return ["clean"]  # Default fallback
            
            prompt = f"""Analyze this joke and generate intelligent tags based on its subjects and context.

JOKE: "{joke_text}"

INSTRUCTIONS:
1. **Identify subjects**: What are the main subjects/topics in the joke? (e.g., animals, food, people, objects)
2. **Add subject tags**: Use the subject names as tags (e.g., "turkey", "ghost", "dog", "computer")
3. **Add context tags**: Also include relevant tags from these predefined categories:
   - Location: {', '.join([tag for tag in TAG_CATEGORIES['location'] if tag != 'home'])}
   - Time/Season: {', '.join(TAG_CATEGORIES['time'])}
   - Style: {', '.join(TAG_CATEGORIES['category'])}
   - Maturity: {', '.join(TAG_CATEGORIES['maturity'])} (REQUIRED - must include one)

EXAMPLES:
- "What do you get if you cross a turkey with a ghost? A poultry-geist!" 
  → ["turkey", "ghost", "animals", "halloween", "pun", "clean"]
  
- "Why did the coffee taste like dirt? Because it was ground just a few minutes ago."
  → ["coffee", "food", "wordplay", "dad_joke", "clean"]
  
- "I threw a boomerang months ago. Now I live in constant fear."
  → ["boomerang", "outdoor", "dad_joke", "clean"]

RULES:
- Include 4-8 tags total
- MUST include at least one maturity tag (clean or nsfw)
- Subject names should be lowercase, single words (e.g., "turkey" not "Turkey")
- DO NOT use "home" as a tag under any circumstances
- Return ONLY a JSON array: ["tag1", "tag2", "tag3", ...]
"""

            def _generate_tags():
                logging.info(f"🤖 In thread: Calling Gemini API to generate tags...")
                try:
                    model = genai.GenerativeModel("gemini-2.0-flash")
                    response = model.generate_content(prompt)
                    logging.info(f"🤖 In thread: Got response from Gemini")
                    
                    try:
                        tags = json.loads(response.text)
                        logging.info(f"🤖 In thread: Successfully parsed tags: {tags}")
                        return tags if isinstance(tags, list) else ["clean"]
                    except json.JSONDecodeError:
                        # Try to extract JSON from response text
                        import re
                        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
                        if json_match:
                            tags = json.loads(json_match.group())
                            logging.info(f"🤖 In thread: Extracted tags via regex: {tags}")
                            return tags if isinstance(tags, list) else ["clean"]
                        logging.info(f"🤖 In thread: Could not parse tags, using default")
                        return ["clean"]  # Default fallback
                except Exception as e:
                    logging.error(f"❌ Error calling Gemini API: {e}", exc_info=True)
                    return ["clean"]  # Default fallback
            
            return await asyncio.to_thread(_generate_tags)
                
        except Exception as e:
            logging.error(f"❌ Error auto-tagging joke: {e}", exc_info=True)
            return ["clean"]  # Default fallback
    
    async def _generate_joke_summary(self, joke_text: str) -> str:
        """Generate a short summary (5 words or less) for a joke using Gemini."""
        try:
            logging.info(f"🤖 Generating summary for joke: {joke_text[:50]}...")
            
            prompt = f"""Generate a very short summary for this joke suitable as a button label.

JOKE: "{joke_text}"

INSTRUCTIONS:
1. Create a summary with 5 words or less
2. Capture the main subject or punchline
3. Make it clear and engaging for a button label
4. Be concise and specific

EXAMPLES:
- "What do you get if you cross a turkey with a ghost? A poultry-geist!" 
  → "Turkey ghost"
  
- "Why did the coffee taste like dirt? Because it was ground just a few minutes ago."
  → "Ground coffee"
  
- "I threw a boomerang months ago. Now I live in constant fear."
  → "Boomerang fear"
  
- "Why don't skeletons fight each other? They don't have the guts."
  → "Skeleton guts"

RULES:
- Maximum 5 words
- Lowercase preferred
- No quotes or punctuation
- Return ONLY the summary text, nothing else
"""

            def _generate_summary():
                logging.info(f"🤖 In thread: Calling Gemini API to generate summary...")
                try:
                    model = genai.GenerativeModel("gemini-2.0-flash")
                    response = model.generate_content(prompt)
                    logging.info(f"🤖 In thread: Got response from Gemini")
                    
                    # Clean up the response
                    summary = response.text.strip()
                    summary = summary.strip('"\'')  # Remove quotes if present
                    
                    # Ensure it's not too long (5 words max)
                    words = summary.split()
                    if len(words) > 5:
                        summary = ' '.join(words[:5])

                    normalized = summary.strip().lower()
                    if not normalized or normalized in {"joke", "a joke", "the joke"}:
                        fallback = self._fallback_summary_from_text(joke_text)
                        logging.info(f"🤖 In thread: Summary too generic, fallback to: {fallback}")
                        return fallback
                    
                    logging.info(f"🤖 In thread: Generated summary: {summary}")
                    return summary if summary else self._fallback_summary_from_text(joke_text)
                    
                except Exception as e:
                    logging.error(f"❌ Error calling Gemini API: {e}", exc_info=True)
                    return self._fallback_summary_from_text(joke_text)  # Default fallback
            
            return await asyncio.to_thread(_generate_summary)
                
        except Exception as e:
            logging.error(f"❌ Error generating joke summary: {e}", exc_info=True)
            return self._fallback_summary_from_text(joke_text)  # Default fallback

    def _fallback_summary_from_text(self, joke_text: str) -> str:
        """Generate a simple fallback summary from the joke text."""
        tokens = re.findall(r"[a-z0-9']+", (joke_text or "").lower())
        stopwords = {
            "a", "an", "the", "and", "or", "but", "if", "then", "than", "so", "to",
            "in", "on", "at", "of", "for", "with", "by", "from", "is", "are", "was",
            "were", "be", "been", "being", "do", "does", "did", "have", "has", "had",
            "i", "you", "he", "she", "it", "we", "they", "me", "my", "your", "his",
            "her", "its", "our", "their", "this", "that", "these", "those", "what",
            "why", "how", "when", "where", "who", "whom", "because", "as", "about",
            "just", "joke"
        }
        filtered = [token for token in tokens if token not in stopwords]
        if not filtered:
            return "funny"

        summary_words = filtered[:3]
        return " ".join(summary_words)
    
    async def update_joke(self, joke_id: str, text: Optional[str] = None, 
                         tags: Optional[List[str]] = None, 
                         enabled: Optional[bool] = None,
                         summary: Optional[str] = None) -> Dict[str, Any]:
        """Update a joke's text, tags, summary, or status."""
        try:
            updates = {"updatedAt": datetime.utcnow()}
            
            if text:
                updates["text"] = text.strip()
            if tags is not None:
                updates["tags"] = tags
            if enabled is not None:
                updates["enabled"] = enabled
            if summary is not None:
                updates["summary"] = summary.strip()
            
            def _update_doc():
                self.db.collection(self.collection).document(joke_id).update(updates)
            
            await asyncio.to_thread(_update_doc)
            
            return {"success": True, "joke_id": joke_id}
        except Exception as e:
            logging.error(f"Error updating joke: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_joke(self, joke_id: str, retire: bool = True) -> Dict[str, Any]:
        """Delete or retire a joke. Retiring (soft delete) is preferred."""
        try:
            def _delete_doc():
                if retire:
                    # Soft delete: mark as disabled
                    self.db.collection(self.collection).document(joke_id).update({
                        "enabled": False,
                        "updatedAt": datetime.utcnow()
                    })
                else:
                    # Hard delete
                    self.db.collection(self.collection).document(joke_id).delete()
            
            await asyncio.to_thread(_delete_doc)
            
            return {"success": True, "joke_id": joke_id}
        except Exception as e:
            logging.error(f"Error deleting joke: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_all_jokes(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """Get all jokes for admin management."""
        try:
            def _fetch_jokes():
                query = self.db.collection(self.collection)
                
                if not include_disabled:
                    query = query.where("enabled", "==", True)
                
                docs = query.stream()
                jokes = []
                for doc in docs:
                    joke = {"id": doc.id}
                    joke_data = doc.to_dict()
                    
                    # Convert datetime objects to ISO format strings for JSON serialization
                    if "createdAt" in joke_data and isinstance(joke_data["createdAt"], datetime):
                        joke_data["createdAt"] = joke_data["createdAt"].isoformat()
                    if "updatedAt" in joke_data and isinstance(joke_data["updatedAt"], datetime):
                        joke_data["updatedAt"] = joke_data["updatedAt"].isoformat()
                    
                    joke.update(joke_data)
                    jokes.append(joke)
                
                return jokes
            
            return await asyncio.to_thread(_fetch_jokes)
        except Exception as e:
            logging.error(f"Error fetching all jokes: {e}", exc_info=True)
            return []
    
    async def import_jokes_from_csv(self, csv_content: str, source: str = "csv_import") -> Dict[str, Any]:
        """
        Import jokes from CSV content using proper CSV parsing.
        Format: one joke per line
        - Simple: "joke text"
        - With tags: "joke text","tag1","tag2","tag3"
        
        Supports standard CSV escaping (quoted fields, escaped quotes)
        """
        try:
            logging.info(f"📝 Starting CSV import with {len(csv_content)} characters")
            
            # Use csv.reader to properly parse CSV with quoted fields
            csv_reader = csv.reader(io.StringIO(csv_content))
            imported_count = 0
            errors = []
            
            for line_num, row in enumerate(csv_reader, 1):
                if not row or not row[0].strip():
                    continue
                
                # First column is always the joke text
                joke_text = row[0].strip()
                
                # Clean up CSV artifacts (order matters!):
                # 1. FIRST remove leading/trailing quotes if they're wrapping the entire text
                if joke_text.startswith('"') and joke_text.endswith('"'):
                    joke_text = joke_text[1:-1].strip()
                elif joke_text.startswith("'") and joke_text.endswith("'"):
                    joke_text = joke_text[1:-1].strip()
                
                # 2. THEN replace escaped double quotes with single quotes
                joke_text = joke_text.replace('""', '"')
                
                # Remaining columns (if any) are tags
                manual_tags = None
                if len(row) > 1:
                    manual_tags = [tag.strip() for tag in row[1:] if tag.strip()]
                
                if not joke_text:
                    errors.append(f"Line {line_num}: Empty joke text")
                    continue
                
                logging.info(f"📝 Importing line {line_num}: {joke_text[:50]}... tags={manual_tags}")
                
                try:
                    result = await self.add_joke(
                        joke_text, 
                        tags=manual_tags if manual_tags else None,
                        source=source,
                        auto_tag=True
                    )
                    if result["success"]:
                        imported_count += 1
                        logging.info(f"✅ Imported line {line_num} successfully")
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        errors.append(f"Line {line_num}: {error_msg}")
                        logging.warning(f"⚠️  Line {line_num} failed: {error_msg}")
                except Exception as e:
                    error_msg = str(e)
                    errors.append(f"Line {line_num}: {error_msg}")
                    logging.error(f"❌ Line {line_num} error: {error_msg}", exc_info=True)
            
            logging.info(f"✅ CSV import complete: {imported_count} jokes imported, {len(errors)} errors")
            
            return {
                "success": True,
                "imported_count": imported_count,
                "errors": errors,
                "error_count": len(errors)
            }
        except Exception as e:
            logging.error(f"❌ Error importing jokes from CSV: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


async def bulk_import_icanhazdadjoke():
    """One-time bulk import from icanhazdadjoke.com API with pagination and auto-tagging."""
    try:
        import aiohttp
        import asyncio
        
        logging.info("📝 Starting bulk import from icanhazdadjoke.com...")
        
        db = JokesDatabase()
        jokes_added = 0
        errors = []
        all_jokes = []
        
        # icanhazdadjoke.com requires Accept header for JSON response
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Bravo AAC App'
        }
        
        # Use timeout for API calls
        timeout = aiohttp.ClientTimeout(total=120)  # 2 minute timeout for entire session
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # First request to get total count
                logging.info("🌐 Fetching jokes from icanhazdadjoke.com API...")
                async with session.get('https://icanhazdadjoke.com/search?limit=30&page=1', headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        raise Exception(f"API returned status {resp.status}")
                    data = await resp.json()
                    total_jokes = data.get('total_jokes', 0)
                    total_pages = data.get('total_pages', 1)
                    all_jokes.extend(data.get('results', []))
                    
                    logging.info(f"📊 Found {total_jokes} total jokes across {total_pages} pages")
                
                # Fetch remaining pages (limit to first 10 pages for safety)
                pages_to_fetch = min(total_pages, 10)
                if pages_to_fetch > 1:
                    for page in range(2, pages_to_fetch + 1):
                        logging.info(f"📥 Fetching page {page}/{pages_to_fetch}...")
                        try:
                            async with session.get(f'https://icanhazdadjoke.com/search?limit=30&page={page}', headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    all_jokes.extend(data.get('results', []))
                                else:
                                    logging.warning(f"⚠️ Page {page} returned status {resp.status}")
                        except asyncio.TimeoutError:
                            logging.warning(f"⚠️ Timeout fetching page {page}, continuing...")
                            continue
                        
                        # Be nice to their API
                        await asyncio.sleep(0.5)
                
                logging.info(f"📥 Retrieved {len(all_jokes)} total jokes from API")
                
                if not all_jokes:
                    return {"success": False, "error": "No jokes retrieved from icanhazdadjoke.com", "imported_count": 0}
                
            except asyncio.TimeoutError as e:
                logging.error(f"❌ Timeout fetching from icanhazdadjoke: {e}")
                return {"success": False, "error": "Timeout fetching from API", "imported_count": 0}
            except Exception as e:
                logging.error(f"❌ Error fetching from icanhazdadjoke: {e}", exc_info=True)
                return {"success": False, "error": str(e), "imported_count": 0}
        
        # Now import all jokes (without auto-tagging first for speed)
        for idx, joke in enumerate(all_jokes, 1):
            if idx % 50 == 0:
                logging.info(f"📝 Processing joke {idx}/{len(all_jokes)}...")
            
            try:
                # Clean the joke text
                joke_text = joke.get('joke', '').strip()
                if not joke_text:
                    continue
                
                # 1. Remove leading/trailing quotes if they're wrapping the entire text
                if joke_text.startswith('"') and joke_text.endswith('"'):
                    joke_text = joke_text[1:-1].strip()
                elif joke_text.startswith("'") and joke_text.endswith("'"):
                    joke_text = joke_text[1:-1].strip()
                
                # 2. Replace escaped double quotes with single quotes
                joke_text = joke_text.replace('""', '"')
                
                # Add joke WITHOUT auto-tagging initially (to be fast)
                result = await db.add_joke(
                    joke_text,
                    tags=['dad_joke', 'clean'],  # icanhazdadjoke is always clean
                    source='icanhazdadjoke',
                    auto_tag=False  # DISABLED for speed - we'll tag after all are imported
                )
                if result.get("success"):
                    jokes_added += 1
                else:
                    errors.append(f"Joke {idx}: {result.get('error', 'Unknown error')}")
            except Exception as e:
                logging.error(f"❌ Error adding joke {idx}: {e}", exc_info=True)
                errors.append(f"Joke {idx}: {str(e)}")
        
        logging.info(f"✅ Imported {jokes_added} jokes from icanhazdadjoke.com")
        if errors:
            logging.warning(f"⚠️ {len(errors)} import errors occurred")
            logging.warning(f"First error: {errors[0] if errors else 'None'}")
        
        # NOW: Add LLM tags to all imported jokes (after they're all in the database)
        if jokes_added > 0:
            logging.info(f"🏷️ Starting to tag {jokes_added} imported jokes...")
            tagged_count = 0
            tagging_errors = []
            
            def _fetch_untagged():
                # Fetch all jokes with minimal tags (just dad_joke + clean)
                query = db.collection("jokes").where("enabled", "==", True)
                docs = query.stream()
                return [
                    {"id": doc.id, "text": doc.to_dict().get("text", "")}
                    for doc in docs
                    if set(doc.to_dict().get("tags", [])) == {"dad_joke", "clean"} or 
                       set(doc.to_dict().get("tags", [])) == {"clean", "dad_joke"}
                ]
            
            untagged_jokes = await asyncio.to_thread(_fetch_untagged)
            logging.info(f"🏷️ Found {len(untagged_jokes)} jokes to tag")
            
            for tag_idx, joke_item in enumerate(untagged_jokes, 1):
                if tag_idx % 10 == 0:
                    logging.info(f"🏷️ Tagging joke {tag_idx}/{len(untagged_jokes)}...")
                
                try:
                    joke_id = joke_item["id"]
                    joke_text = joke_item["text"]
                    
                    # Generate tags using LLM
                    new_tags = await db._auto_tag_joke(joke_text)
                    
                    # Combine: keep dad_joke + clean, add LLM-generated tags
                    combined_tags = list(set(["dad_joke", "clean"] + new_tags))
                    
                    # Update in Firestore
                    def _update_tags():
                        db.collection("jokes").document(joke_id).update({"tags": combined_tags})
                    
                    await asyncio.to_thread(_update_tags)
                    tagged_count += 1
                    
                except Exception as e:
                    logging.error(f"❌ Error tagging joke {tag_idx}: {e}")
                    tagging_errors.append(str(e))
            
            logging.info(f"✅ Tagged {tagged_count} jokes successfully")
            if tagging_errors:
                logging.warning(f"⚠️ {len(tagging_errors)} tagging errors occurred")
        
        return {
            "success": True,
            "imported_count": jokes_added,
            "total_processed": len(all_jokes),
            "import_errors": errors[:10],  # Return first 10 errors only
            "status": "Import and tagging complete"
        }
        
    except Exception as e:
        logging.error(f"❌ Error bulk importing from icanhazdadjoke: {e}", exc_info=True)
        return {"success": False, "error": str(e), "imported_count": 0}


async def cleanup_joke_quotes():
    """Clean up quotes from all existing jokes in the database."""
    try:
        logging.info("🧹 Starting quote cleanup for all jokes...")
        
        db = JokesDatabase()
        
        # Get all jokes
        def _fetch_all():
            docs = db.db.collection(db.collection).stream()
            return [(doc.id, doc.to_dict()) for doc in docs]
        
        all_jokes = await asyncio.to_thread(_fetch_all)
        logging.info(f"📊 Found {len(all_jokes)} jokes to check")
        
        cleaned_count = 0
        
        for joke_id, joke_data in all_jokes:
            original_text = joke_data.get('text', '')
            cleaned_text = original_text.strip()
            
            # Remove leading/trailing quotes
            if cleaned_text.startswith('"') and cleaned_text.endswith('"'):
                cleaned_text = cleaned_text[1:-1].strip()
            elif cleaned_text.startswith("'") and cleaned_text.endswith("'"):
                cleaned_text = cleaned_text[1:-1].strip()
            
            # Replace escaped double quotes
            cleaned_text = cleaned_text.replace('""', '"')
            
            # Only update if text changed
            if cleaned_text != original_text:
                def _update():
                    db.db.collection(db.collection).document(joke_id).update({
                        'text': cleaned_text
                    })
                
                await asyncio.to_thread(_update)
                cleaned_count += 1
                
                if cleaned_count % 50 == 0:
                    logging.info(f"🧹 Cleaned {cleaned_count} jokes so far...")
        
        logging.info(f"✅ Cleanup complete! Fixed {cleaned_count} jokes")
        
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "total_checked": len(all_jokes)
        }
        
    except Exception as e:
        logging.error(f"❌ Error cleaning up quotes: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# Initialize global database instance
jokes_db = JokesDatabase()
