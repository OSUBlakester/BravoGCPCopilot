#!/usr/bin/env python3
"""
Script to clean up batch_009 entries from Firestore aac_images collection
before re-importing the reorganized batch_009 files.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys

def initialize_firebase():
    """Initialize Firebase connection using gcloud auth (Application Default Credentials)"""
    try:
        # Try to get the default app first
        app = firebase_admin.get_app()
        print("Firebase app already initialized")
        return firestore.client()
    except ValueError:
        # Initialize Firebase using Application Default Credentials (gcloud auth)
        try:
            firebase_admin.initialize_app()
            print("Firebase initialized with Application Default Credentials (gcloud auth)")
            return firestore.client()
        except Exception as e:
            print(f"Failed to initialize Firebase with gcloud auth: {e}")
            print("\nTo fix this, run:")
            print("  gcloud auth application-default login")
            print("  gcloud config set project your-project-id")
            return None

def find_batch_009_documents(db):
    """Find all batch_009 documents in aac_images collection"""
    print("Searching for batch_009 entries in Firestore aac_images collection...")
    
    batch_009_docs = {}
    
    try:
        # Search for documents where concept equals 'batch_009'
        query1 = db.collection('aac_images').where('concept', '==', 'batch_009')
        docs1 = list(query1.stream())
        print(f"Found {len(docs1)} documents with concept='batch_009'")
        
        # Search for documents where subconcept contains 'batch_009'
        # Note: Firestore doesn't support 'contains' for strings, so we use range queries
        query2 = db.collection('aac_images').where('subconcept', '>=', 'batch_009').where('subconcept', '<', 'batch_010')
        docs2 = list(query2.stream())
        print(f"Found {len(docs2)} documents with subconcept starting with 'batch_009'")
        
        # Combine and deduplicate results
        for doc in docs1 + docs2:
            batch_009_docs[doc.id] = doc
        
        print(f"\nTotal unique batch_009 documents found: {len(batch_009_docs)}")
        
        if batch_009_docs:
            print("\nSample batch_009 entries:")
            for i, (doc_id, doc) in enumerate(list(batch_009_docs.items())[:5]):
                data = doc.to_dict()
                print(f"  {i+1}. ID: {doc_id}")
                print(f"     Concept: {data.get('concept', 'N/A')}")
                print(f"     Subconcept: {data.get('subconcept', 'N/A')}")
                print(f"     Source: {data.get('source', 'N/A')}")
                print(f"     Image Path: {data.get('image_path', 'N/A')}")
                print()
        
        return batch_009_docs
        
    except Exception as e:
        print(f"Error searching for batch_009 documents: {e}")
        import traceback
        traceback.print_exc()
        return {}

def delete_batch_009_documents(db, batch_009_docs):
    """Delete batch_009 documents from Firestore"""
    if not batch_009_docs:
        print("No batch_009 documents to delete.")
        return 0
    
    print(f"\nProceeding to delete {len(batch_009_docs)} batch_009 documents...")
    deleted_count = 0
    batch_size = 500  # Firestore batch limit
    
    doc_ids = list(batch_009_docs.keys())
    for i in range(0, len(doc_ids), batch_size):
        batch = db.batch()
        batch_doc_ids = doc_ids[i:i + batch_size]
        
        for doc_id in batch_doc_ids:
            doc_ref = db.collection('aac_images').document(doc_id)
            batch.delete(doc_ref)
            deleted_count += 1
        
        try:
            batch.commit()
            print(f"Deleted batch {i//batch_size + 1}: {len(batch_doc_ids)} documents")
        except Exception as e:
            print(f"Error deleting batch {i//batch_size + 1}: {e}")
            break
    
    print(f"\nSuccessfully deleted {deleted_count} batch_009 entries from Firestore!")
    return deleted_count

def main():
    """Main function"""
    print("Batch 009 Firestore Cleanup Script")
    print("=" * 40)
    
    # Initialize Firebase
    db = initialize_firebase()
    if not db:
        print("Failed to initialize Firebase. Exiting.")
        return
    
    # Find batch_009 documents
    batch_009_docs = find_batch_009_documents(db)
    
    if not batch_009_docs:
        print("No batch_009 documents found. Cleanup not needed.")
        return
    
    # Delete batch_009 documents
    deleted_count = delete_batch_009_documents(db, batch_009_docs)
    
    if deleted_count > 0:
        print(f"\nCleanup complete! Removed {deleted_count} batch_009 entries from Firestore.")
        print("You can now proceed with the re-import of the reorganized batch_009 files.")
    else:
        print("No documents were deleted.")

if __name__ == "__main__":
    main()
