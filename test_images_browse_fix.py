#!/usr/bin/env python3
"""
Test the admin images browse endpoint
"""

import requests
import json
import sys

# Test the endpoint
def test_images_browse():
    """Test the images browse endpoint"""
    print("Testing /api/admin/images/browse endpoint")
    print("=" * 50)
    
    base_url = "https://talkwithbravo.com"
    endpoint = f"{base_url}/api/admin/images/browse"
    
    # Test without authentication (should fail)
    print("\n1. Testing without authentication (should fail with 401)...")
    try:
        response = requests.get(endpoint, params={'limit': 5, 'page': 0})
        print(f"Status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Correctly requires authentication")
        else:
            print(f"❌ Expected 401, got {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Note: We can't easily test with authentication without user credentials
    print("\n2. Authentication test skipped (requires user credentials)")
    print("To test with authentication:")
    print("1. Log in to the web app")
    print("2. Check browser console for any 403 errors")
    print("3. Try to browse images in admin_pages.html")
    
    print("\nEndpoint change summary:")
    print("- Changed from get_current_account_and_user_ids to verify_firebase_token_only")
    print("- This removes the requirement for a valid AAC user ID in Firestore")
    print("- Only requires valid Firebase authentication")
    print("- Should resolve the 403 error for non-admin users")

if __name__ == "__main__":
    test_images_browse()