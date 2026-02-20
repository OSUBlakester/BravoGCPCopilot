#!/usr/bin/env python3
"""
Script to reprocess all existing jokes and remove 'home' tags.
This script:
1. Fetches all jokes from Firestore
2. Removes 'home' tag from each joke's tags list
3. Updates the jokes back to Firestore
"""

import asyncio
import logging
from google.cloud import firestore
from jokes_system import JokesDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reprocess_jokes():
    """Remove 'home' tag from all existing jokes."""
    try:
        jokes_db = JokesDatabase()
        db = jokes_db.db
        
        # Fetch all jokes
        logger.info("📚 Fetching all jokes from Firestore...")
        docs = db.collection("jokes").stream()
        
        jokes_list = []
        for doc in docs:
            joke_data = doc.to_dict()
            jokes_list.append({"id": doc.id, "data": joke_data})
        
        logger.info(f"✅ Found {len(jokes_list)} jokes")
        
        if not jokes_list:
            logger.warning("⚠️  No jokes found to process")
            return
        
        # Process each joke
        updated_count = 0
        for joke_item in jokes_list:
            joke_id = joke_item["id"]
            joke_data = joke_item["data"]
            tags = joke_data.get("tags", [])
            
            # Check if 'home' tag exists
            if "home" in tags:
                # Remove 'home' tag
                updated_tags = [tag for tag in tags if tag != "home"]
                updated_data = joke_data.copy()
                updated_data["tags"] = updated_tags
                
                # Update in Firestore
                def _update():
                    db.collection("jokes").document(joke_id).update({"tags": updated_tags})
                
                await asyncio.to_thread(_update)
                
                logger.info(f"✏️  Updated joke {joke_id}")
                logger.info(f"   Removed 'home' from tags")
                logger.info(f"   Old tags: {tags}")
                logger.info(f"   New tags: {updated_tags}")
                updated_count += 1
            else:
                # No 'home' tag, skip
                logger.info(f"⏭️  Joke {joke_id} has no 'home' tag, skipping")
        
        logger.info(f"✅ Done! Updated {updated_count} jokes")
        
    except Exception as e:
        logger.error(f"❌ Error reprocessing jokes: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    logger.info("🎯 Starting joke reprocessing (remove 'home' tag)...")
    asyncio.run(reprocess_jokes())
    logger.info("✅ Reprocessing complete!")
