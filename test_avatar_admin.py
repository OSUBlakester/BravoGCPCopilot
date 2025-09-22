#!/usr/bin/env python3
"""
Simple test script to verify avatar admin functionality
"""

import requests
import json
import sys

def test_avatar_admin():
    """Test the avatar admin endpoints"""
    BASE_URL = "http://localhost:8001"  # Adjust if needed
    
    print("🧪 Testing Avatar Admin Endpoints...")
    
    # Test 1: Get Users
    print("\n1. Testing GET /api/admin/users")
    try:
        response = requests.get(f"{BASE_URL}/api/admin/users")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            users = response.json().get("users", [])
            print(f"   Found {len(users)} users")
            for user in users[:3]:  # Show first 3
                print(f"   - {user.get('username', 'Unknown')} ({user.get('displayName', 'No display name')})")
        else:
            print(f"   Error: {response.text}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection failed - is server running on port 8001?")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Get Avatar Presets
    print("\n2. Testing GET /api/admin/avatar-presets")
    try:
        response = requests.get(f"{BASE_URL}/api/admin/avatar-presets")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            presets = response.json().get("presets", [])
            print(f"   Found {len(presets)} presets")
            for preset in presets:
                print(f"   - {preset.get('name', 'Unknown')} ({preset.get('description', 'No description')})")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 3: Test Avatar Admin Page
    print("\n3. Testing Avatar Admin HTML page")
    try:
        response = requests.get(f"{BASE_URL}/static/avatar_admin.html")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Avatar admin page loads successfully")
        else:
            print(f"   ❌ Failed to load avatar admin page: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n✅ Avatar Admin tests completed!")
    print(f"\n🌐 You can access the avatar admin at: {BASE_URL}/static/avatar_admin.html")
    return True

if __name__ == "__main__":
    test_avatar_admin()