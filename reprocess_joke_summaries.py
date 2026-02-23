#!/usr/bin/env python3
"""
Regenerate summaries for jokes that have missing or generic summaries.
"""

import asyncio
import logging
from datetime import datetime
from google.cloud import firestore
from jokes_system import JokesDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GENERIC_SUMMARIES = {"joke", "a joke", "the joke", ""}

async def reprocess_summaries():
    jokes_db = JokesDatabase()
    db = jokes_db.db

    logger.info("Fetching jokes...")
    docs = db.collection("jokes").stream()

    jokes_list = []
    for doc in docs:
        data = doc.to_dict()
        jokes_list.append({"id": doc.id, "data": data})

    logger.info("Found %d jokes", len(jokes_list))

    updated_count = 0
    for item in jokes_list:
        joke_id = item["id"]
        data = item["data"]
        summary = (data.get("summary") or "").strip()
        if summary.lower() not in GENERIC_SUMMARIES:
            continue

        text = data.get("text") or ""
        if not text.strip():
            continue

        new_summary = await jokes_db._generate_joke_summary(text)
        if not new_summary or new_summary.strip().lower() in GENERIC_SUMMARIES:
            continue

        def _update():
            db.collection("jokes").document(joke_id).update({
                "summary": new_summary,
                "updatedAt": datetime.utcnow()
            })

        await asyncio.to_thread(_update)
        updated_count += 1
        logger.info("Updated %s -> %s", joke_id, new_summary)

    logger.info("Done. Updated %d jokes.", updated_count)


if __name__ == "__main__":
    asyncio.run(reprocess_summaries())
