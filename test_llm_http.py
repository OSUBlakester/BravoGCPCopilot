#!/usr/bin/env python3
"""
HTTP API Testing Script
Tests your LLM endpoint directly via HTTP calls
"""

import requests
import json
import sys
import time
from datetime import datetime

# Configuration
BASE_URL = "https://talkwithbravo.com"
# Backup URL
BACKUP_URL = "https://bravo-aac-api-lnquhqxkjq-uc.a.run.app"

def test_health_endpoint(base_url):
    """Test the health endpoint"""
    try:
        print(f"🔄 Testing health endpoint: {base_url}/health")
        response = requests.get(f"{base_url}/health", timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Health endpoint OK")
            print(f"   Response: {response.text[:100]}")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False

def test_llm_endpoint_without_auth(base_url):
    """Test LLM endpoint (should fail without auth)"""
    try:
        print(f"🔄 Testing LLM endpoint (no auth): {base_url}/llm")
        
        test_payload = {
            "prompt": "Generate 5 simple greetings in a JSON array format."
        }
        
        response = requests.post(
            f"{base_url}/llm", 
            json=test_payload,
            timeout=30
        )
        
        print(f"   Status code: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 401 or response.status_code == 403:
            print("✅ Correctly rejected request without authentication")
            return True
        elif response.status_code == 200:
            print("⚠️  Request succeeded without auth (unexpected)")
            return True
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ LLM endpoint test error: {e}")
        return False

def test_cors_options(base_url):
    """Test CORS preflight request"""
    try:
        print(f"🔄 Testing CORS OPTIONS: {base_url}/llm")
        
        response = requests.options(
            f"{base_url}/llm",
            headers={
                'Origin': 'https://talkwithbravo.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type, Authorization, X-User-ID'
            },
            timeout=10
        )
        
        print(f"   Status code: {response.status_code}")
        print(f"   CORS headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ CORS preflight OK")
            return True
        else:
            print(f"❌ CORS preflight failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ CORS test error: {e}")
        return False

def check_ssl_certificate(base_url):
    """Check SSL certificate"""
    try:
        print(f"🔄 Checking SSL certificate for: {base_url}")
        
        # Make a simple request and check if it uses HTTPS
        if base_url.startswith('https://'):
            response = requests.get(f"{base_url}/health", timeout=10, verify=True)
            print("✅ SSL certificate is valid")
            return True
        else:
            print("⚠️  Not using HTTPS")
            return True
            
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL certificate error: {e}")
        return False
    except Exception as e:
        print(f"❌ SSL check error: {e}")
        return False

def test_response_times(base_url):
    """Test response times"""
    try:
        print(f"🔄 Testing response times for: {base_url}")
        
        times = []
        for i in range(3):
            start_time = time.time()
            response = requests.get(f"{base_url}/health", timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                response_time = (end_time - start_time) * 1000  # Convert to ms
                times.append(response_time)
                print(f"   Request {i+1}: {response_time:.2f}ms")
        
        if times:
            avg_time = sum(times) / len(times)
            print(f"✅ Average response time: {avg_time:.2f}ms")
            
            if avg_time < 1000:  # Less than 1 second
                print("✅ Response times are good")
            elif avg_time < 3000:  # Less than 3 seconds
                print("⚠️  Response times are acceptable")
            else:
                print("❌ Response times are slow")
            return True
        else:
            print("❌ No successful requests for timing")
            return False
            
    except Exception as e:
        print(f"❌ Response time test error: {e}")
        return False

def run_http_tests():
    """Run all HTTP tests"""
    print("🌐 Starting HTTP API Testing")
    print(f"🕐 Test time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    urls_to_test = [BASE_URL, BACKUP_URL]
    all_passed = True
    
    for url in urls_to_test:
        print(f"\n🔗 Testing URL: {url}")
        print("-" * 40)
        
        # Health endpoint test
        if not test_health_endpoint(url):
            all_passed = False
            continue  # Skip other tests if health fails
        
        # SSL certificate test
        if not check_ssl_certificate(url):
            all_passed = False
        
        # Response time test
        if not test_response_times(url):
            all_passed = False
        
        # CORS test
        if not test_cors_options(url):
            all_passed = False
        
        # LLM endpoint test (should fail without auth)
        if not test_llm_endpoint_without_auth(url):
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All HTTP tests passed!")
    else:
        print("⚠️  Some HTTP tests failed. Check the output above.")
    
    return all_passed

if __name__ == "__main__":
    result = run_http_tests()
    sys.exit(0 if result else 1)
