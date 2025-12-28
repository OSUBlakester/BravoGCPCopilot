#!/usr/bin/env python3
"""
Script to copy the 'aac_images' collection from the Dev project to the Test project.
Usage: python3 copy_aac_images_to_test.py
"""

import logging
import argparse
from google.cloud import firestore
from tqdm import tqdm

# Configuration
DEV_PROJECT_ID = "bravo-dev-465400"
TEST_PROJECT_ID = "bravo-test-465400"
COLLECTION_NAME = "aac_images"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def copy_collection(source_project, dest_project, collection_name, dry_run=False):
    """Copies a Firestore collection from source project to destination project."""
    
    logger.info(f"🚀 Starting copy from {source_project} to {dest_project}")
    logger.info(f"📂 Collection: {collection_name}")
    
    # Initialize clients
    try:
        source_db = firestore.Client(project=source_project)
        dest_db = firestore.Client(project=dest_project)
    except Exception as e:
        logger.error(f"❌ Failed to initialize Firestore clients: {e}")
        return

    # Get source documents
    logger.info("📥 Fetching source documents...")
    source_ref = source_db.collection(collection_name)
    docs = list(source_ref.stream())
    
    total_docs = len(docs)
    logger.info(f"📊 Found {total_docs} documents in {source_project}")
    
    if total_docs == 0:
        logger.warning("⚠️ No documents found to copy.")
        return

    if dry_run:
        logger.info("👀 Dry run mode - no changes will be made.")
    
    # Copy documents
    success_count = 0
    error_count = 0
    
    for doc in tqdm(docs, desc="Copying documents"):
        try:
            doc_id = doc.id
            data = doc.to_dict()
            
            # Optional: Transform data if needed (e.g., update bucket URLs)
            # For now, we assume URLs are either public or we'll handle bucket copy separately
            # If URLs contain the project ID, we might want to replace it, but only if we also move the files.
            
            if not dry_run:
                dest_db.collection(collection_name).document(doc_id).set(data)
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"❌ Error copying document {doc.id}: {e}")
            error_count += 1

    logger.info("-" * 30)
    logger.info(f"✅ Copy complete!")
    logger.info(f"   Success: {success_count}")
    logger.info(f"   Errors:  {error_count}")
    
    if dry_run:
        logger.info("   (Dry run - no actual writes performed)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy aac_images from Dev to Test")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without writing")
    args = parser.parse_args()
    
    copy_collection(DEV_PROJECT_ID, TEST_PROJECT_ID, COLLECTION_NAME, args.dry_run)
