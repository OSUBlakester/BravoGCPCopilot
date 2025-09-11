#!/usr/bin/env python3
"""
Simple script to call the admin API endpoint to copy profiles
between Firebase accounts.
"""

import requests
import json

# Your production server URL
SERVER_URL = "https://app.talkwithbravo.com"

def copy_profiles():
    """Copy profiles from demo@talkwithbravo.com to demoreadonly@talkwithbravo.com"""
    
    endpoint = f"{SERVER_URL}/api/admin/copy-profiles-between-accounts"
    
    payload = {
        "source_email": "demo@talkwithbravo.com",
        "target_email": "demoreadonly@talkwithbravo.com",
        "admin_password": "admin123"
    }
    
    print("🚀 Starting profile copy process...")
    print(f"📡 Calling: {endpoint}")
    print(f"📋 Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(endpoint, json=payload, timeout=60)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print("=" * 60)
            print(f"📧 Source: {result['source_email']}")
            print(f"📧 Target: {result['target_email']}")
            print(f"✅ Copied: {result['copied_count']} profiles")
            print(f"❌ Failed: {result['failed_count']} profiles")
            print(f"👥 New user limit: {result['new_user_limit']}")
            print()
            
            if result['copied_profiles']:
                print("📋 Successfully copied profiles:")
                for profile in result['copied_profiles']:
                    print(f"   ✅ {profile['display_name']} (ID: {profile['target_id']})")
            
            if result['failed_profiles']:
                print("❌ Failed profiles:")
                for profile in result['failed_profiles']:
                    print(f"   ❌ {profile['display_name']}: {profile['error']}")
            
            print()
            print("🎉 Profile copy completed successfully!")
            print("   The demoreadonly@talkwithbravo.com account is now ready for demo use!")
            
        else:
            print(f"❌ FAILED: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error text: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    copy_profiles()
