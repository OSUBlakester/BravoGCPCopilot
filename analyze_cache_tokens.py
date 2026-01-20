#!/usr/bin/env python3
"""
Analyze Gemini cache token usage by examining application logs.

This script helps diagnose why cached token counts are high by:
- Showing actual token counts from recent requests
- Comparing cache sizes between environments
- Identifying if context is growing over time

Usage:
    python3 analyze_cache_tokens.py
"""

import re
import subprocess
import sys
from datetime import datetime, timedelta
from collections import defaultdict


def analyze_docker_logs(container_name="bravo-dev", hours=24):
    """
    Analyze Docker logs to find cached token usage patterns.
    
    Args:
        container_name: Name of the Docker container
        hours: How many hours of logs to analyze
    """
    print("=" * 80)
    print(f"📊 Analyzing Gemini Cache Token Usage from Docker Logs")
    print(f"Container: {container_name}")
    print(f"Time Range: Last {hours} hours")
    print("=" * 80)
    
    try:
        # Get Docker logs
        result = subprocess.run(
            ["docker", "logs", "--since", f"{hours}h", container_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Error getting Docker logs: {result.stderr}")
            return
        
        logs = result.stdout + result.stderr
        
        # Look for cache-related log messages
        cache_warmup_pattern = r"Context for user '([^']+)': (\d+) chars, ~(\d+) tokens"
        cache_created_pattern = r"Successfully warmed up cache for user '([^']+)'\. Cache Name: (cachedContents/[^\s]+)"
        usage_pattern = r"cached_content_token_count['\"]?: ?(\d+)"
        context_size_pattern = r"Combined context for [^:]+/[^:]+? is (\d+) chars long"
        
        # Extract data
        warmup_events = re.findall(cache_warmup_pattern, logs)
        cache_created = re.findall(cache_created_pattern, logs)
        cached_tokens = re.findall(usage_pattern, logs)
        context_sizes = re.findall(context_size_pattern, logs)
        
        print(f"\n📈 Cache Activity Summary:")
        print(f"  • Cache warmup events: {len(warmup_events)}")
        print(f"  • Caches created: {len(cache_created)}")
        print(f"  • Requests using cached tokens: {len(cached_tokens)}")
        
        if warmup_events:
            print(f"\n🔥 Recent Cache Warmup Events:")
            
            # Group by user and show stats
            user_stats = defaultdict(list)
            for user_key, chars, tokens in warmup_events[-20:]:  # Last 20
                tokens_int = int(tokens)
                chars_int = int(chars)
                user_stats[user_key].append((chars_int, tokens_int))
            
            print(f"\n📊 Context Size by User (last 20 warmup events):")
            for user_key, sizes in sorted(user_stats.items(), key=lambda x: max(s[1] for s in x[1]), reverse=True)[:10]:
                avg_tokens = sum(s[1] for s in sizes) / len(sizes)
                max_tokens = max(s[1] for s in sizes)
                print(f"  • {user_key}:")
                print(f"    - Average: ~{int(avg_tokens):,} tokens")
                print(f"    - Maximum: ~{int(max_tokens):,} tokens")
                if len(sizes) > 1:
                    print(f"    - Recreated {len(sizes)} times (⚠️  potential issue)")
        
        if cached_tokens:
            # Analyze cached token usage
            token_counts = [int(t) for t in cached_tokens]
            avg_cached = sum(token_counts) / len(token_counts)
            max_cached = max(token_counts)
            min_cached = min(token_counts)
            
            print(f"\n💰 Cached Token Usage (from {len(token_counts)} requests):")
            print(f"  • Average: {int(avg_cached):,} tokens per request")
            print(f"  • Maximum: {int(max_cached):,} tokens per request")
            print(f"  • Minimum: {int(min_cached):,} tokens per request")
            print(f"  • Total: {sum(token_counts):,} cached tokens")
            
            # Cost estimation (approximate)
            # Gemini 2.5 Flash Lite cached input: $0.01875 per 1M tokens
            cost_per_million = 0.01875
            total_cost = (sum(token_counts) / 1_000_000) * cost_per_million
            print(f"\n💵 Estimated Cost for These Requests:")
            print(f"  • ${total_cost:.4f} (based on $0.01875 per 1M cached tokens)")
            
            if avg_cached > 100_000:
                print(f"\n⚠️  WARNING: Average cached token count is very high!")
                print(f"   Your context appears to be ~{int(avg_cached):,} tokens per request.")
                print(f"   Consider reducing context size to lower costs.")
        
        if context_sizes:
            # Analyze context sizes
            sizes = [int(s) for s in context_sizes]
            avg_size = sum(sizes) / len(sizes)
            max_size = max(sizes)
            
            # Estimate tokens (rough: 3.5 chars per token)
            avg_tokens_est = avg_size / 3.5
            max_tokens_est = max_size / 3.5
            
            print(f"\n📏 Context String Sizes:")
            print(f"  • Average: {int(avg_size):,} characters (~{int(avg_tokens_est):,} tokens)")
            print(f"  • Maximum: {int(max_size):,} characters (~{int(max_tokens_est):,} tokens)")
            
            if avg_tokens_est > 50_000:
                print(f"\n⚠️  Your context is very large!")
                print(f"   Recommendations to reduce context size:")
                print(f"   1. Limit diary entries (currently showing 15, try 10 or 5)")
                print(f"   2. Reduce chat history (currently 3-10, try 2-5)")
                print(f"   3. Summarize user narrative if it's very long")
                print(f"   4. Remove or summarize pages data if extensive")
        
        # Check for cache recreation patterns
        if len(cache_created) > 0:
            print(f"\n🔄 Cache Creation Analysis:")
            print(f"  • Total caches created in last {hours}h: {len(cache_created)}")
            
            # Count unique users
            unique_users = len(set(user for user, _ in cache_created))
            print(f"  • Unique users: {unique_users}")
            
            if len(cache_created) > unique_users * 2:
                avg_per_user = len(cache_created) / unique_users
                print(f"  • Average caches per user: {avg_per_user:.1f}")
                print(f"\n⚠️  WARNING: Caches are being recreated too frequently!")
                print(f"   With a 4-hour TTL, you should see ~1-2 caches per user per day.")
                print(f"   If you're seeing many more, check:")
                print(f"   1. Are caches being invalidated on every user update?")
                print(f"   2. Is the TTL too short?")
                print(f"   3. Are server restarts clearing the in-memory cache map?")
        
        print("\n" + "=" * 80)
        
    except FileNotFoundError:
        print("❌ Docker command not found. Make sure Docker is installed.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error analyzing logs: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def compare_environments():
    """Compare cache usage between dev and prod environments."""
    print("\n" + "=" * 80)
    print("🔀 ENVIRONMENT COMPARISON")
    print("=" * 80)
    
    print("\n📝 To compare dev vs prod, run:")
    print("   1. List caches in both environments:")
    print("      python3 list_gemini_caches.py --project bravo-copilot-dev")
    print("      python3 list_gemini_caches.py --project bravo-copilot-prod")
    print("\n   2. Check Cloud Console billing:")
    print("      https://console.cloud.google.com/billing")
    print("\n   3. Look for differences in:")
    print("      • Number of active caches (dev vs prod)")
    print("      • Average tokens per request (shown above)")
    print("      • User activity patterns")


def main():
    print("\n🔍 Gemini Cache Token Analysis Tool\n")
    
    # Analyze local dev environment
    print("Analyzing local development environment...")
    analyze_docker_logs("bravo-dev", hours=24)
    
    # Provide comparison guidance
    compare_environments()
    
    print("\n💡 NEXT STEPS:")
    print("   1. Run: python3 list_gemini_caches.py --project bravo-copilot-prod")
    print("      to see if you have orphaned/duplicate caches in production")
    print("\n   2. If prod has many duplicate caches, the issue is likely:")
    print("      • Server restarts clearing the in-memory _user_cache_map")
    print("      • Cache invalidation happening too frequently")
    print("\n   3. If cache counts are normal, the issue is likely:")
    print("      • Context size is much larger in prod than dev")
    print("      • More user activity in prod (but you said this didn't triple)")
    print("\n   4. Consider migrating cache state to Firestore so it persists")
    print("      across server restarts (see recommendations below)")
    print("\n")


if __name__ == "__main__":
    main()
