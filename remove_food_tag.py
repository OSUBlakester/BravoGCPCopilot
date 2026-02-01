#!/usr/bin/env python3
"""
Remove 'food' from tags array in all aac_images documents in Firestore.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os

def remove_food_tag():
    """Remove 'food' from tags array in all aac_images documents."""
    
    # Initialize Firebase Admin SDK with Application Default Credentials
    if not firebase_admin._apps:
        # Try to use service account key if available, otherwise use ADC
        key_path = '/keys/service-account.json'
        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
        else:
            # Use Application Default Credentials
            firebase_admin.initialize_app()
    
    db = firestore.client()
    
    # Query all documents where tags array contains "food"
    collection_ref = db.collection('aac_images')
    query = collection_ref.where('tags', 'array_contains', 'food')
    
    docs = query.stream()
    
    updated_count = 0
    error_count = 0
    
    print("Starting to remove 'food' from tags array...")
    print("-" * 60)
    
    for doc in docs:
        try:
            doc_id = doc.id
            doc_data = doc.to_dict()
            
            # Show current data
            print(f"\nDocument ID: {doc_id}")
            print(f"  Current tags: {doc_data.get('tags', [])}")
            print(f"  Label: {doc_data.get('Label', 'N/A')}")
            
            # Remove 'food' from tags array
            doc.reference.update({
                'tags': firestore.ArrayRemove(['food'])
            })
            
            print(f"  ✓ Removed 'food' from tags array")
            updated_count += 1
            
        except Exception as e:
            print(f"  ✗ Error updating document {doc_id}: {e}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print(f"Update complete!")
    print(f"Documents updated: {updated_count}")
    print(f"Errors: {error_count}")
    print("=" * 60)

if __name__ == "__main__":
    # Confirm before proceeding
    print("\n" + "!" * 60)
    print("WARNING: This will remove 'food' from Tag 1 field in")
    print("         all aac_images documents where Tag 1 = 'food'")
    print("!" * 60)
    
    response = input("\nDo you want to proceed? (yes/no): ")
    
    if response.lower() == 'yes':
        remove_food_tag()
    else:
        print("Operation cancelled.")
