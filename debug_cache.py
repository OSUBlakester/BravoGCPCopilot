#!/usr/bin/env python3

"""
Debug script to check cache contents and verify user data is being cached properly
"""

import asyncio
import sys
import os
import logging
from datetime import datetime as dt

# Add the current directory to Python path to import server modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from server
from server import GeminiCacheManager, CacheType

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def debug_cache_contents():
    """Debug what's currently in the cache for a test user"""
    
    # Test with a realistic account/user combo
    account_id = "Blake"  # Use the Blake account we know exists
    aac_user_id = "Blake"  # Use Blake user
    
    print(f"\n🔍 Debugging cache contents for account_id='{account_id}', aac_user_id='{aac_user_id}'")
    print("=" * 80)
    
    # Create cache manager
    cache_manager = GeminiCacheManager()
    user_key = cache_manager._get_user_key(account_id, aac_user_id)
    print(f"User key: {user_key}")
    
    # Check if user has any cached data
    print(f"\nGeneral cache state:")
    print(f"- Total users in cache: {len(cache_manager.gemini_caches)}")
    print(f"- User key exists in cache: {user_key in cache_manager.gemini_caches}")
    
    if user_key in cache_manager.gemini_caches:
        user_caches = cache_manager.gemini_caches[user_key]
        print(f"- Cache types for this user: {list(user_caches.keys())}")
        
        # Check each cache type
        for cache_type in [CacheType.USER_PROFILE, CacheType.FRIENDS_FAMILY, 
                          CacheType.HOLIDAYS_BIRTHDAYS, CacheType.USER_SETTINGS]:
            
            cached_data = await cache_manager.get_cached_context(account_id, aac_user_id, cache_type)
            print(f"\n📋 {cache_type}:")
            if cached_data:
                if isinstance(cached_data, dict):
                    print(f"  Type: dict with keys {list(cached_data.keys())}")
                    for key, value in cached_data.items():
                        if isinstance(value, str):
                            preview = value[:100] + "..." if len(value) > 100 else value
                        else:
                            preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                        print(f"    {key}: {preview}")
                elif isinstance(cached_data, str):
                    if cached_data.startswith("cachedContents/"):
                        print(f"  Type: Gemini cache reference: {cached_data}")
                    else:
                        preview = cached_data[:100] + "..." if len(cached_data) > 100 else cached_data
                        print(f"  Type: string content: {preview}")
                else:
                    print(f"  Type: {type(cached_data)}: {str(cached_data)[:100]}")
            else:
                print(f"  ❌ No cached data found")
    
    # Try to force cache a simple test
    print(f"\n🔄 Testing cache storage...")
    test_data = {
        "user_info": "Test user info content",
        "user_current": "Test current state"
    }
    
    await cache_manager.store_cached_context(account_id, aac_user_id, CacheType.USER_PROFILE, test_data)
    print(f"✅ Stored test data in USER_PROFILE cache")
    
    # Verify it was stored
    retrieved_data = await cache_manager.get_cached_context(account_id, aac_user_id, CacheType.USER_PROFILE)
    print(f"📥 Retrieved data: {retrieved_data}")
    
    # Check if combined cache exists
    print(f"\n🔄 Checking combined cache...")
    if user_key in cache_manager.gemini_caches and "COMBINED" in cache_manager.gemini_caches[user_key]:
        combined_cache = cache_manager.gemini_caches[user_key]["COMBINED"]
        print(f"✅ Combined cache exists:")
        print(f"  Gemini cache name: {combined_cache.get('gemini_cache_name')}")
        print(f"  Created at: {dt.fromtimestamp(combined_cache.get('created_at', 0))}")
        print(f"  TTL: {combined_cache.get('ttl')} seconds")
        print(f"  Content preview: {combined_cache.get('content_preview')}")
    else:
        print(f"❌ No combined cache found")
        
        # Try to trigger combined cache creation
        print(f"\n🔄 Attempting to trigger combined cache creation...")
        try:
            # This should trigger cache building
            session = await cache_manager.get_or_create_conversation_session(account_id, aac_user_id)
            print(f"✅ Got conversation session: {session is not None}")
            
            # Check again for combined cache
            if user_key in cache_manager.gemini_caches and "COMBINED" in cache_manager.gemini_caches[user_key]:
                combined_cache = cache_manager.gemini_caches[user_key]["COMBINED"]
                print(f"✅ Combined cache created:")
                print(f"  Gemini cache name: {combined_cache.get('gemini_cache_name')}")
                print(f"  Content preview: {combined_cache.get('content_preview')}")
            else:
                print(f"❌ Combined cache still not created")
                
        except Exception as e:
            print(f"❌ Error creating conversation session: {e}")

if __name__ == "__main__":
    asyncio.run(debug_cache_contents())
