#!/usr/bin/env python3

import asyncio
import json
import requests
from datetime import datetime

# Configuration for testing
BASE_URL = "https://test.talkwithbravo.com"
FIREBASE_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjU3YmZiMmExMWRkZmZjMGFkMmU2ODE0YzY4NzYzYjhjNjg3NTgxZDgiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vYnJhdm8tdGVzdC00NjU0MDAiLCJhdWQiOiJicmF2by10ZXN0LTQ2NTQwMCIsImF1dGhfdGltZSI6MTc1NTUxOTYxNywidXNlcl9pZCI6IndsSmVkVlY0ak1hcHhMeFBIakJlMmRNQndhRDIiLCJzdWIiOiJ3bEplZFZWNGpNYXB4THhQSGpCZTJkTUJ3YUQyIiwiaWF0IjoxNzU1NTE5NjE3LCJleHAiOjE3NTU1MjMyMTcsImVtYWlsIjoiYnJhZHl0aG9tYXM5OUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnsiZW1haWwiOlsiYnJhZHl0aG9tYXM5OUBnbWFpbC5jb20iXX0sInNpZ25faW5fcHJvdmlkZXIiOiJwYXNzd29yZCJ9fQ.CRofX9ArEkqARh2I8d0iGnWmyNVJmhcFArgqB5kCM1fWgGPJvuo8dY3YDyoZINw5CflwrqWJDGjHg9et4hrO8RgEiruvvESVDGxGpLjCUdhKHMwt2f_g-3dhkUNUkyoXp032TyX6g4vwWIPushM_cxsWnj2JkJvyByMcWKaHsaJKfNEqhwZS47zZ1gAq3UK3b8c5DvtBt1NS-Psj1TXDXH4Akhej-v2GIQdevitogGxKCozAFWe6ZKPoU90HD4QxC0ubvnZufmnv-p-R_mx53RAb8mpAoEzimywPsr520xRuDT9S1F2P6u5TBM4wH7CfYt9cQOYhE2_FzrftXWns2g"
USER_ID = "7fdc7994-2a51-43d5-973f-841b496ac038"

def test_cache_creation_trigger():
    """Test cache creation by making an LLM call to trigger cache updates"""
    
    headers = {
        "Authorization": f"Bearer {FIREBASE_TOKEN}",
        "X-User-ID": USER_ID,
        "Content-Type": "application/json"
    }
    
    print("🔍 Step 1: Check current cache state")
    response = requests.get(f"{BASE_URL}/api/debug/cache", headers=headers)
    if response.status_code == 200:
        cache_data = response.json()
        print(f"   Current cached types: {cache_data['debug_info']['cached_types']}")
        has_combined = "COMBINED" in cache_data['debug_info']['cached_types']
        print(f"   Has COMBINED cache: {has_combined}")
        
        if has_combined:
            combined_details = cache_data['debug_info']['cache_details'].get('COMBINED', {})
            print(f"   COMBINED cache details: {json.dumps(combined_details, indent=2)}")
        else:
            print("   ❌ No COMBINED cache found")
    
    print("\n🚀 Step 2: Change mood to trigger cache invalidation")
    mood_payload = {
        "userInfo": "",  # Keep existing user info
        "currentMood": "Excited"  # Change mood to trigger cache update
    }
    
    response = requests.post(f"{BASE_URL}/api/user-info", headers=headers, json=mood_payload)
    print(f"   Mood change response status: {response.status_code}")
    
    if response.status_code == 200:
        mood_data = response.json()
        print(f"   Mood saved successfully: {mood_data.get('currentMood')}")
    else:
        print(f"   ❌ Mood change failed: {response.text}")
        
    print("\n🚀 Step 3: Make LLM call to trigger cache creation")
    llm_payload = {
        "prompt": "How are you feeling today?"
    }
    
    response = requests.post(f"{BASE_URL}/llm", headers=headers, json=llm_payload)
    print(f"   LLM response status: {response.status_code}")
    
    if response.status_code == 200:
        llm_data = response.json()
        print(f"   LLM response received: {len(str(llm_data))} chars")
    else:
        print(f"   ❌ LLM call failed: {response.text}")
        return
    
    print("\n🔍 Step 4: Check cache state after mood change and LLM call")
    response = requests.get(f"{BASE_URL}/api/debug/cache", headers=headers)
    if response.status_code == 200:
        cache_data = response.json()
        print(f"   Updated cached types: {cache_data['debug_info']['cached_types']}")
        has_combined = "COMBINED" in cache_data['debug_info']['cached_types']
        print(f"   Has COMBINED cache now: {has_combined}")
        
        if has_combined:
            combined_details = cache_data['debug_info']['cache_details'].get('COMBINED', {})
            print(f"   COMBINED cache details: {json.dumps(combined_details, indent=2)}")
        else:
            print("   ❌ Still no COMBINED cache created")
            
        # Check if any cache references start with "cachedContents/"
        gemini_cache_count = 0
        for cache_type, details in cache_data['debug_info']['cache_details'].items():
            if details.get('is_gemini_cache', False):
                gemini_cache_count += 1
                print(f"   ✅ {cache_type} is Gemini cached: {details.get('gemini_cache_name')}")
        
        if gemini_cache_count == 0:
            print("   ❌ No Gemini cached content found - all caches are local only")
        else:
            print(f"   ✅ Found {gemini_cache_count} Gemini cached content entries")

if __name__ == "__main__":
    print("=== Cache Creation Debug Test ===")
    test_cache_creation_trigger()
