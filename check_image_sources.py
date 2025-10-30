#!/usr/bin/env python3
"""Check image sources and counts in Firestore database"""

import asyncio
import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Try to get existing app
        app = firebase_admin.get_app()
    except ValueError:
        # App doesn't exist, create it
        try:
            cred = credentials.ApplicationDefault()
            app = firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            return None
    
    return firestore.client()

async def check_image_sources():
    """Check all image sources and counts"""
    db = initialize_firebase()
    if not db:
        return
    
    try:
        # Get all images
        collection_ref = db.collection('aac_images')
        docs = await asyncio.to_thread(collection_ref.get)
        
        sources = {}
        total = 0
        
        for doc in docs:
            data = doc.to_dict()
            source = data.get('source', 'no_source')
            sources[source] = sources.get(source, 0) + 1
            total += 1
            
            # Show progress for large collections
            if total % 500 == 0:
                print(f"Processed {total} images...")
        
        print(f'\n✅ Total images in database: {total}')
        print('📊 Sources breakdown:')
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            print(f'   {source}: {count:,} images')
            
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    asyncio.run(check_image_sources())