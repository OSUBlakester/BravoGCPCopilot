#!/usr/bin/env python3
"""
Check how many images are in the aac_images Firestore collection
"""

from google.cloud import firestore

def count_collection(project_id, collection_name):
    """Count documents in a Firestore collection"""
    
    db = firestore.Client(project=project_id)
    collection_ref = db.collection(collection_name)
    
    # Get all documents
    docs = list(collection_ref.stream())
    
    print(f"\n{project_id}:")
    print(f"  Collection '{collection_name}': {len(docs)} documents")
    
    return len(docs)

print("="*60)
print("Counting aac_images in Firestore collections")
print("="*60)

dev_count = count_collection('bravo-dev-465400', 'aac_images')
prod_count = count_collection('bravo-prod-465323', 'aac_images')

print("\n" + "="*60)
print("Summary:")
print("="*60)
print(f"Dev Firestore:  {dev_count} documents")
print(f"Prod Firestore: {prod_count} documents")
print("\nDev Bucket:     9,006 files in bravo_images/")
print(f"Prod Bucket:    9,006 files in bravo_images/")
print("="*60)
print(f"\nDifference: {9006 - dev_count} files in bucket NOT indexed in Firestore")
print("="*60)
