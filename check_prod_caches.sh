#!/bin/bash
#
# Check Gemini caches in production using gcloud CLI
# This is a workaround for permission issues with the Python SDK
#

PROJECT="bravo-copilot-prod"
LOCATION="us-central1"

echo "================================================================================"
echo "🔍 Checking Gemini Caches in $PROJECT"
echo "================================================================================"

# Try using curl with gcloud auth
TOKEN=$(gcloud auth print-access-token)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get access token. Run: gcloud auth login"
    exit 1
fi

echo "✅ Got access token"
echo ""

# Make API call to list caches
ENDPOINT="https://${LOCATION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT}/locations/${LOCATION}/cachedContents"

echo "📡 Calling API: $ENDPOINT"
echo ""

RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" "$ENDPOINT")

# Check if response contains error
if echo "$RESPONSE" | grep -q "error"; then
    echo "❌ API Error:"
    echo "$RESPONSE" | python3 -m json.tool
    exit 1
fi

# Parse and display results
echo "$RESPONSE" | python3 << 'PYTHON'
import json
import sys
from datetime import datetime
from collections import defaultdict

try:
    data = json.load(sys.stdin)
    
    caches = data.get('cachedContents', [])
    total = len(caches)
    
    if total == 0:
        print("✅ No active caches found in production")
        print("\nThis is UNEXPECTED if you're seeing high costs!")
        print("Possible reasons:")
        print("1. Caches have short TTL and expire quickly")
        print("2. Caches are in a different location (try us-west1, etc.)")
        print("3. Cost is from NEW cache creation, not existing caches")
        sys.exit(0)
    
    print(f"⚠️  Found {total} active caches\n")
    print("="*80)
    
    # Analyze patterns
    user_caches = defaultdict(list)
    
    for i, cache in enumerate(caches[:50], 1):  # Show first 50
        name = cache.get('name', 'Unknown')
        display_name = cache.get('displayName', 'Unknown')
        expire_time = cache.get('expireTime', 'Unknown')
        model = cache.get('model', 'Unknown')
        
        print(f"\nCache #{i}:")
        print(f"  ID: {name}")
        print(f"  Display Name: {display_name}")
        print(f"  Model: {model}")
        print(f"  Expires: {expire_time}")
        
        # Extract user key from display name
        if display_name.startswith('user_cache_'):
            parts = display_name.split('_')
            if len(parts) >= 4:
                user_key = '_'.join(parts[2:-1])
                user_caches[user_key].append(display_name)
        
        print("  " + "-"*76)
    
    if total > 50:
        print(f"\n... and {total - 50} more caches (not shown)")
    
    # Summary
    print("\n" + "="*80)
    print("📊 ANALYSIS")
    print("="*80)
    print(f"\nTotal Active Caches: {total}")
    print(f"Unique Users: {len(user_caches)}")
    
    # Check for duplicates
    duplicates = {k: v for k, v in user_caches.items() if len(v) > 1}
    if duplicates:
        print(f"\n🔴 PROBLEM FOUND: {len(duplicates)} users have multiple caches!")
        print("\nTop offenders:")
        for user_key, cache_list in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            print(f"  • {user_key}: {len(cache_list)} caches")
        
        print("\n💡 ROOT CAUSE:")
        print("   Your server is likely restarting frequently OR the in-memory")
        print("   _user_cache_map is being cleared, causing new caches to be")
        print("   created even though old ones still exist and haven't expired.")
        print("\n🔧 FIX:")
        print("   Store the cache map in Firestore so it persists across restarts.")
    else:
        print("\n✅ No duplicate caches detected")
        print("   The high cost is likely due to:")
        print("   1. Very large context size in production")
        print("   2. High request volume")
        print("   3. Frequent cache recreation (check logs)")
    
except json.JSONDecodeError as e:
    print(f"❌ Failed to parse JSON: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON
