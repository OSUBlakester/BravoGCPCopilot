# Firestore Cache Persistence - Deployment Checklist

## ✅ Changes Implemented

### 1. GeminiCacheManager Updates
- ✅ Replaced in-memory dictionaries with Firestore persistence
- ✅ Added `CACHE_COLLECTION = "system/cache_manager/user_caches"`
- ✅ Added Firestore helper methods:
  - `_load_cache_from_firestore()`
  - `_save_cache_to_firestore()`
  - `_delete_cache_from_firestore()`
  - `_delete_expired_cache()`
- ✅ Updated `_is_cache_valid()` to check Firestore + verify Gemini cache still exists
- ✅ Updated `warm_up_user_cache_if_needed()` to save to Firestore
- ✅ Updated `get_cached_content_reference()` to load from Firestore
- ✅ Updated `invalidate_cache()` to delete from both Firestore and Gemini
- ✅ Updated `get_cache_debug_info()` to read from Firestore
- ✅ Added `cleanup_expired_caches_globally()` method

### 2. Background Cleanup Task
- ✅ Added `periodic_cache_cleanup()` function (runs every hour)
- ✅ Integrated into FastAPI lifespan context manager
- ✅ Proper task cancellation on shutdown

### 3. Bug Fixes
- ✅ Updated minimum token requirement from 1024 → 2048 for Gemini 2.5 Flash

### 4. Monitoring Tools
- ✅ Created `monitor_cache_health.py` to check Firestore ↔ Gemini sync

## 📋 Pre-Deployment Checklist

### Local Testing
- [ ] Restart local dev server: `./restart-local.sh`
- [ ] Check logs for successful cache creation
- [ ] Verify Firestore collection is created
- [ ] Test cache persistence across server restarts

### Firestore Setup
- [ ] Ensure Firestore is enabled in production project
- [ ] No indexes needed (simple document reads/writes)
- [ ] Collection will be auto-created: `system/cache_manager/user_caches`

### Production Deployment
- [ ] Commit changes: `git add server.py monitor_cache_health.py`
- [ ] Push to dev branch: `git push origin dev`
- [ ] Deploy to Cloud Run (prod)
- [ ] Monitor logs for cache creation success

## 🧪 Testing Steps

### 1. Local Testing

```bash
# Restart local server
./restart-local.sh

# Watch logs for cache activity
docker logs -f bravo-dev 2>&1 | grep -i cache

# Make a request that triggers cache creation
# (Use the app and interact with LLM features)

# Check if Firestore collection was created
# Go to Firebase Console → Firestore Database → system/cache_manager/user_caches
```

### 2. Verify Cache Persistence

```bash
# 1. Create a cache by using the app
# 2. Restart the server
./restart-local.sh

# 3. Make another request - should REUSE the cache (not create new one)
# 4. Check logs - should see "Cache for user 'XXX' is already warm and valid (loaded from Firestore)"
```

### 3. Monitor Production

After deployment to prod:

```bash
# Set project
gcloud config set project bravo-prod-465323

# Monitor cache health
python3 monitor_cache_health.py --project bravo-prod-465323

# Watch for successful cache creations
gcloud logging read 'resource.type="cloud_run_revision" AND textPayload=~"Successfully warmed up cache"' \
  --project bravo-prod-465323 --limit 10 --freshness=1h

# Check cleanup task is running
gcloud logging read 'resource.type="cloud_run_revision" AND textPayload=~"Running global cache cleanup"' \
  --project bravo-prod-465323 --limit 5 --freshness=6h
```

## 📊 Expected Results

### Before Fix
- ❌ No active Gemini caches (despite high costs)
- ❌ Cache creation failures due to 1024 token minimum
- ❌ Implicit caching causing uncontrolled costs
- ❌ Server restarts = lost cache references = duplicate caches

### After Fix
- ✅ Active Gemini caches visible in monitoring
- ✅ Cache creation succeeds (2048 token minimum)
- ✅ Explicit cache control and lifecycle management
- ✅ Server restarts = cache references persist = no duplicates
- ✅ Hourly cleanup removes expired caches
- ✅ **Cost reduction: 50-70% expected**

## 💰 Cost Impact Timeline

- **Day 1-2**: Mixed costs (old orphaned caches still expiring)
- **Day 3+**: Costs should stabilize at proper level
- **Week 1**: Clear trend of cost reduction
- **Monitor**: Check billing daily for first week

### Expected Monthly Cost
- **Before**: ~$20-25/month (662M tokens in 18 days)
- **After**: ~$7-10/month (proper cache management)
- **Savings**: ~$13-15/month (~60% reduction)

## 🔍 Troubleshooting

### Issue: Caches still not being created

```bash
# Check logs for errors
gcloud logging read 'resource.type="cloud_run_revision" AND severity>=ERROR AND textPayload=~"cache"' \
  --project bravo-prod-465323 --limit 20

# Common causes:
# 1. Context too small (< 2048 tokens) - expand user profiles
# 2. API errors - check Vertex AI API is enabled
# 3. Firestore permission issues - check service account permissions
```

### Issue: Stale Firestore references

```bash
# Run manual cleanup
python3 monitor_cache_health.py --project bravo-prod-465323

# The hourly cleanup task will handle these automatically
```

### Issue: Orphaned Gemini caches

```bash
# These are caches not tracked in Firestore
# They will expire naturally within 4 hours
# After 4 hours of the new code running, all caches should be tracked
```

## 🎯 Success Metrics

Track these over the first week:

1. **Cache Creation Success Rate**
   - Target: >90% of warmup attempts succeed
   - Check: Logs for "Successfully warmed up cache"

2. **Cache Reuse Rate**
   - Target: Most requests reuse existing cache
   - Check: Logs for "Cache for user 'XXX' is already warm and valid"

3. **Firestore ↔ Gemini Sync**
   - Target: 100% sync (equal counts)
   - Check: `monitor_cache_health.py`

4. **Cost Reduction**
   - Target: 50-70% reduction in cached token costs
   - Check: GCP Billing console SKU EBC7-B1E9-1DA3

5. **No Cache Orphaning**
   - Target: 0 orphaned caches after 24 hours
   - Check: `monitor_cache_health.py` orphaned count

## 📞 Support

If you see any issues:
1. Check the troubleshooting section above
2. Run `monitor_cache_health.py` for diagnostics
3. Check Cloud Run logs for errors
4. Verify Firestore collection has documents

The implementation is complete and ready for deployment! 🚀
