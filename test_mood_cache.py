#!/usr/bin/env python3
"""
Test script to check if mood is properly stored in cache and user profile
"""
import asyncio
import requests
import json
import sys

# Test with your test environment
BASE_URL = "https://test.talkwithbravo.com"

async def test_mood_cache():
    """Test mood storage and cache"""
    
    print("🔍 Testing Mood Cache and User Profile...")
    print("=" * 50)
    
    # Test 1: Check user info endpoint
    print("\n1. Testing /api/user-info endpoint:")
    try:
        response = requests.get(f"{BASE_URL}/api/user-info", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            current_mood = data.get('currentMood')
            user_info = data.get('userInfo', '')
            
            print(f"Current Mood: {current_mood}")
            print(f"User Info Length: {len(user_info)} characters")
            
            if current_mood:
                print(f"✅ Mood found in user info: '{current_mood}'")
            else:
                print("❌ No mood found in user info")
        else:
            print(f"❌ Failed to get user info: {response.text}")
    except Exception as e:
        print(f"❌ Error testing user info: {e}")
    
    # Test 2: Check cache stats
    print("\n2. Testing /api/cache/stats endpoint:")
    try:
        response = requests.get(f"{BASE_URL}/api/cache/stats", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            cache_stats = response.json()
            print("Cache Statistics:")
            print(json.dumps(cache_stats, indent=2))
            
            # Look for USER_PROFILE cache
            user_profile_cache = cache_stats.get('cache_entries', {}).get('USER_PROFILE')
            if user_profile_cache:
                print(f"✅ USER_PROFILE cache found")
                if 'current_mood' in str(user_profile_cache):
                    print(f"✅ Mood appears to be in USER_PROFILE cache")
                else:
                    print(f"❌ Mood not visible in USER_PROFILE cache")
            else:
                print("❌ No USER_PROFILE cache found")
        else:
            print(f"❌ Failed to get cache stats: {response.text}")
    except Exception as e:
        print(f"❌ Error testing cache stats: {e}")
    
    # Test 3: Test LLM endpoint with mood-sensitive prompt
    print("\n3. Testing LLM endpoint with mood-sensitive greeting:")
    try:
        test_prompt = "Generate 3 generic greetings. Each greeting should reflect my current mood and be appropriate for how I'm feeling."
        
        response = requests.post(
            f"{BASE_URL}/llm",
            json={"prompt": test_prompt},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            greetings = response.json()
            print(f"✅ Received {len(greetings)} greetings:")
            for i, greeting in enumerate(greetings, 1):
                option_text = greeting.get('option', 'No option text')
                print(f"  {i}. {option_text}")
            
            # Check if any greeting seems mood-aware
            greeting_text = ' '.join([g.get('option', '') for g in greetings]).lower()
            mood_indicators = ['happy', 'sad', 'excited', 'calm', 'tired', 'anxious', 'feeling', 'mood']
            mood_aware = any(indicator in greeting_text for indicator in mood_indicators)
            
            if mood_aware:
                print(f"✅ Greetings appear to be mood-aware")
            else:
                print(f"❌ Greetings don't seem to reflect mood")
                
        else:
            print(f"❌ Failed to get LLM response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing LLM endpoint: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Mood cache test complete!")

if __name__ == "__main__":
    asyncio.run(test_mood_cache())
