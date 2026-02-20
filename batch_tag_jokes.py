#!/usr/bin/env python3
"""
Batch tag jokes that have minimal tags (just 'dad_joke' and 'clean').
Run this after bulk import to add LLM-generated tags.
"""

import asyncio
import logging
from google.cloud import firestore
from jokes_system import JokesDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def batch_tag_jokes():
    """Add LLM-generated tags to jokes that only have basic tags."""
    try:
        jokes_db = JokesDatabase()
        db = jokes_db.db
        
        logger.info("📚 Fetching jokes from Firestore...")
        docs = db.collection("jokes").where("enabled", "==", True).stream()
        
        jokes_to_tag = []
        for doc in docs:
            data = doc.to_dict()
            tags = data.get("tags", [])
            
            # Only tag if tags are minimal (just dad_joke and clean)
            if set(tags) == {"dad_joke", "clean"} or set(tags) == {"clean", "dad_joke"}:
                jokes_to_tag.append({"id": doc.id, "text": data.get("text", "")})
        
        logger.info(f"✅ Found {len(jokes_to_tag)} jokes to tag")
        
        if not jokes_to_tag:
            logger.info("⏭️  No jokes need tagging")
            return
        
        # Tag jokes in batches
        tagged_count = 0
        for idx, joke_item in enumerate(jokes_to_tag, 1):
            joke_id = joke_item["id"]
            joke_text = joke_item["text"]
            
            if idx % 10 == 0:
                logger.info(f"🏷️  Tagging joke {idx}/{len(jokes_to_tag)}...")
            
            try:
                # Generate tags
                new_tags = await jokes_db._auto_tag_joke(joke_text)
                
                # Keep dad_joke and clean, add new tags
                combined_tags = list(set(["dad_joke", "clean"] + new_tags))
                
                # Update in Firestore
                def _update():
                    db.collection("jokes").document(joke_id).update({"tags": combined_tags})
                
                await asyncio.to_thread(_update)
                
                tagged_count += 1
                logger.info(f"✅ Tagged joke {joke_id} with: {new_tags}")
                
            except Exception as e:
                logger.error(f"❌ Error tagging joke {joke_id}: {e}")
        
        logger.info(f"✅ Done! Tagged {tagged_count} jokes")
        
    except Exception as e:
        logger.error(f"❌ Error in batch tagging: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    logger.info("🎯 Starting batch joke tagging...")
    asyncio.run(batch_tag_jokes())
    logger.info("✅ Batch tagging complete!")
