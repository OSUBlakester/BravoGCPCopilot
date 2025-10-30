#!/usr/bin/env python3

import firebase_admin
from firebase_admin import firestore

def check_batch_009_status():
    try:
        firebase_admin.initialize_app()
        db = firestore.client()
        
        print("Quick check for batch_009 entries...")
        
        # Check different collections and patterns
        collections_to_check = [
            ('aac_images', 'concept', 'batch_009'),
            ('aac_symbols', 'concept', 'batch_009'), 
            ('aac_symbols', 'batch', 'batch_009')
        ]
        
        total_found = 0
        
        for collection_name, field, value in collections_to_check:
            try:
                # Get count by limiting to 1000 and counting
                docs = list(db.collection(collection_name).where(field, '==', value).limit(1000).stream())
                count = len(docs)
                total_found += count
                print(f"{collection_name} ({field}='{value}'): {count} documents")
                
                # Show a sample if any found
                if count > 0 and len(docs) > 0:
                    sample = docs[0].to_dict()
                    print(f"  Sample: concept={sample.get('concept')}, subconcept={sample.get('subconcept')}")
                    
            except Exception as e:
                print(f"Error checking {collection_name}: {e}")
        
        print(f"\nTotal batch_009 documents found: {total_found}")
        return total_found > 0
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    check_batch_009_status()
