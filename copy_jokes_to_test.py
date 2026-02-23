#!/usr/bin/env python3
"""
Copy the jokes collection from dev to test project
"""

import sys
from google.cloud import firestore

# Project configurations
SOURCE_PROJECT = 'bravo-dev-465400'
DEST_PROJECT = 'bravo-test-465400'
COLLECTION = 'jokes'

def delete_collection(db, collection_name, batch_size=500):
    """Delete all documents in a Firestore collection"""
    
    print(f"\n🗑️  Deleting collection: {collection_name}")
    
    collection_ref = db.collection(collection_name)
    docs = collection_ref.stream()
    
    deleted = 0
    errors = 0
    batch = db.batch()
    batch_count = 0
    
    for doc in docs:
        try:
            batch.delete(collection_ref.document(doc.id))
            batch_count += 1
            deleted += 1
            
            # Commit batch every batch_size documents
            if batch_count >= batch_size:
                batch.commit()
                print(f"   ✅ Deleted batch of {batch_count} documents (total: {deleted})")
                batch = db.batch()
                batch_count = 0
                
        except Exception as e:
            print(f"   ❌ Error deleting document {doc.id}: {e}")
            errors += 1
    
    # Commit any remaining documents
    if batch_count > 0:
        batch.commit()
        print(f"   ✅ Deleted final batch of {batch_count} documents")
    
    print(f"\n   Summary for {collection_name}:")
    print(f"   ✅ Deleted: {deleted}")
    print(f"   ❌ Errors:  {errors}")
    
    return deleted, errors

def copy_collection(source_db, dest_db, collection_name, batch_size=500):
    """Copy a Firestore collection from source to destination"""
    
    print(f"\n📁 Copying collection: {collection_name}")
    
    # Get all documents in the source collection
    source_collection = source_db.collection(collection_name)
    docs = source_collection.stream()
    
    copied = 0
    errors = 0
    batch = dest_db.batch()
    batch_count = 0
    
    for doc in docs:
        try:
            # Get document data
            doc_data = doc.to_dict()
            
            # Copy to destination
            dest_ref = dest_db.collection(collection_name).document(doc.id)
            batch.set(dest_ref, doc_data)
            batch_count += 1
            copied += 1
            
            # Commit batch every batch_size documents
            if batch_count >= batch_size:
                batch.commit()
                print(f"   ✅ Copied batch of {batch_count} documents (total: {copied})")
                batch = dest_db.batch()
                batch_count = 0
                
        except Exception as e:
            print(f"   ❌ Error copying document {doc.id}: {e}")
            errors += 1
    
    # Commit any remaining documents
    if batch_count > 0:
        batch.commit()
        print(f"   ✅ Copied final batch of {batch_count} documents")
    
    print(f"\n   Summary for {collection_name}:")
    print(f"   ✅ Copied: {copied}")
    print(f"   ❌ Errors: {errors}")
    
    return copied, errors

def main():
    print()
    print("=" * 60)
    print("⚠️  Copy jokes collection from dev to test")
    print("=" * 60)
    print(f"   Source:      {SOURCE_PROJECT}")
    print(f"   Destination: {DEST_PROJECT}")
    print(f"   Collection:  {COLLECTION}")
    print()
    print("⚠️  WARNING: This will DELETE ALL existing jokes in test first!")
    print()
    print("✅ Proceeding with copy operation...")
    
    # Initialize Firestore clients
    print("\n🔌 Connecting to Firestore...")
    source_db = firestore.Client(project=SOURCE_PROJECT)
    dest_db = firestore.Client(project=DEST_PROJECT)
    
    # Delete existing jokes in test
    deleted, del_errors = delete_collection(dest_db, COLLECTION)
    
    # Copy jokes from dev to test
    copied, copy_errors = copy_collection(source_db, dest_db, COLLECTION)
    
    print("\n" + "=" * 60)
    print("📊 Overall Summary:")
    print(f"   🗑️  Deleted from test: {deleted}")
    print(f"   ✅ Copied from dev:    {copied}")
    print(f"   ❌ Total Errors:       {del_errors + copy_errors}")
    print("=" * 60)
    print()

if __name__ == "__main__":
    main()
