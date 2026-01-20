#!/usr/bin/env python3
"""
Monitor Gemini Cache Health

Checks both Firestore cache mappings and actual Gemini caches to ensure they're in sync.
Run this periodically to verify the Firestore persistence is working correctly.

Usage:
    python3 monitor_cache_health.py --project PROJECT_ID
"""

import argparse
import sys
from datetime import datetime
from google.cloud import firestore
from google.cloud.aiplatform_v1beta1 import GenAiCacheServiceClient
from google.api_core import exceptions


def check_firestore_caches(project_id: str):
    """Check cache mappings stored in Firestore."""
    print("\n" + "=" * 80)
    print("📊 FIRESTORE CACHE MAPPINGS")
    print("=" * 80)
    
    try:
        db = firestore.Client(project=project_id)
        collection_path = "system/cache_manager/user_caches"
        
        docs = list(db.collection(collection_path).stream())
        
        if not docs:
            print("\n✅ No cache mappings found in Firestore")
            print("   This is normal if no caches have been created yet.")
            return {}
        
        print(f"\nFound {len(docs)} cache mappings in Firestore:\n")
        
        cache_map = {}
        now = datetime.now().timestamp()
        
        for doc in docs:
            data = doc.to_dict()
            user_key = data.get('user_key', 'Unknown')
            cache_name = data.get('cache_name', 'Unknown')
            created_at = data.get('created_at', 0)
            expires_at = data.get('expires_at', 0)
            
            age_hours = (now - created_at) / 3600
            time_left_hours = (expires_at - now) / 3600
            is_expired = time_left_hours <= 0
            
            status = "🔴 EXPIRED" if is_expired else "🟢 ACTIVE"
            
            print(f"{status} {user_key}")
            print(f"  Cache ID: {cache_name}")
            print(f"  Age: {age_hours:.1f} hours")
            print(f"  Time remaining: {time_left_hours:.1f} hours")
            print()
            
            cache_map[user_key] = cache_name
        
        return cache_map
        
    except Exception as e:
        print(f"❌ Error checking Firestore: {e}")
        return {}


def check_gemini_caches(project_id: str, location: str = "us-central1"):
    """Check actual Gemini caches."""
    print("\n" + "=" * 80)
    print("🔍 ACTUAL GEMINI CACHES")
    print("=" * 80)
    
    try:
        client = GenAiCacheServiceClient(
            client_options={"api_endpoint": f"{location}-aiplatform.googleapis.com"}
        )
        
        parent = f"projects/{project_id}/locations/{location}"
        request = {"parent": parent}
        
        page_result = client.list_cached_contents(request=request)
        caches = list(page_result)
        
        if not caches:
            print("\n✅ No active Gemini caches found")
            return set()
        
        print(f"\nFound {len(caches)} active Gemini caches:\n")
        
        cache_names = set()
        
        for cache in caches:
            cache_names.add(cache.name)
            print(f"• {cache.name}")
            print(f"  Display Name: {cache.display_name}")
            if cache.expire_time:
                expire_dt = cache.expire_time
                now = datetime.now(expire_dt.tzinfo)
                time_left = expire_dt - now
                hours_left = time_left.total_seconds() / 3600
                print(f"  Expires in: {hours_left:.1f} hours")
            print()
        
        return cache_names
        
    except exceptions.PermissionDenied:
        print("❌ Permission denied. Make sure you're authenticated:")
        print("   gcloud auth application-default login")
        return set()
    except Exception as e:
        print(f"❌ Error checking Gemini caches: {e}")
        return set()


def compare_caches(firestore_map: dict, gemini_cache_names: set):
    """Compare Firestore mappings with actual Gemini caches."""
    print("\n" + "=" * 80)
    print("🔄 CACHE SYNC STATUS")
    print("=" * 80)
    
    # Caches in Firestore but not in Gemini (stale references)
    firestore_cache_names = set(firestore_map.values())
    stale_refs = firestore_cache_names - gemini_cache_names
    
    # Caches in Gemini but not in Firestore (orphaned caches)
    orphaned = gemini_cache_names - firestore_cache_names
    
    # Perfect matches
    in_sync = firestore_cache_names & gemini_cache_names
    
    print(f"\n✅ In Sync: {len(in_sync)} caches")
    print(f"⚠️  Stale References in Firestore: {len(stale_refs)} (should auto-cleanup)")
    print(f"🔴 Orphaned Gemini Caches: {len(orphaned)} (NOT tracked in Firestore!)")
    
    if orphaned:
        print("\n⚠️  WARNING: Orphaned caches detected!")
        print("These caches exist in Gemini but aren't tracked in Firestore.")
        print("This suggests caches were created before Firestore persistence was implemented.")
        print("\nOrphaned caches:")
        for cache_name in sorted(orphaned):
            print(f"  • {cache_name}")
        print("\n💡 These will expire naturally within their TTL (4 hours).")
    
    if stale_refs:
        print("\n⚠️  Stale references detected!")
        print("These Firestore entries point to caches that no longer exist in Gemini.")
        print("They should be cleaned up on next cache validation or by the hourly cleanup task.")
    
    if not orphaned and not stale_refs:
        print("\n🎉 Perfect! All caches are properly tracked and in sync.")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor Gemini cache health and Firestore sync",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--project",
        required=True,
        help="GCP project ID (e.g., bravo-prod-465323)"
    )
    
    parser.add_argument(
        "--location",
        default="us-central1",
        help="GCP location/region (default: us-central1)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🏥 GEMINI CACHE HEALTH MONITOR")
    print("=" * 80)
    print(f"Project: {args.project}")
    print(f"Location: {args.location}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check Firestore
    firestore_map = check_firestore_caches(args.project)
    
    # Check Gemini
    gemini_caches = check_gemini_caches(args.project, args.location)
    
    # Compare
    compare_caches(firestore_map, gemini_caches)
    
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    print(f"Firestore cache mappings: {len(firestore_map)}")
    print(f"Active Gemini caches: {len(gemini_caches)}")
    print(f"Expected state: These numbers should be equal or very close")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
