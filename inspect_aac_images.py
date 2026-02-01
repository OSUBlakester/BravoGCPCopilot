#!/usr/bin/env python3
"""
Inspect aac_images collection to see Tag 1 values.
"""

import firebase_admin
from firebase_admin import firestore
import os

def inspect_tags():
    """Inspect Tag 1 field in aac_images documents."""
    
    # Initialize Firebase Admin SDK
    if not firebase_admin._apps:
        key_path = '/keys/service-account.json'
        if os.path.exists(key_path):
            from firebase_admin import credentials
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
    
    db = firestore.client()
    
    # Get first 20 documents to see structure
    collection_ref = db.collection('aac_images')
    docs = collection_ref.limit(20).stream()
    
    print("Sample documents from aac_images collection:")
    print("=" * 80)
    
    tag1_values = set()
    
    for doc in docs:
        doc_data = doc.to_dict()
        doc_id = doc.id
        
        # Get all field names that contain "tag"
        tag_fields = {k: v for k, v in doc_data.items() if 'tag' in k.lower() or 'Tag' in k}
        
        if tag_fields:
            print(f"\nDocument ID: {doc_id}")
            print(f"  Label: {doc_data.get('Label', 'N/A')}")
            for field, value in tag_fields.items():
                print(f"  {field}: {value}")
                if field == 'Tag 1' or field == 'tag_1' or field == 'tag1':
                    tag1_values.add(value)
    
    print("\n" + "=" * 80)
    print("\nUnique Tag 1 values found:")
    for val in sorted(tag1_values):
        print(f"  - {val}")
    
    # Count documents with 'food' in various tag fields
    print("\n" + "=" * 80)
    print("Searching for documents with 'food'...")
    
    all_docs = collection_ref.stream()
    food_count = 0
    
    for doc in all_docs:
        doc_data = doc.to_dict()
        # Check all fields for 'food'
        for field, value in doc_data.items():
            if isinstance(value, str) and value.lower() == 'food':
                food_count += 1
                print(f"\n  Document: {doc.id}")
                print(f"    Label: {doc_data.get('Label', 'N/A')}")
                print(f"    Field '{field}': {value}")
                break
    
    print(f"\nTotal documents with 'food' value: {food_count}")

if __name__ == "__main__":
    inspect_tags()
