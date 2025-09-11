#!/usr/bin/env python3
"""
Simple mood debug script
"""
import requests
import json

# Test with your test environment
BASE_URL = "https://test.talkwithbravo.com"

def test_mood_debug():
    print("🔍 Simple Mood Debug Test")
    print("=" * 40)
    
    # Test health endpoint first
    print("\n1. Testing health endpoint:")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Health Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Server is healthy")
        else:
            print("❌ Server health check failed")
            return
    except Exception as e:
        print(f"❌ Cannot reach server: {e}")
        return
    
    # Test user-info endpoint
    print("\n2. Testing user info:")
    try:
        response = requests.get(f"{BASE_URL}/api/user-info", timeout=10)
        print(f"User Info Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            current_mood = data.get('currentMood')
            print(f"Current Mood from API: '{current_mood}'")
            
            if current_mood:
                print(f"✅ Mood is set: {current_mood}")
            else:
                print("❌ No mood set in user info")
                
        elif response.status_code == 401:
            print("❌ Authentication required - this might be expected for test environment")
        else:
            print(f"❌ Error: {response.status_code} - {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test with a simple prompt to see server logs
    print("\n3. Testing simple LLM call:")
    try:
        response = requests.post(
            f"{BASE_URL}/llm",
            json={"prompt": "Generate 1 simple greeting"},
            timeout=15
        )
        print(f"LLM Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ LLM responded with {len(result)} items")
            if result:
                print(f"First greeting: {result[0].get('option', 'No option')}")
        elif response.status_code == 401:
            print("❌ Authentication required for LLM endpoint")
        else:
            print(f"❌ LLM Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ LLM Error: {e}")

if __name__ == "__main__":
    test_mood_debug()
