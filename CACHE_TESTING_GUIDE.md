# Cache Functionality Testing Guide

This guide outlines how to test the Gemini Cache Manager implementation for performance optimization.

## Quick Test Commands

### 1. Start the Server (if not running)
```bash
python server.py
# Or if using your deployment script:
./deploy.sh test
```

### 2. Test Cache Endpoints (Manual)

#### Check Cache Stats
```bash
curl -X GET "http://localhost:8000/api/cache/stats" \
  -H "Content-Type: application/json"
```

#### Refresh Cache Manually
```bash
curl -X POST "http://localhost:8000/api/cache/refresh" \
  -H "Content-Type: application/json"
```

### 3. Test LLM Performance

#### First Call (Cold Cache)
```bash
time curl -X POST "http://localhost:8000/llm" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you today?"}'
```

#### Second Call (Warm Cache)
```bash
time curl -X POST "http://localhost:8000/llm" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "How is the weather?"}'
```

## Automated Test Suite

Run the comprehensive test suite:
```bash
python test_cache_functionality.py
```

## What to Look For

### 1. Performance Improvements
- **First LLM call**: Should be normal speed (4s for Gemini, 19s for ChatGPT)
- **Subsequent calls**: Should be faster due to cached context data
- **Expected improvement**: Up to 90% with full cache hits

### 2. Cache Hit Rate Logging
Check server logs for lines like:
```
PERFORMANCE: Cache hit rate: 85.7% (6/7) for account test_account and user testuser
PERFORMANCE: Estimated speedup: 1.77x with 85.7% cache hit rate
```

### 3. Cache Invalidation
- Update user info via admin panel
- Next LLM call should show cache invalidation working
- Look for "Loading fresh user profile" vs "Using cached user profile"

### 4. Cache Statistics
The `/api/cache/stats` endpoint should show:
```json
{
  "total_entries": 5,
  "cache_types": {
    "USER_PROFILE": "2024-08-15T10:30:00",
    "FRIENDS_FAMILY": "2024-08-15T10:30:00",
    "HOLIDAYS_BIRTHDAYS": "2024-08-15T10:30:00"
  },
  "hit_rate": "85.7%"
}
```

## Server Log Analysis

### Cache Hits (Good)
```
Using cached user profile for account test_account and user testuser
Using cached friends/family for account test_account and user testuser
Using cached holidays/birthdays for account test_account and user testuser
```

### Cache Misses (Expected on first run)
```
Loading fresh user profile for account test_account and user testuser
Loading fresh friends/family for account test_account and user testuser
Loading fresh holidays/birthdays for account test_account and user testuser
```

### Cache Invalidation (When data updates)
```
Cache invalidated for account test_account, user testuser: USER_PROFILE
Cache invalidated for account test_account, user testuser: FRIENDS_FAMILY
```

## Performance Benchmarking

### Before Cache (Baseline)
- Gemini: ~4 seconds
- ChatGPT: ~19 seconds

### With Cache (Expected)
- 90% cache hit: ~1.4s (Gemini) / ~2.9s (ChatGPT)
- 50% cache hit: ~2.2s (Gemini) / ~10.5s (ChatGPT)
- 0% cache hit: Same as baseline

## Troubleshooting

### Cache Not Working
1. Check server logs for cache manager initialization
2. Verify authentication is working for test endpoints
3. Ensure user has existing data to cache

### Performance Not Improving
1. Check cache hit rate in logs
2. Verify cache TTL settings (1-24 hours)
3. Look for cache invalidation triggers

### Test Script Issues
1. Update base_url in test script if needed
2. Add proper authentication headers
3. Ensure test user exists with sample data

## Production Monitoring

Monitor these metrics in production:
- Cache hit rates per user
- Average response times
- Cache storage usage
- Cache invalidation frequency
- Error rates in cache operations
