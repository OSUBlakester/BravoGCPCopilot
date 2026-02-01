#!/usr/bin/env python3
"""
Inspect all fields in aac_images collection documents.
"""

import firebase_admin
from firebase_admin import firestore
import os

def inspect_all_fields():
    """Show all field names in aac_images documents."""
    
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
    
    # Get first 5 documents to see full structure
    collection_ref = db.collection('aac_images')
    docs = collection_ref.limit(5).stream()
    
    print("All fields in first 5 documents:")
    print("=" * 80)
    
    all_field_names = set()
    
    for doc in docs:
        doc_data = doc.to_dict()
        doc_id = doc.id
        
        print(f"\nDocument ID: {doc_id}")
        print(f"Fields:")
        for field, value in sorted(doc_data.items()):
            all_field_names.add(field)
            # Truncate long values
            if isinstance(value, list):
                print(f"  {field}: [array with {len(value)} items]")
            elif isinstance(value, str) and len(value) > 100:
                print(f"  {field}: {value[:100]}...")
            else:
                print(f"  {field}: {value}")
    
    print("\n" + "=" * 80)
    print("\nAll unique field names found:")
    for field in sorted(all_field_names):
        print(f"  - {field}")
    
    # Now search specifically for Tag 1
    print("\n" + "=" * 80)
    print("Searching for documents with 'Tag 1' field...")
    
    all_docs = collection_ref.limit(100).stream()
    tag1_found = 0
    
    for doc in all_docs:
        doc_data = doc.to_dict()
        if 'Tag 1' in doc_data:
            tag1_found += 1
            if tag1_found <= 5:  # Show first 5
                print(f"\n  Document: {doc.id}")
                print(f"    Tag 1: {doc_data.get('Tag 1')}")
    
    print(f"\nDocuments with 'Tag 1' field (in first 100): {tag1_found}")

if __name__ == "__main__":
    inspect_all_fields()
