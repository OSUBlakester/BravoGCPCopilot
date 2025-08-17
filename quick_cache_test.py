#!/usr/bin/env python3
"""
Quick Cache Verification Script

This script does a basic check to see if the cache endpoints are working.
Run this while your server is running to verify cache functionality.
"""

import requests
import json
import time
import sys

def test_cache_endpoints(base_url="http://localhost:8000"):
    """Quick test of cache endpoints"""
    print("🔍 Quick Cache Functionality Check")
    print("=" * 40)
    
    # Test 1: Cache Stats
    print("1. Testing cache stats endpoint...")
    try:
        response = requests.get(f"{base_url}/api/cache/stats", timeout=10)
        if response.status_code == 200:
            print("   ✅ Cache stats endpoint working")
            stats = response.json()
            print(f"   📊 Stats: {json.dumps(stats, indent=2)}")
        else:
            print(f"   ❌ Cache stats failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Cache stats error: {e}")
    
    print()
    
    # Test 2: Cache Refresh
    print("2. Testing cache refresh endpoint...")
    try:
        response = requests.post(f"{base_url}/api/cache/refresh", timeout=10)
        if response.status_code == 200:
            print("   ✅ Cache refresh endpoint working")
            result = response.json()
            print(f"   🔄 Result: {json.dumps(result, indent=2)}")
        else:
            print(f"   ❌ Cache refresh failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Cache refresh error: {e}")
    
    print()
    
    # Test 3: Basic LLM Performance Test
    print("3. Testing LLM performance (basic)...")
    test_prompt = "Hello, this is a cache test"
    
    try:
        # First call
        print("   Making first LLM call...")
        start_time = time.time()
        response = requests.post(
            f"{base_url}/llm",
            json={"prompt": test_prompt},
            timeout=30
        )
        first_call_time = time.time() - start_time
        
        if response.status_code == 200:
            print(f"   ✅ First call successful: {first_call_time:.2f}s")
        else:
            print(f"   ❌ First call failed: {response.status_code}")
            return
        
        # Second call
        print("   Making second LLM call...")
        start_time = time.time()
        response = requests.post(
            f"{base_url}/llm",
            json={"prompt": test_prompt + " (second call)"},
            timeout=30
        )
        second_call_time = time.time() - start_time
        
        if response.status_code == 200:
            print(f"   ✅ Second call successful: {second_call_time:.2f}s")
            
            # Calculate improvement
            if first_call_time > 0:
                improvement = ((first_call_time - second_call_time) / first_call_time) * 100
                if improvement > 0:
                    print(f"   🚀 Performance improvement: {improvement:.1f}%")
                else:
                    print(f"   📈 Second call was {abs(improvement):.1f}% slower (expected on first runs)")
        else:
            print(f"   ❌ Second call failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ LLM performance test error: {e}")
    
    print()
    print("=" * 40)
    print("✨ Quick cache check complete!")
    print()
    print("💡 Tips:")
    print("   - Run multiple times to see cache warming effects")
    print("   - Check server logs for detailed cache hit rates")
    print("   - Use the full test suite for comprehensive testing")

def check_server_running(base_url="http://localhost:8000"):
    """Check if server is running"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        return response.status_code == 200
    except:
        try:
            # Try the root endpoint if health doesn't exist
            response = requests.get(base_url, timeout=5)
            return response.status_code in [200, 404]  # 404 is fine, means server is up
        except:
            return False

if __name__ == "__main__":
    base_url = "http://localhost:8000"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"Testing cache functionality at: {base_url}")
    print()
    
    # Check if server is running
    if not check_server_running(base_url):
        print("❌ Server doesn't appear to be running!")
        print("   Please start your server first:")
        print("   python server.py")
        print("   # or")
        print("   ./deploy.sh test")
        sys.exit(1)
    
    print("✅ Server is running")
    print()
    
    test_cache_endpoints(base_url)
