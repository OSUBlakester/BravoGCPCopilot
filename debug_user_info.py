#!/usr/bin/env python3
"""
Script to debug what's in the user info for both accounts
"""

import requests
import json

# Configuration
BASE_URL = "https://app.talkwithbravo.com"
ADMIN_PASSWORD = "admin123"

def debug_user_info():
    """Check what user info exists in both accounts"""
    
    endpoint = f"{BASE_URL}/api/admin/debug-user-info"
    
    payload = {
        "source_email": "demo@talkwithbravo.com",
        "target_email": "demoreadonly@talkwithbravo.com",
        "admin_password": ADMIN_PASSWORD
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    print("🔍 Debugging user info...")
    print(f"📡 Calling: {endpoint}")
    print(f"📋 Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            data = response.json()
            print("=" * 60)
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ FAILED: {response.status_code}")
            try:
                error_data = response.json()
                print("Error details:", json.dumps(error_data, indent=2))
            except:
                print("Error details:", response.text)
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    debug_user_info()
