#!/usr/bin/env python3
"""
Test script to check cache debug endpoint
"""
import requests
import json
import sys

def test_cache_debug():
    """Test the cache debug endpoint"""
    base_url = "https://test.talkwithbravo.com"
    
    # You'll need to provide your Firebase ID token here
    # Get this from browser dev tools or frontend
    token = input("Enter your Firebase ID token (from browser dev tools): ").strip()
    
    if not token:
        print("❌ No token provided")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        print("🔍 Checking cache debug endpoint...")
        response = requests.get(f"{base_url}/api/debug/cache", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Cache Debug Response:")
            print(json.dumps(data, indent=2))
            
            # Analyze the cache state
            debug_info = data.get("debug_info", {})
            print("\n📊 Cache Analysis:")
            print(f"User Key: {debug_info.get('user_key')}")
            print(f"Cached Types: {debug_info.get('cached_types')}")
            
            cache_details = debug_info.get("cache_details", {})
            for cache_type, details in cache_details.items():
                print(f"  {cache_type}: {details}")
            
            conv_session = debug_info.get("conversation_session", {})
            print(f"Conversation Session: {conv_session}")
            
            cache_validity = debug_info.get("cache_validity", {})
            print("\n⏰ Cache Validity:")
            for cache_type, validity in cache_validity.items():
                status = "✅ Valid" if validity.get("is_valid") else "❌ Invalid"
                print(f"  {cache_type}: {status}")
                if "age_seconds" in validity:
                    print(f"    Age: {validity['age_seconds']:.1f}s / TTL: {validity['ttl_seconds']}s")
            
            current_data = debug_info.get("current_user_data", {})
            print(f"\n👤 Current User Data:")
            print(f"  Has Mood: {current_data.get('has_mood')}")
            print(f"  Current Mood: {current_data.get('current_mood')}")
            
            return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_cache_debug()
