#!/usr/bin/env python3
"""
Test script to verify cache warming is working during authentication
"""

import requests
import json
import time

BASE_URL = "http://localhost:8080"  # Change this to your server URL

def test_cache_warming():
    """Test that cache is created during authentication"""
    
    print("=== Cache Warming Test ===")
    print(f"Testing against: {BASE_URL}")
    
    # Headers with fake authentication for testing
    headers = {
        "Authorization": "Bearer test-token",
        "X-User-ID": "testuser",
        "Content-Type": "application/json"
    }
    
    print("\n1. Testing cache debug endpoint to check initial state...")
    try:
        response = requests.get(f"{BASE_URL}/api/debug/cache", headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            cache_data = response.json()
            print("Cache debug response:")
            print(json.dumps(cache_data, indent=2))
            
            # Check if COMBINED cache exists
            cache_info = cache_data.get("cache_info", {})
            combined_cache = cache_info.get("COMBINED")
            
            if combined_cache:
                print("✅ COMBINED cache found!")
                print(f"   Cache created: {combined_cache.get('created_at')}")
                print(f"   Is valid: {combined_cache.get('is_valid')}")
                
                # Check cache contents
                cache_contents = cache_data.get("cache_contents", {})
                if cache_contents:
                    print(f"   Available contexts: {list(cache_contents.keys())}")
                    for ctx_type, content in cache_contents.items():
                        if isinstance(content, dict):
                            print(f"     {ctx_type}: {len(str(content))} chars")
                        else:
                            print(f"     {ctx_type}: {len(content)} chars")
                else:
                    print("   No cache contents found")
            else:
                print("❌ No COMBINED cache found")
                print("   This suggests cache warming either failed or hasn't been triggered")
                
                # List what caches are available
                available_caches = list(cache_info.keys())
                if available_caches:
                    print(f"   Available caches: {available_caches}")
                else:
                    print("   No caches available at all")
        else:
            print(f"❌ Debug endpoint failed: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on the specified URL.")
        return False
    except Exception as e:
        print(f"❌ Error testing cache: {e}")
        return False
    
    print("\n2. Testing user-info endpoint to trigger potential cache creation...")
    try:
        response = requests.get(f"{BASE_URL}/api/user-info", headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ User-info endpoint accessible")
            
            # Wait a moment for background cache warming
            print("   Waiting 3 seconds for background cache warming...")
            time.sleep(3)
            
            # Check cache again
            print("   Checking cache status after user-info call...")
            response = requests.get(f"{BASE_URL}/api/debug/cache", headers=headers)
            if response.status_code == 200:
                cache_data = response.json()
                cache_info = cache_data.get("cache_info", {})
                combined_cache = cache_info.get("COMBINED")
                
                if combined_cache:
                    print("✅ COMBINED cache now exists!")
                else:
                    print("❌ Still no COMBINED cache after user-info call")
                    print("   This suggests cache warming is not working as expected")
            
        else:
            print(f"❌ User-info endpoint failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing user-info: {e}")
    
    print("\n=== Test Complete ===")
    return True

if __name__ == "__main__":
    test_cache_warming()
