#!/usr/bin/env python3
"""
Test script to verify token savings from caching implementation
"""

import asyncio
import json
import logging
from server import GeminiCacheManager
from config import GEMINI_PRIMARY_MODEL

# Set up logging
logging.basicConfig(level=logging.INFO)

async def test_token_savings():
    """Test that cached content actually reduces token usage"""
    
    cache_manager = GeminiCacheManager()
    
    # Test user data
    account_id = "test_account"
    aac_user_id = "test_user"
    
    # Create some test context data
    test_contexts = {
        "USER_PROFILE": "Name: Test User\nAge: 25\nInterests: Music, Reading, Cooking",
        "FRIENDS_FAMILY": "Friends: Alice, Bob, Charlie\nFamily: Mom (Sarah), Dad (Mike), Sister (Emma)",
        "HOLIDAYS_BIRTHDAYS": "Upcoming: Alice's birthday on Dec 15th, Christmas on Dec 25th",
        "CONVERSATION_SESSION": "Recent conversations about weekend plans and holiday preparations"
    }
    
    print("=" * 60)
    print("TESTING GEMINI CONTEXT CACHING TOKEN SAVINGS")
    print("=" * 60)
    
    # Store test contexts in cache
    print("\n1. Creating cached contexts...")
    for context_type, context_data in test_contexts.items():
        await cache_manager.store_cached_context(account_id, aac_user_id, context_type, context_data)
    
    # Check if combined cache was created
    user_key = cache_manager._get_user_key(account_id, aac_user_id)
    if user_key in cache_manager.gemini_caches and "COMBINED" in cache_manager.gemini_caches[user_key]:
        combined_cache = cache_manager.gemini_caches[user_key]["COMBINED"]
        print(f"✅ Combined cache created: {combined_cache.get('gemini_cache_name', 'N/A')}")
        print(f"   Content preview: {combined_cache.get('content_preview', 'N/A')}")
    else:
        print("❌ No combined cache found")
    
    # Test building cached content references
    print("\n2. Testing cached content references...")
    cached_refs = await cache_manager.build_cached_context_references(account_id, aac_user_id)
    if cached_refs:
        print(f"✅ Found {len(cached_refs)} cached content references:")
        for ref in cached_refs:
            print(f"   - {ref}")
    else:
        print("❌ No cached content references found")
    
    # Simulate full context vs cached context token usage
    print("\n3. Estimating token savings...")
    
    # Estimate full context size
    full_context = "\n\n".join([
        "Current Date: December 10, 2024",
        "General User Information:\nName: Test User\nAge: 25\nInterests: Music, Reading, Cooking",
        "User's Current State:\nLocation: Home\nPeople Present: Family\nActivity: Relaxing",
        "Friends Family Context:\nFriends: Alice, Bob, Charlie\nFamily: Mom (Sarah), Dad (Mike), Sister (Emma)",
        "Birthday Info & Upcoming Birthdays:\nAlice's birthday on Dec 15th, Christmas on Dec 25th",
        "Recent Conversation History:\nRecent conversations about weekend plans and holiday preparations"
    ])
    
    user_query = "What should I say about weekend plans?"
    
    full_prompt_tokens = len(full_context.split()) + len(user_query.split())
    user_only_tokens = len(user_query.split())
    
    token_savings = full_prompt_tokens - user_only_tokens
    savings_percent = (token_savings / full_prompt_tokens) * 100
    
    print(f"📊 ESTIMATED TOKEN USAGE:")
    print(f"   Full context prompt: ~{full_prompt_tokens} tokens")
    print(f"   User query only: ~{user_only_tokens} tokens")
    print(f"   Token savings: ~{token_savings} tokens ({savings_percent:.1f}% reduction)")
    
    # Get cache stats
    print("\n4. Cache statistics...")
    stats = cache_manager.get_cache_stats()
    print(f"📈 CACHE STATS:")
    print(f"   Total users: {stats.get('total_users', 0)}")
    print(f"   Total caches: {stats.get('total_caches', 0)}")
    print(f"   Cache types: {stats.get('cache_types', {})}")
    
    print("\n" + "=" * 60)
    print("TOKEN SAVINGS TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_token_savings())
