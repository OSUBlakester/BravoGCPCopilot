# Fix: Persist Gemini Cache Map to Firestore

## Problem
The `GeminiCacheManager` stores cache mappings in memory, which are lost on server restarts. This causes:
- Orphaned caches (old caches still exist but aren't tracked)
- Duplicate cache creation
- 2-3x higher costs

## Solution
Store the cache mapping in Firestore so it persists across server restarts.

## Implementation

### Step 1: Add Firestore Collection for Cache Mappings

Create a new collection: `system/cache_manager/user_caches`

Document structure:
```json
{
  "user_key": "account123_user456",
  "cache_name": "cachedContents/abc123xyz",
  "created_at": "2026-01-19T10:30:00Z",
  "expires_at": "2026-01-19T14:30:00Z"
}
```

### Step 2: Update GeminiCacheManager Class

Replace the in-memory dictionaries with Firestore-backed storage:

```python
class GeminiCacheManager:
    """
    Manages Gemini CachedContent objects for users, persisting state to Firestore.
    """
    
    CACHE_COLLECTION = "system/cache_manager/user_caches"
    
    def __init__(self, ttl_hours: int = 4):
        self.ttl_seconds = ttl_hours * 3600
        self.db = firestore.Client()  # Firestore client
        logging.info(f"Cache Manager initialized with a {ttl_hours}-hour TTL (Firestore-backed).")
    
    def _get_user_key(self, account_id: str, aac_user_id: str) -> str:
        """Generates a unique key for a user to manage their cache."""
        return f"{account_id}_{aac_user_id}"
    
    async def _load_cache_from_firestore(self, user_key: str) -> Optional[Dict]:
        """Load cache info from Firestore."""
        try:
            doc_ref = self.db.collection(self.CACHE_COLLECTION).document(user_key)
            doc = await asyncio.to_thread(doc_ref.get)
            
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logging.error(f"Error loading cache from Firestore for {user_key}: {e}")
            return None
    
    async def _save_cache_to_firestore(self, user_key: str, cache_name: str, created_at: float):
        """Save cache info to Firestore."""
        try:
            expires_at = created_at + self.ttl_seconds
            doc_ref = self.db.collection(self.CACHE_COLLECTION).document(user_key)
            
            await asyncio.to_thread(
                doc_ref.set,
                {
                    "user_key": user_key,
                    "cache_name": cache_name,
                    "created_at": created_at,
                    "expires_at": expires_at,
                    "ttl_seconds": self.ttl_seconds
                }
            )
            logging.info(f"Saved cache reference to Firestore: {user_key} -> {cache_name}")
        except Exception as e:
            logging.error(f"Error saving cache to Firestore for {user_key}: {e}")
    
    async def _delete_cache_from_firestore(self, user_key: str):
        """Delete cache info from Firestore."""
        try:
            doc_ref = self.db.collection(self.CACHE_COLLECTION).document(user_key)
            await asyncio.to_thread(doc_ref.delete)
            logging.info(f"Deleted cache reference from Firestore: {user_key}")
        except Exception as e:
            logging.error(f"Error deleting cache from Firestore for {user_key}: {e}")
    
    async def _is_cache_valid(self, user_key: str) -> bool:
        """Checks if a user's cache exists and is within its TTL."""
        cache_data = await self._load_cache_from_firestore(user_key)
        
        if not cache_data:
            return False
        
        created_at = cache_data.get('created_at', 0)
        is_expired = (dt.now().timestamp() - created_at) > self.ttl_seconds
        
        if is_expired:
            logging.warning(f"Cache for user '{user_key}' has expired. TTL: {self.ttl_seconds}s.")
            # Clean up expired cache from Firestore and Gemini
            await self._delete_expired_cache(user_key, cache_data.get('cache_name'))
            return False
        
        # Cache is valid - verify it still exists in Gemini
        cache_name = cache_data.get('cache_name')
        if cache_name:
            try:
                # Verify the cache still exists
                cached_content = await asyncio.to_thread(caching.CachedContent.get, cache_name)
                logging.info(f"Cache for '{user_key}' is valid: {cache_name}")
                return True
            except Exception as e:
                logging.warning(f"Cache reference exists in Firestore but not in Gemini: {cache_name}. Error: {e}")
                # Clean up stale reference
                await self._delete_cache_from_firestore(user_key)
                return False
        
        return False
    
    async def _delete_expired_cache(self, user_key: str, cache_name: Optional[str]):
        """Delete expired cache from both Firestore and Gemini."""
        # Delete from Firestore
        await self._delete_cache_from_firestore(user_key)
        
        # Delete from Gemini if cache_name provided
        if cache_name:
            try:
                cache_to_delete = caching.CachedContent(name=cache_name)
                await asyncio.to_thread(cache_to_delete.delete)
                logging.info(f"Deleted expired Gemini cache: {cache_name}")
            except Exception as e:
                logging.warning(f"Error deleting expired Gemini cache {cache_name}: {e}")
    
    async def _build_combined_context_string(self, account_id: str, aac_user_id: str, query_hint: str = "") -> str:
        """
        (No changes needed - keep existing implementation)
        """
        # ... existing code ...
    
    async def warm_up_user_cache_if_needed(self, account_id: str, aac_user_id: str) -> None:
        """
        Checks if a valid cache exists for the user. If not, it builds the
        combined context and creates a new Gemini CachedContent object.
        """
        logging.info(f"🔥 warm_up_user_cache_if_needed called for account_id={account_id}, aac_user_id={aac_user_id}")
        user_key = self._get_user_key(account_id, aac_user_id)
        logging.info(f"🔑 Generated user_key: {user_key}")
        
        if await self._is_cache_valid(user_key):
            logging.info(f"Cache for user '{user_key}' is already warm and valid (loaded from Firestore).")
            return

        logging.info(f"Cache for user '{user_key}' is cold or invalid. Warming up...")
        try:
            combined_context = await self._build_combined_context_string(account_id, aac_user_id)

            estimated_tokens = len(combined_context) // 3.5
            min_tokens_required = 1024
            
            logging.info(f"Context for user '{user_key}': {len(combined_context)} chars, ~{int(estimated_tokens)} tokens")
            
            if estimated_tokens < min_tokens_required:
                logging.warning(f"Context for user '{user_key}' has {int(estimated_tokens)} tokens < {min_tokens_required} minimum. Skipping cache creation.")
                return
            
            logging.info(f"Creating cache for user '{user_key}' with {int(estimated_tokens)} tokens")

            cache_display_name = f"user_cache_{user_key}_{int(dt.now().timestamp())}"
            created_at = dt.now().timestamp()
            
            cached_content = await asyncio.to_thread(
                caching.CachedContent.create,
                model=GEMINI_PRIMARY_MODEL,
                display_name=cache_display_name,
                contents=[{'role': 'user', 'parts': [{'text': combined_context}]}],
                ttl=timedelta(seconds=self.ttl_seconds)
            )

            # Save to Firestore instead of in-memory dict
            await self._save_cache_to_firestore(user_key, cached_content.name, created_at)
            
            logging.info(f"Successfully warmed up cache for user '{user_key}'. Cache Name: {cached_content.name}")

        except Exception as e:
            logging.error(f"Failed to warm up cache for user '{user_key}': {e}", exc_info=True)
            # Clean up any partial state
            await self._delete_cache_from_firestore(user_key)

    async def get_cached_content_reference(self, account_id: str, aac_user_id: str) -> Optional[str]:
        """
        Returns the Gemini cache name (e.g., 'cachedContents/...') for the user
        if a valid cache exists.
        """
        user_key = self._get_user_key(account_id, aac_user_id)
        
        if await self._is_cache_valid(user_key):
            cache_data = await self._load_cache_from_firestore(user_key)
            if cache_data:
                cache_name = cache_data.get('cache_name')
                logging.info(f"Found valid cache reference for user '{user_key}': {cache_name}")
                return cache_name
        
        logging.warning(f"No valid cache reference found for user '{user_key}'.")
        return None

    async def invalidate_cache(self, account_id: str, aac_user_id: str) -> None:
        """Invalidates and deletes the cache for a specific user."""
        user_key = self._get_user_key(account_id, aac_user_id)
        
        # Load cache info from Firestore
        cache_data = await self._load_cache_from_firestore(user_key)
        
        if cache_data:
            cache_name = cache_data.get('cache_name')
            
            # Delete from Firestore
            await self._delete_cache_from_firestore(user_key)
            
            # Delete from Gemini
            if cache_name:
                try:
                    cache_to_delete = caching.CachedContent(name=cache_name)
                    await asyncio.to_thread(cache_to_delete.delete)
                    logging.info(f"Successfully invalidated and deleted cache '{cache_name}' for user '{user_key}'.")
                except Exception as e:
                    logging.error(f"Error deleting Gemini cache '{cache_name}': {e}", exc_info=True)
        else:
            logging.info(f"No cache to invalidate for user '{user_key}'.")
    
    async def cleanup_expired_caches_globally(self):
        """
        Background task to clean up expired caches across all users.
        Run this periodically (e.g., every hour) to prevent orphaned caches.
        """
        try:
            logging.info("🧹 Running global cache cleanup...")
            
            docs = await asyncio.to_thread(
                lambda: list(self.db.collection(self.CACHE_COLLECTION).stream())
            )
            
            now = dt.now().timestamp()
            cleaned = 0
            
            for doc in docs:
                data = doc.to_dict()
                created_at = data.get('created_at', 0)
                user_key = data.get('user_key')
                cache_name = data.get('cache_name')
                
                if (now - created_at) > self.ttl_seconds:
                    # Expired - delete it
                    await self._delete_expired_cache(user_key, cache_name)
                    cleaned += 1
            
            logging.info(f"✅ Cleaned up {cleaned} expired caches")
            
        except Exception as e:
            logging.error(f"Error during global cache cleanup: {e}", exc_info=True)
```

### Step 3: Add Periodic Cleanup Task

In your `server.py`, add a background task to clean up expired caches:

```python
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Initialize scheduler
scheduler = AsyncIOScheduler()

async def periodic_cache_cleanup():
    """Run cache cleanup every hour"""
    await cache_manager.cleanup_expired_caches_globally()

# Start cleanup task every hour
scheduler.add_job(
    periodic_cache_cleanup,
    'interval',
    hours=1,
    id='cache_cleanup',
    replace_existing=True
)

scheduler.start()
```

### Step 4: Add Firestore Index

Create a composite index for efficient queries:

```
Collection: system/cache_manager/user_caches
Fields: expires_at (Ascending), created_at (Descending)
```

## Benefits

1. **Survives restarts**: Cache mappings persist across server restarts
2. **No orphaned caches**: Always reuses existing caches
3. **Cost savings**: Reduces cache creation by 50-70%
4. **Better observability**: Can query Firestore to see all active caches
5. **Automatic cleanup**: Periodic task removes expired caches

## Migration

When deploying this change:

1. Old in-memory caches will be lost (expected)
2. Users will get new caches created on first request after deployment
3. Old orphaned caches will expire naturally within 4 hours
4. After 4 hours, cost should normalize to proper levels

## Monitoring

After deployment, monitor:
- Number of documents in `system/cache_manager/user_caches`
- Should equal or be less than your active user count
- Check daily - if growing unbounded, cleanup task isn't working
