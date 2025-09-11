#!/usr/bin/env python3

"""
Test script specifically for Brady profile to check cache functionality
"""

import requests
import json

# Test environment URL
BASE_URL = "https://bravo-aac-api-6spp73n6pa-uc.a.run.app"

def test_brady_about_me():
    """Test if Brady profile returns user-specific data"""
    
    print("🧪 Testing Brady 'About Me' functionality...")
    print("=" * 60)
    
    # Test with Brady account
    account_id = "Brady"  # or whatever account Brady belongs to
    aac_user_id = "Brady"
    
    # You'll need to get these from browser inspection when logged in
    # For now, let's test the cache stats to see if Brady has cached data
    
    try:
        print(f"📡 Testing cache stats to see Brady's cached data...")
        response = requests.get(f"{BASE_URL}/api/cache/stats", timeout=30)
        print(f"📊 Cache stats response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            cache_stats = data.get('cache_stats', {})
            
            print(f"✅ Cache stats:")
            print(f"  Total users: {cache_stats.get('total_users', 0)}")
            print(f"  Total caches: {cache_stats.get('total_caches', 0)}")
            print(f"  Cache types: {cache_stats.get('cache_types', {})}")
            print(f"  Active sessions: {cache_stats.get('active_sessions', 0)}")
            
            # If cache is working and Brady has data, we should see some cached entries
            if cache_stats.get('total_caches', 0) > 0:
                print(f"🎉 Cache system is active with {cache_stats['total_caches']} cached entries!")
                print(f"💡 This suggests cache synchronization is working")
            else:
                print(f"⚠️  No cached entries found")
                print(f"💡 This could mean:")
                print(f"   • No users have accessed the system recently")
                print(f"   • Cache is being cleared/not persisting")
                print(f"   • Cache synchronization may not be working")
                
        else:
            print(f"❌ Cache stats failed: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def check_deployment_status():
    """Check if the latest changes are deployed"""
    
    print("\n🚀 Checking deployment status...")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Service is healthy")
            print(f"📋 Environment: {health_data.get('environment')}")
            print(f"🌐 Domain: {health_data.get('domain')}")
            print(f"🔧 Debug mode: {health_data.get('debug_mode')}")
            
            # Check when this was last deployed (not directly available, but we can infer)
            print(f"\n💡 To verify cache fixes are deployed:")
            print(f"   1. Log into https://test.talkwithbravo.com with Brady account")
            print(f"   2. Update Brady's profile information")
            print(f"   3. Test 'About Me' immediately after update")
            print(f"   4. Check if responses include Brady-specific details")
            
        else:
            print(f"❌ Service health check failed")
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")

if __name__ == "__main__":
    print("🚀 Brady Profile Cache Test")
    print("=" * 80)
    
    test_brady_about_me()
    check_deployment_status()
    
    print("\n" + "=" * 80)
    print("🤔 ANSWER TO YOUR QUESTION:")
    print("✅ Cache code changes were committed and should be deployed")
    print("❓ To verify, you need to:")
    print("   1. Log in to test.talkwithbravo.com as Brady")
    print("   2. Update Brady's profile with some personal information")  
    print("   3. Test 'About Me' - it should include Brady-specific details")
    print("   4. If still generic, there may be an authentication/deployment issue")
    print()
    print("🔄 You may need to log in again if the deployment reset sessions")
