#!/usr/bin/env python3
"""
Diagnostic script to understand why the context isn't reaching the 1,024 token threshold
despite the LLM requests being 6,000+ tokens.
"""

import asyncio
import sys
import os
import json

# Add current directory to path to import from server.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import (
    cache_manager, 
    load_firestore_document, 
    load_settings_from_file,
    load_birthdays_from_file, 
    load_diary_entries,
    load_chat_history,
    load_pages_from_file,
    DEFAULT_USER_INFO,
    DEFAULT_USER_CURRENT
)

async def analyze_user_data(account_id: str, aac_user_id: str):
    """Analyze all the data components for a user to understand size"""
    
    print(f"\n🔍 ANALYZING DATA FOR USER: {account_id}/{aac_user_id}")
    print("=" * 70)
    
    # Fetch all data components individually
    print("\n📊 FETCHING INDIVIDUAL DATA COMPONENTS...")
    
    try:
        user_info = await load_firestore_document(account_id, aac_user_id, "info/user_narrative", DEFAULT_USER_INFO)
        user_current = await load_firestore_document(account_id, aac_user_id, "info/current_state", DEFAULT_USER_CURRENT)
        settings = await load_settings_from_file(account_id, aac_user_id)
        birthdays = await load_birthdays_from_file(account_id, aac_user_id)
        diary = await load_diary_entries(account_id, aac_user_id)
        chat_history = await load_chat_history(account_id, aac_user_id)
        pages = await load_pages_from_file(account_id, aac_user_id)
        friends_family = await load_firestore_document(account_id, aac_user_id, "info/friends_family", {"friends_family": []})
        
        # Analyze each component
        components = {
            "user_info": user_info,
            "user_current": user_current, 
            "settings": settings,
            "birthdays": birthdays,
            "diary": diary,
            "chat_history": chat_history,
            "pages": pages,
            "friends_family": friends_family
        }
        
        total_size = 0
        for name, data in components.items():
            if data:
                data_str = json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
                size_chars = len(data_str)
                estimated_tokens = size_chars // 3.5
                total_size += size_chars
                
                print(f"   {name:15}: {size_chars:5} chars (~{int(estimated_tokens):4} tokens)")
                
                # Show first 100 chars for debugging
                preview = data_str.replace('\n', ' ')[:100] + "..." if len(data_str) > 100 else data_str
                print(f"                   Preview: {preview}")
                print()
            else:
                print(f"   {name:15}: Empty/None")
                print()
        
        print(f"\n📈 SUMMARY:")
        print(f"   Total raw data: {total_size} chars (~{int(total_size // 3.5)} tokens)")
        
        # Now test the actual cache context building
        print(f"\n🏗️  BUILDING ACTUAL CACHE CONTEXT...")
        cache_context = await cache_manager._build_combined_context_string(account_id, aac_user_id)
        cache_size = len(cache_context)
        cache_tokens = cache_size // 3.5
        
        print(f"   Cache context: {cache_size} chars (~{int(cache_tokens)} tokens)")
        print(f"   Meets 1,024 threshold: {'✅ YES' if cache_tokens >= 1024 else '❌ NO'}")
        
        if cache_tokens < 1024:
            deficit = 1024 - cache_tokens
            print(f"   Deficit: {int(deficit)} tokens needed")
            print(f"   Additional chars needed: ~{int(deficit * 3.5)}")
        
        # Show the actual cache context structure
        print(f"\n📝 CACHE CONTEXT STRUCTURE:")
        lines = cache_context.split('\n')
        for i, line in enumerate(lines[:10]):  # First 10 lines
            print(f"   {i+1:2}: {line[:80]}")
        if len(lines) > 10:
            print(f"   ... ({len(lines)-10} more lines)")
            
        return cache_tokens >= 1024, cache_tokens, cache_context
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, ""

async def main():
    """Main function to run the analysis"""
    
    # You can modify these to match your test user
    account_id = "wlJedVV4jMapxLxPHjBe2dMBwaD2"  # Replace with actual account ID
    aac_user_id = "7fdc7994-2a51-43d5-973f-841b496ac038"  # Replace with actual user ID
    
    print("🚀 DATA SIZE DIAGNOSTIC TOOL")
    print(f"Account ID: {account_id}")
    print(f"User ID: {aac_user_id}")
    
    can_cache, token_count, context = await analyze_user_data(account_id, aac_user_id)
    
    print(f"\n🎯 FINAL RESULT:")
    print(f"   Can create cache: {'✅ YES' if can_cache else '❌ NO'}")
    print(f"   Token count: {int(token_count)}")
    print(f"   Minimum needed: 1,024")
    
    if not can_cache:
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   1. Add more user data to Firestore")
        print(f"   2. Include more diary entries (currently limited to 5)")
        print(f"   3. Include more chat history (currently limited to 5)")
        print(f"   4. Add more detailed user profile information")
        
    return can_cache

if __name__ == "__main__":
    asyncio.run(main())
