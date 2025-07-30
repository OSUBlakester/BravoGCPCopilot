#!/usr/bin/env python3
"""
Complete LLM Service Test
Tests the actual LLM endpoint of your deployed service with authentication simulation
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://talkwithbravo.com"
TEST_PROMPT = "Generate #LLMOptions simple greeting phrases. Return as a JSON array."

def test_llm_service_recovery():
    """Test if the LLM service has recovered"""
    print("🔄 Testing LLM Service Recovery")
    print(f"🕐 Test time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Test health endpoint first
    print("1️⃣ Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health endpoint OK")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False
    
    # Wait for potential cold start
    print("\n2️⃣ Waiting for service warm-up (10 seconds)...")
    time.sleep(10)
    
    # Test LLM endpoint without auth (should get proper error, not 503)
    print("3️⃣ Testing LLM endpoint response...")
    try:
        test_payload = {"prompt": TEST_PROMPT}
        response = requests.post(
            f"{BASE_URL}/llm", 
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"   Status code: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 503:
            print("❌ Service still returning 503 - LLM not initialized")
            return False
        elif response.status_code == 403 or response.status_code == 401:
            print("✅ LLM service is responding (authentication required)")
            return True
        elif response.status_code == 200:
            print("⚠️  Unexpected success without auth")
            return True
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ LLM endpoint test error: {e}")
        return False

def monitor_service_startup():
    """Monitor the service until it's ready"""
    print("🔄 Monitoring LLM Service Startup")
    print("=" * 60)
    
    max_attempts = 12  # 2 minutes with 10-second intervals
    attempt = 1
    
    while attempt <= max_attempts:
        print(f"\n📊 Attempt {attempt}/{max_attempts} at {datetime.now().strftime('%H:%M:%S')}")
        
        if test_llm_service_recovery():
            print(f"\n🎉 LLM service is ready after {attempt} attempts!")
            return True
        
        if attempt < max_attempts:
            print("⏳ Waiting 10 seconds before next check...")
            time.sleep(10)
        
        attempt += 1
    
    print(f"\n❌ LLM service did not recover after {max_attempts} attempts")
    return False

def suggest_fixes():
    """Suggest potential fixes"""
    print("\n🔧 Troubleshooting Suggestions:")
    print("=" * 60)
    print("1. Check Cloud Run logs:")
    print("   gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=bravo-aac-api\" --limit=10")
    print()
    print("2. Restart the Cloud Run service:")
    print("   gcloud run services update bravo-aac-api --region=us-central1 --project=bravo-prod-465323")
    print()
    print("3. Check environment variables:")
    print("   gcloud run services describe bravo-aac-api --region=us-central1 --format=\"value(spec.template.spec.template.spec.containers[0].env[].name)\"")
    print()
    print("4. Redeploy the service:")
    print("   ./deploy.sh prod")

if __name__ == "__main__":
    print("🧪 LLM Service Recovery Test")
    
    # Run immediate test
    if test_llm_service_recovery():
        print("\n✅ LLM service is already working!")
    else:
        print("\n⚠️  LLM service needs recovery. Starting monitoring...")
        if not monitor_service_startup():
            suggest_fixes()
    
    print("\n" + "=" * 60)
    print("Test completed.")
