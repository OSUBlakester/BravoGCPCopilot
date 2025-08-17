#!/usr/bin/env python3
"""
Test Frontend Configuration Endpoint

This script tests the /api/frontend-config endpoint that was causing
the "Invalid configuration received from server" error in auth.html.
"""

import requests
import json
import sys

def test_frontend_config(base_url="http://localhost:8000"):
    """Test the frontend configuration endpoint"""
    print("🔍 Testing Frontend Configuration Endpoint")
    print("=" * 50)
    
    endpoint = f"{base_url}/api/frontend-config"
    print(f"Testing: {endpoint}")
    
    try:
        response = requests.get(endpoint, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                config = response.json()
                print("✅ Configuration received successfully!")
                print("\nConfiguration contents:")
                print(json.dumps(config, indent=2))
                
                # Validate required fields
                required_fields = ['apiKey', 'authDomain', 'projectId', 'storageBucket', 'messagingSenderId', 'appId']
                missing_fields = [field for field in required_fields if field not in config]
                
                if missing_fields:
                    print(f"\n⚠️  Missing required fields: {missing_fields}")
                else:
                    print("\n✅ All required Firebase config fields present")
                
                # Check if config has meaningful values
                empty_fields = [field for field in required_fields if not config.get(field)]
                if empty_fields:
                    print(f"\n⚠️  Empty fields (may be expected in testing): {empty_fields}")
                
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON response: {e}")
                print(f"Raw response: {response.text}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the server running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

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
    
    print(f"Testing frontend config at: {base_url}")
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
    
    # Test the configuration endpoint
    success = test_frontend_config(base_url)
    
    if success:
        print("\n🎉 Frontend configuration test passed!")
        print("The auth.html error should be resolved.")
    else:
        print("\n💥 Frontend configuration test failed!")
        print("The auth.html error may persist.")
    
    sys.exit(0 if success else 1)
