#!/usr/bin/env python3
"""
Quick script to create a test favorite for testing the favorite loading functionality
"""

import json
import asyncio
import sys
import os

# Add the current directory to Python path to import from server.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import save_firestore_document, initialize_firestore_client

async def create_test_favorite():
    """Create a test favorite for testing"""
    
    # Initialize Firestore
    await initialize_firestore_client()
    
    # Test favorite data
    test_favorites = {
        "favorites": [
            {
                "name": "Home Dinner", 
                "location": "Home", 
                "people": "Family", 
                "activity": "Having dinner"
            },
            {
                "name": "Work Meeting", 
                "location": "Office", 
                "people": "Colleagues", 
                "activity": "Team meeting"
            },
            {
                "name": "Park Visit", 
                "location": "Central Park", 
                "people": "Friends", 
                "activity": "Playing frisbee"
            }
        ]
    }
    
    # Save to Firestore - adjust these IDs as needed for your test account
    account_id = "test_account_id"  # Replace with your actual account ID
    aac_user_id = "test_user_id"   # Replace with your actual user ID
    
    try:
        success = await save_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_favorites",
            data_to_save=test_favorites
        )
        
        if success:
            print("✅ Test favorites created successfully!")
            print(f"Created {len(test_favorites['favorites'])} favorites:")
            for fav in test_favorites['favorites']:
                print(f"  - {fav['name']}: {fav['location']} | {fav['people']} | {fav['activity']}")
            print("\nYou can now test loading these favorites in the UI!")
        else:
            print("❌ Failed to create test favorites")
            
    except Exception as e:
        print(f"❌ Error creating test favorites: {e}")

if __name__ == "__main__":
    print("Creating test favorites...")
    asyncio.run(create_test_favorite())
