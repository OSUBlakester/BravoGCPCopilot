#!/usr/bin/env python3
"""
Test script to verify AAC-Image service integration
Run this after deployment completes to test the integration
"""
import requests
import json
import time

# Service URLs
AAC_SERVICE = "https://bravo-aac-api-894197055102.us-central1.run.app"
IMAGE_SERVICE = "https://bravo-image-api-894197055102.us-central1.run.app"

def test_service_health():
    """Test both services are healthy"""
    print("🔍 Testing service health...")
    
    try:
        # Test AAC service
        aac_response = requests.get(f"{AAC_SERVICE}/health", timeout=10)
        print(f"✅ AAC Service: {aac_response.status_code} - {aac_response.json().get('status', 'unknown')}")
        
        # Test Image service
        img_response = requests.get(f"{IMAGE_SERVICE}/health", timeout=10)
        print(f"✅ Image Service: {img_response.status_code} - {img_response.json().get('status', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"❌ Service health check failed: {e}")
        return False

def test_image_integration_endpoints():
    """Test the new image integration endpoints on AAC service"""
    print("\n🔗 Testing image integration endpoints...")
    
    endpoints_to_test = [
        "/api/images/search",
        "/api/images/generate-prompts",
    ]
    
    for endpoint in endpoints_to_test:
        try:
            if endpoint == "/api/images/search":
                # Test image search
                response = requests.post(
                    f"{AAC_SERVICE}{endpoint}",
                    json={"tags": ["test"], "limit": 5},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            elif endpoint == "/api/images/generate-prompts":
                # Test prompt generation
                response = requests.post(
                    f"{AAC_SERVICE}{endpoint}",
                    json={"concept": "family", "num_variations": 2},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            
            if response.status_code == 200:
                print(f"✅ {endpoint}: Working")
            else:
                print(f"⚠️ {endpoint}: {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            print(f"❌ {endpoint}: Failed - {e}")

def test_direct_image_service():
    """Test direct calls to image service for comparison"""
    print("\n🖼️ Testing direct image service calls...")
    
    try:
        # Test search
        search_response = requests.post(
            f"{IMAGE_SERVICE}/search_images",
            json={"tags": ["test"], "limit": 3},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if search_response.status_code == 200:
            images = search_response.json().get('images', [])
            print(f"✅ Direct image search: Found {len(images)} images")
        else:
            print(f"⚠️ Direct image search: {search_response.status_code}")
            
    except Exception as e:
        print(f"❌ Direct image service test failed: {e}")

def main():
    """Run all integration tests"""
    print("🚀 AAC-Image Integration Test Suite")
    print("=" * 50)
    
    # Test 1: Service health
    if not test_service_health():
        print("❌ Services not healthy, skipping integration tests")
        return
    
    # Wait a moment for services to be ready
    print("\n⏱️ Waiting 5 seconds for services to be ready...")
    time.sleep(5)
    
    # Test 2: Integration endpoints
    test_image_integration_endpoints()
    
    # Test 3: Direct image service (for comparison)
    test_direct_image_service()
    
    print("\n🎉 Integration test complete!")
    print("📝 Check the results above to verify everything is working")

if __name__ == "__main__":
    main()
