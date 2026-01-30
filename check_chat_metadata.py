#!/usr/bin/env python3
"""
Check if chat history messages have the new metadata fields
"""

from google.cloud import firestore
import json

def check_chat_metadata(account_id='Fr1ezRaDRJMxVF8YMKiJ8OBM0052', 
                        user_id='d7a13800-b01c-484f-8304-869154877014',
                        project_id='bravo-dev-465400'):
    """Check the latest chat messages for metadata"""
    
    db = firestore.Client(project=project_id)
    
    # Get chat history
    chat_ref = db.collection('accounts').document(account_id)\
                .collection('users').document(user_id)\
                .collection('chat_history')
    
    # Get latest 10 messages ordered by timestamp
    messages = chat_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
    
    print(f"\n{'='*80}")
    print("Latest 10 Chat Messages - Metadata Check")
    print(f"{'='*80}\n")
    
    has_metadata = False
    for i, msg in enumerate(messages, 1):
        data = msg.to_dict()
        
        print(f"Message {i} (ID: {msg.id[:8]}...)")
        print(f"  Timestamp: {data.get('timestamp', 'N/A')}")
        print(f"  Role: {data.get('role', 'N/A')}")
        print(f"  Content: {data.get('content', '')[:80]}...")
        
        # Check for new metadata fields
        metadata = data.get('metadata', {})
        if metadata:
            has_metadata = True
            print(f"  ✅ Metadata Found:")
            print(f"     Type: {metadata.get('type', 'N/A')}")
            print(f"     Category: {metadata.get('category', 'N/A')}")
            print(f"     Is Repetition: {metadata.get('is_repetition', False)}")
            print(f"     Source: {metadata.get('source', 'N/A')}")
        else:
            print(f"  ❌ No metadata (old message format)")
        
        print()
    
    print(f"{'='*80}")
    if has_metadata:
        print("✅ SUCCESS: New metadata format detected!")
    else:
        print("⚠️  WARNING: No messages with new metadata found yet")
        print("   Create some new chat interactions to test metadata recording")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    check_chat_metadata()
