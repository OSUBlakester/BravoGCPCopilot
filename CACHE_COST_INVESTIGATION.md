# Gemini Cache Cost Investigation Summary

## Problem Statement
- SKU EBC7-B1E9-1DA3 (cached input tokens for Gemini 2.5 Flash Lite) costs increasing
- Last month: 261 million tokens
- This month (18 days): 662 million tokens  
- User activity has NOT tripled
- Only happening in prod, not dev

## Most Likely Root Cause

Based on the code analysis and symptoms, the issue is almost certainly:

### **Server Restarts Causing Cache Orphaning**

Your `GeminiCacheManager` stores the cache mapping in memory:
```python
self._user_cache_map = {}  # In-memory dictionary
self._cache_creation_times = {}  # In-memory dictionary
```

**What happens:**
1. Server creates cache for user A → stores `cachedContents/abc123` in `_user_cache_map`
2. Server restarts (Cloud Run auto-scales down/up, deployment, crash, etc.)
3. `_user_cache_map` is now EMPTY (memory cleared)
4. User A makes request
5. `_is_cache_valid()` returns False (user_key not in map)
6. Server creates NEW cache → `cachedContents/xyz789`
7. OLD cache `cachedContents/abc123` still exists (hasn't expired yet, 4-hour TTL)
8. User continues using NEW cache, paying for tokens
9. After 4 hours, old cache expires
10. Repeat cycle...

**Result:** You're paying for 2-3x the caches you actually need because orphaned caches haven't expired yet.

## Why Dev Doesn't Show This

- Dev has minimal restarts (you control when Docker restarts)
- Dev has fewer users, so less cache creation overall
- Prod likely has auto-scaling, more deployments, occasional crashes

## Evidence Needed (Permission Required)

To confirm this, you need to access prod with proper permissions and run:
```bash
python3 list_gemini_caches.py --project bravo-copilot-prod
```

You should see either:
1. **Many duplicate caches per user** (confirms orphaning)
2. **OR very few/no caches** (means they're being created and expiring rapidly - also a problem)

## Solutions

### Solution 1: Persist Cache Map to Firestore (RECOMMENDED)

Store the cache mapping in Firestore so it survives server restarts:

**Benefits:**
- Cache references persist across restarts
- No orphaned caches
- Significant cost savings

**Implementation:** See `fix_cache_persistence.md` for code changes

### Solution 2: Reduce Context Size

Your `_build_combined_context_string()` includes:
- Full user narrative
- Friends & family data
- Settings
- Birthdays
- Diary entries (15 entries)
- Chat history (3-10 messages)
- User-defined pages
- System prompt

This can easily be 50,000+ tokens per user.

**Quick wins:**
- Reduce diary entries: 15 → 5
- Reduce chat history: 10 → 3
- Summarize long user narratives
- Remove pages if not frequently used

### Solution 3: Increase TTL (Temporary)

Current TTL: 4 hours

If caches are being recreated due to restarts, a longer TTL just makes it worse (more overlap).
But if users are genuinely returning multiple times per day, increase to 8 hours:

```python
def __init__(self, ttl_hours: int = 8):  # Was 4
```

### Solution 4: Add Cache Cleanup on Startup

Before creating new caches, check for existing ones:

```python
async def cleanup_orphaned_caches(self):
    """Delete all caches and start fresh on startup"""
    # Requires listing caches via API
    # Only run once on server startup
    pass
```

## Cost Breakdown

Gemini 2.5 Flash Lite cached tokens: $0.01875 per 1M tokens

**Current:**
- 662M tokens in 18 days = ~36.8M tokens/day
- Cost per day: $0.69
- Monthly cost (30 days): ~$20.60

**If this is due to orphaning (3x duplication):**
- Actual needed: ~12.3M tokens/day
- Should cost: ~$6.87/month
- You're overpaying: ~$13.73/month

**If this is due to large context (50k tokens average):**
- With 20 users making 10 requests/day each = 200 requests
- 50k tokens × 200 requests = 10M tokens/day
- Cost: ~$5.63/month (reasonable)

## Next Steps

1. **Get proper GCP permissions** to list caches in prod
   - Contact your GCP admin
   - Need: `aiplatform.cachedContents.list` permission
   
2. **Run diagnostics:**
   ```bash
   python3 list_gemini_caches.py --project bravo-copilot-prod
   ```

3. **Implement Solution 1** (Firestore persistence) - see detailed guide

4. **Monitor for 3-5 days** after fix to confirm cost reduction

## How to Get Permissions

As the developer, you should request these IAM roles:
- **Vertex AI User** (`roles/aiplatform.user`)
- **Or custom role with:** `aiplatform.cachedContents.list`, `aiplatform.cachedContents.get`

Ask your GCP org admin to grant these on the `bravo-copilot-prod` project.

Alternatively, use a service account that has these permissions (likely your Cloud Run service account already does).
