#!/usr/bin/env python3
"""
Copy jokes collection from dev Firestore to prod Firestore
Only copies the 'jokes' collection - nothing else
"""

import json
from google.cloud import firestore
from datetime import datetime

# Configuration
DEV_PROJECT = "bravo-dev-465400"
PROD_PROJECT = "bravo-prod-465323"
COLLECTION_NAME = "jokes"

def copy_jokes_collection():
    """Copy jokes collection from dev to prod"""
    
    print(f"🚀 Starting jokes collection copy from {DEV_PROJECT} to {PROD_PROJECT}")
    
    # Initialize clients for both projects
    dev_db = firestore.Client(project=DEV_PROJECT)
    prod_db = firestore.Client(project=PROD_PROJECT)
    
    # Get all jokes from dev
    print(f"\n📖 Reading jokes from dev ({DEV_PROJECT})...")
    dev_jokes_ref = dev_db.collection(COLLECTION_NAME)
    dev_docs = list(dev_jokes_ref.stream())
    
    print(f"✅ Found {len(dev_docs)} jokes in dev")
    
    if not dev_docs:
        print("⚠️  No jokes found in dev collection. Exiting.")
        return
    
    # Copy to prod
    print(f"\n📝 Copying jokes to prod ({PROD_PROJECT})...")
    prod_jokes_ref = prod_db.collection(COLLECTION_NAME)
    
    copied_count = 0
    failed_count = 0
    
    for dev_doc in dev_docs:
        doc_id = dev_doc.id
        doc_data = dev_doc.to_dict()
        
        try:
            # Write to prod with same document ID
            prod_jokes_ref.document(doc_id).set(doc_data)
            copied_count += 1
            print(f"  ✓ Copied: {doc_id}")
        except Exception as e:
            failed_count += 1
            print(f"  ✗ Failed to copy {doc_id}: {str(e)}")
    
    # Summary
    print(f"\n📊 Copy Summary:")
    print(f"  Total jokes: {len(dev_docs)}")
    print(f"  Successfully copied: {copied_count}")
    print(f"  Failed: {failed_count}")
    
    if failed_count == 0:
        print(f"\n✅ All jokes successfully copied from dev to prod!")
    else:
        print(f"\n⚠️  {failed_count} jokes failed to copy. Please review.")

if __name__ == "__main__":
    copy_jokes_collection()
