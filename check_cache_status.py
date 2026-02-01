#!/usr/bin/env python3
"""Check cache status in Firestore."""

import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase
cred = credentials.Certificate("bravo-dev-465400.json")
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Get cache document
account_id = "Fr1ezRaDRJMxVF8YMKiJ8OBM0052"
user_id = "d7a13800-b01c-484f-8304-869154877014"

cache_ref = db.collection("accounts").document(account_id).collection("users").document(user_id).collection("context_cache").document("base")

cache_doc = cache_ref.get()

if cache_doc.exists:
    data = cache_doc.to_dict()
    print("=" * 80)
    print("✅ CACHE EXISTS")
    print("=" * 80)
    
    created = data.get('created_timestamp')
    if created:
        print(f"Created: {created}")
    
    if 'metadata' in data:
        meta = data['metadata']
        print(f"\nMetadata:")
        print(f"  Message count: {meta.get('message_count', 'N/A')}")
        print(f"  Token count: {meta.get('token_count', 'N/A')}")
        print(f"  Chars: {meta.get('chars', 'N/A')}")
        print(f"  Has narrative: {meta.get('has_narrative', False)}")
    
    if 'cached_content' in data:
        content = data['cached_content']
        if isinstance(content, dict):
            content_text = content.get('content', '')
        else:
            content_text = content
        
        print(f"\nContent length: {len(content_text)} chars")
        
        # Check for key indicators
        has_narrative = "NARRATIVE SUMMARY" in content_text
        has_recent = "RECENT MESSAGES" in content_text
        has_joke_avoid = "AVOID THESE" in content_text
        has_answered = "answered questions" in content_text.lower()
        
        print(f"\nIndicators:")
        print(f"  ✓ Has narrative section: {has_narrative}")
        print(f"  ✓ Has recent messages: {has_recent}")
        print(f"  ✓ Has joke avoidance: {has_joke_avoid}")
        print(f"  ✓ Has answered questions: {has_answered}")
        
        # Count messages
        msg_count = content_text.count("user:")
        print(f"  Messages in cache: {msg_count}")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATION: Invalidate cache to force rebuild with Phase 3 code")
    print("=" * 80)
else:
    print("❌ No cache exists - will be created on next LLM request")
