# Base + Delta Cache Architecture Refactor

## Problem Identified by Vertex AI

The previous caching strategy was causing **cache churn** - creating new caches on every request instead of reusing them. This happened because:

1. **Everything was cached together**: Mood, location, chat history, pages, AND profile were all in one big cache
2. **Frequent data changes**: Every time mood/location/recent chat changed, the ENTIRE cache was invalidated and recreated
3. **Cost impact**: Recreating 50K+ token caches multiple times per user per day instead of once per session

## Vertex AI Recommendation

Use a **"Base + Delta" architecture**:

- **BASE Context (Cached)**: Stable, long-term data cached once per session
  - User profile narrative
  - Friends & family
  - Settings
  - Birthdays
  - Diary entries
  - Old chat history (>10 messages old)

- **DELTA Context (Standard Input)**: Dynamic data passed as text with each request
  - Current mood (changes frequently)
  - Current location/people/activity
  - Recent chat history (last 10 turns)
  - User pages (frequently edited)

## Implementation Changes

### 1. New Methods Created

#### `_build_base_context(account_id, aac_user_id)` (Lines 1640-1740)
- **Purpose**: Build stable context for caching
- **Includes**: System prompt, user narrative, friends/family, settings, birthdays, diary, old chat history
- **Excludes**: Mood, location, recent chat, pages
- **Estimated size**: ~40-50K tokens (stable across sessions)

#### `_build_delta_context(account_id, aac_user_id, query_hint)` (Lines 1742-1798)
- **Purpose**: Build dynamic context for each request
- **Includes**: Current mood, location/people/activity, recent chat (last 10), user pages
- **Estimated size**: ~500-2000 tokens (changes frequently)

### 2. Cache Management Updates

#### `warm_up_user_cache_if_needed()` (Lines 1805-1845)
- **Changed**: Now uses `_build_base_context()` instead of `_build_combined_context_string()`
- **Result**: Cache contains ONLY stable data
- **Token estimation**: Updated to `// 4` chars per token (more accurate)

#### Request Generation (Lines 3195-3232)
- **Changed**: Now combines cached base + delta context + user query
- **Old approach**: 
  ```python
  model.generate_content(final_user_query)
  ```
- **New approach**:
  ```python
  delta_context = await cache_manager._build_delta_context(...)
  combined_prompt = f"{delta_context}\n\n=== USER QUERY ===\n{final_user_query}"
  model.generate_content(combined_prompt)
  ```
- **Result**: Gemini receives cached base context + fresh delta + query

### 3. Cache Invalidation Strategy

#### REMOVED Invalidation (No longer needed - data in delta context):
- ❌ Page creation/update/delete (Lines 849, 913, 937)
- ❌ Current state updates - mood/location/activity (Line 1064)
- ❌ User favorites changes (Lines 3769, 3840)
- ❌ Chat history updates (Line 8001)
- ❌ Mood-only updates (Line 9057)

#### KEPT Invalidation (Data in base context):
- ✅ User narrative changes (Line 3725)
- ✅ Settings updates (Line 6046)
- ✅ Birthdays updates (Line 7073)
- ✅ Friends & family updates (Line 7101)
- ✅ Diary entry add/update/delete (Lines 7952, 7971)
- ✅ Manual cache refresh endpoint (Line 2951)

### 4. Fallback Function Update

#### `build_full_prompt_for_non_cached_llm()` (Lines 2955-2970)
- **Changed**: Now builds base + delta separately for consistency
- **Old approach**: Called `_build_combined_context_string()`
- **New approach**: 
  ```python
  base_context = await cache_manager._build_base_context(...)
  delta_context = await cache_manager._build_delta_context(...)
  full_context_string = f"{base_context}\n\n{delta_context}"
  ```
- **Result**: Fallback matches same structure as cached requests

## Expected Cost Impact

### Before (Cache Churn):
- User sends 10 messages in a session
- Mood changes 2 times
- Location changes 3 times
- Pages edited 1 time
- **Result**: 6+ cache creations x 50K tokens = **300K+ cached tokens**

### After (Base + Delta):
- User sends 10 messages in a session
- Cache created once at start: 40K tokens (cached)
- Each message: ~1K delta tokens (standard input)
- **Result**: 40K cached + 10K standard = **40K cached tokens + 10K standard**

### Cost Calculation:
- **Cached input**: $0.01875 per 1M tokens
- **Standard input**: $0.075 per 1M tokens

**Before**: 300K cached tokens = $0.005625
**After**: 40K cached + 10K standard = $0.00075 + $0.00075 = $0.0015

**Savings per session**: ~73% reduction

### Monthly Projection:
- **Current**: ~662M cached tokens/month ≈ $12.41/month
- **After fix**: ~165M cached + 50M standard ≈ $3.10 + $3.75 = **$6.85/month**
- **Estimated savings**: **~$5.56/month (~45% reduction)**

Combined with Firestore persistence fix (reducing orphaned caches), total expected savings: **60-70%**

## Testing Checklist

### Local Testing:
1. ✅ Syntax validation passed
2. ⏳ Start local server: `./restart-local.sh`
3. ⏳ Send first message → cache created with base context
4. ⏳ Change mood → verify no cache invalidation in logs
5. ⏳ Send another message → verify cache reused + delta context added
6. ⏳ Edit a page → verify no cache invalidation
7. ⏳ Update user narrative → verify cache IS invalidated

### Production Deployment:
1. Deploy to Cloud Run
2. Monitor logs for:
   - `🏛️ Building BASE context (for caching)`
   - `⚡ Building DELTA context (dynamic data)`
   - `✅ Successfully generated content using BASE cache + DELTA context`
3. Check Firestore: Should see cache documents persisting across requests
4. Use `python3 monitor_cache_health.py --project bravo-prod-465323` to verify sync
5. Monitor billing: Should see reduction in SKU EBC7-B1E9-1DA3 over 3-7 days

## Key Architectural Principles

1. **Cache ONLY stable data** (profile, settings, diary, friends/family)
2. **Pass dynamic data as standard input** (mood, location, recent chat, pages)
3. **Invalidate cache ONLY when base context changes** (narrative, settings, etc.)
4. **Let TTL handle cleanup** for most cases (4-hour cache lifetime)
5. **Firestore persistence** ensures caches survive server restarts

## Monitoring

### Log Messages to Watch:
- ✅ `🏛️ Building BASE context (for caching)` - Creating stable cache
- ✅ `⚡ Building DELTA context (dynamic data)` - Fetching fresh data
- ✅ `✅ Successfully generated content using BASE cache + DELTA context` - Cache reuse working
- ⚠️ `No valid cache found` - Cache miss (should be rare after warmup)

### Success Metrics:
- Cache creation frequency: Should drop from multiple/user/day to ~1/user/session
- Cached token count: Should drop by 50-70%
- Standard input tokens: Will increase slightly (delta context)
- Total cost: Should decrease by 45-60%

## Rollback Plan

If issues arise:
1. Revert to previous `_build_combined_context_string()` approach
2. Keep Firestore persistence (that's still beneficial)
3. Restore cache invalidation on all endpoints
4. Original code available in git history

## Credits

This refactor was guided by Vertex AI Support's detailed analysis of Gemini caching best practices for AAC applications.
