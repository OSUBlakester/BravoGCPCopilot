#!/usr/bin/env python3
"""
Copy ONLY the aac_images Firestore collection between GCP projects
⚠️  SAFETY: This script is hardcoded to ONLY copy the aac_images collection.
⚠️  It will NEVER touch accounts, users, or any other critical collections.

Usage: python3 copy_firestore_between_projects.py <source_project> <dest_project> [--delete-existing]
Example: python3 copy_firestore_between_projects.py dev prod
Example: python3 copy_firestore_between_projects.py dev prod --delete-existing
"""

import sys
import argparse
from google.cloud import firestore

# SAFETY: Hardcoded to only copy this collection
ALLOWED_COLLECTION = 'aac_images'

# Project configurations
PROJECTS = {
    'dev': 'bravo-dev-465400',
    'test': 'bravo-test-465400',
    'prod': 'bravo-prod-465323'
}

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
    skipped = 0
    errors = 0
    batch = dest_db.batch()
    batch_count = 0
    
    for doc in docs:
        try:
            # Get the destination document reference
            dest_doc_ref = dest_db.collection(collection_name).document(doc.id)
            
            # Check if document already exists
            if dest_doc_ref.get().exists:
                print(f"   ⏭️  Skipping (already exists): {doc.id}")
                skipped += 1
                continue
            
            # Add to batch
            batch.set(dest_doc_ref, doc.to_dict())
            batch_count += 1
            copied += 1
            
            # Commit batch every batch_size documents
            if batch_count >= batch_size:
                batch.commit()
                print(f"   ✅ Committed batch of {batch_count} documents (total: {copied})")
                batch = dest_db.batch()
                batch_count = 0
                
        except Exception as e:
            print(f"   ❌ Error copying document {doc.id}: {e}")
            errors += 1
    
    # Commit any remaining documents
    if batch_count > 0:
        batch.commit()
        print(f"   ✅ Committed final batch of {batch_count} documents")
    
    print(f"\n   Summary for {collection_name}:")
    print(f"   ✅ Copied:  {copied}")
    print(f"   ⏭️  Skipped: {skipped}")
    print(f"   ❌ Errors:  {errors}")
    
    return copied, skipped, errors

def copy_subcollections(source_db, dest_db, parent_path, doc_id):
    """Recursively copy subcollections of a document"""
    
    source_doc_ref = source_db.document(parent_path).document(doc_id)
    dest_doc_ref = dest_db.document(parent_path).document(doc_id)
    
    # Get all subcollections
    for subcollection in source_doc_ref.collections():
        subcoll_name = subcollection.id
        print(f"      📂 Found subcollection: {parent_path}/{doc_id}/{subcoll_name}")
        
        # Copy subcollection documents
        for subdoc in subcollection.stream():
            try:
                dest_subdoc_ref = dest_doc_ref.collection(subcoll_name).document(subdoc.id)
                
                if not dest_subdoc_ref.get().exists:
                    dest_subdoc_ref.set(subdoc.to_dict())
                    print(f"         ✅ Copied: {subdoc.id}")
                    
                    # Recursively copy any nested subcollections
                    copy_subcollections(source_db, dest_db, f"{parent_path}/{doc_id}/{subcoll_name}", subdoc.id)
                else:
                    print(f"         ⏭️  Skipped: {subdoc.id}")
                    
            except Exception as e:
                print(f"         ❌ Error copying {subdoc.id}: {e}")

def copy_firestore_data(source_project_id, dest_project_id, collections=None, delete_existing=False):
    """Copy Firestore collections from source to destination"""
    
    print(f"\n📋 Copying Firestore data")
    print(f"   From: {source_project_id}")
    print(f"   To:   {dest_project_id}")
    
    # Initialize Firestore clients
    source_db = firestore.Client(project=source_project_id)
    dest_db = firestore.Client(project=dest_project_id)
    
    # SAFETY: Force only aac_images collection
    collections = [ALLOWED_COLLECTION]
    
    print(f"   Collection: {ALLOWED_COLLECTION} (hardcoded for safety)")
    print()
    
    total_copied = 0
    total_skipped = 0
    total_errors = 0
    total_deleted = 0
    
    # Delete existing collections if requested
    if delete_existing:
        for collection_name in collections:
            deleted, errors = delete_collection(dest_db, collection_name)
            total_deleted += deleted
            total_errors += errors
    
    for collection_name in collections:
        copied, skipped, errors = copy_collection(source_db, dest_db, collection_name)
        total_copied += copied
        total_skipped += skipped
        total_errors += errors
    
    print("\n" + "=" * 60)
    print("📊 Overall Summary:")
    if delete_existing:
        print(f"   🗑️  Total Deleted: {total_deleted}")
    print(f"   ✅ Total Copied:  {total_copied}")
    print(f"   ⏭️  Total Skipped: {total_skipped}")
    print(f"   ❌ Total Errors:  {total_errors}")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(
        description='Copy ONLY the aac_images Firestore collection between GCP projects (hardcoded for safety)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 copy_firestore_between_projects.py dev prod
  python3 copy_firestore_between_projects.py dev prod --delete-existing

⚠️  SAFETY: This script only copies the aac_images collection.
⚠️  It will never touch accounts, users, or any other collections.
        """
    )
    
    parser.add_argument('source', help='Source project (dev/test/prod or full project ID)')
    parser.add_argument('destination', help='Destination project (dev/test/prod or full project ID)')
    parser.add_argument('--delete-existing', action='store_true',
                       help='Delete all existing documents in aac_images collection before copying')
    
    args = parser.parse_args()
    
    # Convert shortcuts to project IDs
    source_project = PROJECTS.get(args.source, args.source)
    dest_project = PROJECTS.get(args.destination, args.destination)
    
    # Confirm with user
    print()
    print("⚠️  About to copy Firestore data:")
    print(f"   Source:      {source_project}")
    print(f"   Destination: {dest_project}")
    print(f"   Collection:  {ALLOWED_COLLECTION} (hardcoded for safety)")
    if args.delete_existing:
        print(f"   ⚠️  DELETE EXISTING: Yes - all documents in {ALLOWED_COLLECTION} will be deleted first!")
    else:
        print(f"   DELETE EXISTING: No - existing documents will be skipped")
    print()
    print("⚠️  SAFETY: This script ONLY touches the aac_images collection.")
    print("⚠️  It will NEVER modify accounts, users, or any other data.")
    print()
    
    confirm = input("Proceed? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Cancelled")
        sys.exit(0)
    
    copy_firestore_data(source_project, dest_project, None, args.delete_existing)

if __name__ == "__main__":
    main()
