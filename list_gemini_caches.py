#!/usr/bin/env python3
"""
List all Gemini cached content in a GCP project to investigate caching costs.

This script helps diagnose high cached token costs by showing:
- Total number of active caches
- Cache display names and IDs
- Expiration times
- Potential duplicates or orphaned caches

Usage:
    python3 list_gemini_caches.py --project PROJECT_ID [--location LOCATION]
    
Examples:
    # List caches in prod
    python3 list_gemini_caches.py --project bravo-copilot-prod
    
    # List caches in dev
    python3 list_gemini_caches.py --project bravo-copilot-dev
    
    # Specify custom location
    python3 list_gemini_caches.py --project bravo-copilot-prod --location us-central1
"""

import argparse
import sys
from datetime import datetime
from collections import defaultdict
from google.cloud.aiplatform_v1beta1 import GenAiCacheServiceClient
from google.api_core import exceptions


def list_caches(project_id: str, location: str = "us-central1"):
    """
    List all cached content in the specified GCP project.
    
    Args:
        project_id: GCP project ID
        location: GCP region (default: us-central1)
    """
    try:
        # Initialize the client
        client = GenAiCacheServiceClient(
            client_options={"api_endpoint": f"{location}-aiplatform.googleapis.com"}
        )
        
        parent = f"projects/{project_id}/locations/{location}"
        
        print("=" * 80)
        print(f"🔍 Listing Gemini Caches in {parent}")
        print("=" * 80)
        
        request = {"parent": parent}
        
        # List all active caches
        page_result = client.list_cached_contents(request=request)
        
        caches = list(page_result)
        total_caches = len(caches)
        
        if total_caches == 0:
            print("\n✅ No active caches found.")
            print("\nThis is GOOD - it means you're not accumulating orphaned caches.")
            return
        
        print(f"\n⚠️  Found {total_caches} active caches\n")
        
        # Analyze cache patterns
        cache_by_prefix = defaultdict(list)
        cache_by_day = defaultdict(int)
        
        for i, cache in enumerate(caches, 1):
            print(f"\nCache #{i}:")
            print(f"  ID: {cache.name}")
            print(f"  Display Name: {cache.display_name}")
            
            # Extract expiration time
            if cache.expire_time:
                expire_dt = cache.expire_time
                now = datetime.now(expire_dt.tzinfo)
                time_until_expire = expire_dt - now
                hours_remaining = time_until_expire.total_seconds() / 3600
                
                print(f"  Expires: {expire_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                print(f"  Time Remaining: {hours_remaining:.1f} hours")
                
                # Track by creation day (approximate)
                creation_date = expire_dt.date()
                cache_by_day[str(creation_date)] += 1
            
            # Extract user_key from display name if it follows the pattern "user_cache_accountid_userid_timestamp"
            if cache.display_name.startswith("user_cache_"):
                parts = cache.display_name.split("_")
                if len(parts) >= 4:
                    # Extract account_id and user_id
                    user_key = "_".join(parts[2:-1])  # Everything between "user_cache_" and timestamp
                    cache_by_prefix[user_key].append(cache.display_name)
            
            # Check model
            if hasattr(cache, 'model'):
                print(f"  Model: {cache.model}")
            
            print("  " + "-" * 76)
        
        # Summary statistics
        print("\n" + "=" * 80)
        print("📊 CACHE ANALYSIS")
        print("=" * 80)
        
        print(f"\n📈 Total Active Caches: {total_caches}")
        
        # Check for duplicate user caches
        duplicates = {k: v for k, v in cache_by_prefix.items() if len(v) > 1}
        if duplicates:
            print(f"\n⚠️  POTENTIAL ISSUE: Found {len(duplicates)} users with multiple caches!")
            print("\n🔴 Users with duplicate caches (this is likely causing high costs):")
            for user_key, cache_names in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True):
                print(f"  • {user_key}: {len(cache_names)} caches")
                for cache_name in cache_names[:3]:  # Show first 3
                    print(f"    - {cache_name}")
                if len(cache_names) > 3:
                    print(f"    ... and {len(cache_names) - 3} more")
            
            print("\n💡 RECOMMENDATION:")
            print("   Your code might be creating a new cache for each request instead of")
            print("   reusing existing caches. Check your cache validation logic in")
            print("   GeminiCacheManager._is_cache_valid() and warm_up_user_cache_if_needed().")
        else:
            print("\n✅ No duplicate user caches detected")
            print("   Each user has at most 1 active cache (this is good)")
        
        # Check cache distribution by day
        if cache_by_day:
            print(f"\n📅 Cache Creation Distribution:")
            for day in sorted(cache_by_day.keys(), reverse=True)[:7]:  # Last 7 days
                print(f"  • {day}: {cache_by_day[day]} caches")
        
        # Unique users
        unique_users = len(cache_by_prefix)
        print(f"\n👥 Unique Users with Caches: {unique_users}")
        
        if total_caches > unique_users * 2:
            print(f"\n⚠️  WARNING: You have {total_caches} caches for {unique_users} users")
            print(f"   Average: {total_caches / unique_users:.1f} caches per user")
            print("   This suggests cache creation is happening too frequently!")
        
        print("\n" + "=" * 80)
        
    except exceptions.PermissionDenied:
        print(f"❌ Permission denied. Make sure you have the necessary permissions.")
        print(f"   Run: gcloud auth application-default login")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error listing caches: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="List all Gemini cached content in a GCP project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List caches in production
  %(prog)s --project bravo-copilot-prod
  
  # List caches in dev
  %(prog)s --project bravo-copilot-dev
  
  # Specify custom location
  %(prog)s --project bravo-copilot-prod --location us-central1
        """
    )
    
    parser.add_argument(
        "--project",
        required=True,
        help="GCP project ID (e.g., bravo-copilot-prod)"
    )
    
    parser.add_argument(
        "--location",
        default="us-central1",
        help="GCP location/region (default: us-central1)"
    )
    
    args = parser.parse_args()
    
    list_caches(args.project, args.location)


if __name__ == "__main__":
    main()
