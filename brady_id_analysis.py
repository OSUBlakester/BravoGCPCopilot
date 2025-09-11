#!/usr/bin/env python3

"""
Check for Brady's exact account and user ID mapping
"""

import requests
import json

BASE_URL = "https://bravo-aac-api-6spp73n6pa-uc.a.run.app"

def analyze_brady_cache_issue():
    """Analyze the Brady cache issue with proper ID mapping"""
    
    print("🔍 Brady Cache Issue Analysis")
    print("=" * 60)
    
    # Brady's known Firestore path components
    brady_account_id = "wlJedVV4jMapxLxPHjBe2dMBwaD2"  # Firebase UID
    brady_aac_user_id = "7fdc7994-2a51-43d5-973f-841b496ac038"  # UUID
    
    print(f"📋 Brady's Firestore Identity:")
    print(f"  Account ID: {brady_account_id}")
    print(f"  AAC User ID: {brady_aac_user_id}")
    print(f"  Expected Path: accounts/{brady_account_id}/users/{brady_aac_user_id}/info/user_narrative")
    
    print(f"\n🔍 Potential Issues:")
    print(f"1. ❓ Authentication: Is Brady's browser session providing correct headers?")
    print(f"   • X-User-ID should be: {brady_aac_user_id}")
    print(f"   • Account ID should be: {brady_account_id}")
    
    print(f"\n2. ❓ Cache Key: Is cache using the right user key?")
    print(f"   • Expected cache key: {brady_account_id}_{brady_aac_user_id}")
    
    print(f"\n3. ❓ Token Calculation: Is Brady's content above 512 token threshold?")
    
    # Estimate Brady's content size
    brady_content_estimate = """You are Bravo, an AI communication assistant designed for AAC users...

## User Profile
Default user info.The user is Brady Thomas.  
Brady's name is pronounced "BRAY-DEE"
Brady was born on May 13, 1999, man who lives in Highlands Ranch, Colorado with his mother, Anne and Father, Blake.
Brady was born with a genetic condition called KCNQ2.  Brady has severe developmental disabilities.  Brady is non-verbal and uses AAC to communicate.  Brady uses a manual wheelchair. Brady is entirely tube-fed with Kate Farms formula.  
Brady loves the Denver Broncos and Oklahoma State Cowboys sports teams.  He also enjoys the other Denver-area professional sports teams and the Colorado State University Rams sports teams.

## Friends Family
[Brady's family and friends data]

## User Settings
[Brady's settings]

## Holidays Birthdays
[Brady's birthdays/holidays]
"""
    
    estimated_tokens = len(brady_content_estimate) // 4
    print(f"   • Estimated Brady content: ~{len(brady_content_estimate)} chars")
    print(f"   • Estimated tokens: ~{estimated_tokens}")
    print(f"   • Above 512 threshold: {'✅ YES' if estimated_tokens >= 512 else '❌ NO'}")
    
    print(f"\n💡 Debugging Actions:")
    print(f"1. 🌐 In browser (logged in as Brady):")
    print(f"   • Open Developer Tools → Network tab")
    print(f"   • Make 'About Me' request") 
    print(f"   • Check request headers for X-User-ID and Authorization")
    print(f"   • Verify they match Brady's expected IDs")
    
    print(f"\n2. 🔄 Force cache refresh:")
    print(f"   • Update Brady's profile (add a space, save)")
    print(f"   • This should trigger cache_manager.store_cached_context()")
    print(f"   • Then test 'About Me' immediately")
    
    print(f"\n3. 📊 Check cache stats after Brady activity:")
    print(f"   • Should show 1 user with >0 cached items")
    print(f"   • If still 0 cached items → authentication/ID mismatch")
    
    print(f"\n🎯 MOST LIKELY CAUSE:")
    print(f"Brady's browser authentication is sending different account/user IDs")
    print(f"than what's expected, so cache lookups are failing.")

if __name__ == "__main__":
    analyze_brady_cache_issue()
