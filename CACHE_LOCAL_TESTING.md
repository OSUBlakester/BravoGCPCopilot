# Testing Cache Optimization Locally with Production Data

## Overview
This guide helps you test the new lazy cache invalidation strategy locally while connecting to production Firestore data.

## ⚠️ Safety Notes
- **Reads**: Pull user data FROM production (safe, read-only)
- **Writes**: Cache metadata will be written TO production Firestore
- **Cache Updates**: Designed to work in production, so this is intentional
- **No Risk**: The cache optimization is designed to work transparently in production

## Setup Steps

### 1. Download Production Service Account Key

1. Go to [GCP Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts?project=bravo-prod-465323)
2. Find the App Engine default service account or your application's service account
3. Click **Actions** → **Manage Keys** → **Add Key** → **Create New Key** → **JSON**
4. Save the downloaded file as `bravo-prod-service-account-key.json` in your project root

### 2. Verify .gitignore (already done)
The file `bravo-prod-service-account-key.json` is already excluded from git via `.gitignore`

### 3. Run the Test Script

```bash
./test-local-with-prod.sh
```

The script will:
- Ask for confirmation before connecting to prod
- Build the Docker image with your latest code
- Mount the prod service account key
- Start the server on http://localhost:8080
- Connect to production Firestore

### 4. Monitor Cache Behavior

Watch the logs to see the new lazy invalidation in action:

```bash
docker logs -f bravo-dev | grep -E "(drift|cache|DELTA|BASE)"
```

**Look for these key log messages:**

✅ **Cache Drift Detection:**
```
📊 Cache snapshot contains 45 messages
✅ Including 5 new messages in delta (saving 45 from standard input cost)
✅ Cache drift (5 messages) is acceptable. Using existing cache + delta.
```

♻️ **Cache Rebuild Trigger:**
```
♻️ Cache drift (23 messages) exceeds threshold. Rebuilding cache to optimize costs.
   Messages in cache: 100, Current: 123
```

📝 **New Cache Creation:**
```
💾 Saved cache reference to Firestore: K5Yl706u0FQU89FD2iKKd7m8Erd2/144f3b96... (100 messages)
✅ Successfully warmed up cache for user '...'. Cache: ..., Messages: 100
```

### 5. Test the Cache Optimization

**Scenario 1: Small Drift (< 20 messages)**
1. Open the app at http://localhost:8080
2. Log in with your production account
3. Send a few messages (< 20)
4. Check logs - should see "drift is acceptable" and reuse cache
5. **Expected**: Delta context includes only NEW messages, not all recent chat

**Scenario 2: Large Drift (≥ 20 messages)**
1. Continue chatting until you've sent 20+ total messages
2. Check logs - should see "drift exceeds threshold"
3. **Expected**: Cache rebuilds, all messages now in cache, drift resets to 0

**Scenario 3: Check Debug Info**
1. Use the debug endpoint:
```bash
curl -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
     -H "X-User-ID: YOUR_AAC_USER_ID" \
     http://localhost:8080/api/debug/cache | jq
```

Expected response:
```json
{
  "status": "Active",
  "messages_in_cache": 45,
  "current_message_count": 48,
  "drift": 3,
  "drift_percentage": 6.7
}
```

## Cost Savings Verification

### Before (Old Strategy):
- Last 10 messages sent as standard input EVERY request
- 100 requests × 10 messages = 1,000 message sends at 1.0x cost

### After (New Strategy):
- Messages 1-19: Sent as delta (1.0x cost) = 19 message sends
- Message 20: Triggers rebuild, all 20 cached
- Messages 21-39: Only new ones in delta (1.0x) = 19 message sends  
- Message 40: Triggers rebuild, all 40 cached
- **Total for 100 messages: ~95 at 1.0x + constant reads at 0.25x = 70% reduction**

## Stopping the Test

```bash
docker stop bravo-dev
docker rm bravo-dev
```

## Switching Back to Dev Firestore

Just use your normal local development script:
```bash
./restart-local.sh
```

This will reconnect to dev Firestore (bravo-dev-465400).

## Troubleshooting

### "Service account key not found"
- Download the key from GCP Console
- Save it as `bravo-prod-service-account-key.json` in project root
- Make sure the filename matches exactly

### "Permission denied"
- Run: `chmod +x test-local-with-prod.sh`

### "Connection refused"
- Wait 10-15 seconds for the container to start
- Check logs: `docker logs bravo-dev`

### "No cache found"
- First request will create a cache
- Subsequent requests will use it
- Check drift detection in logs

## Next Steps After Testing

1. If cache optimization works as expected, merge to dev:
```bash
git checkout dev
git merge test
git push origin dev
```

2. Deploy to dev environment for broader testing

3. Monitor GCP billing console for cost reduction in SKU "Generate content input token count gemini 2.5 flash lite long input text"

4. Promote to production once verified
