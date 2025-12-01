# Firestore Index Creation Guide

## Required Index for Custom Images

The custom images feature requires a composite index in Firestore. Here's how to create it:

### Option 1: Automatic Creation (Recommended)
1. Try uploading an image after the deployment completes
2. If you get a 400 error with an index creation link, click the link
3. It will automatically create the required index

### Option 2: Manual Creation
Go to the Firebase Console and create this index:

**Collection ID**: `custom_images`

**Fields to index**:
1. `account_id` (Ascending)
2. `aac_user_id` (Ascending) 
3. `active` (Ascending)
4. `created_at` (Descending)

### Option 3: Firebase CLI
If you have Firebase CLI installed, you can create the index with:

```bash
# Create firestore.indexes.json
cat > firestore.indexes.json << 'EOF'
{
  "indexes": [
    {
      "collectionGroup": "custom_images",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "account_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "aac_user_id", 
          "order": "ASCENDING"
        },
        {
          "fieldPath": "active",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "DESCENDING"
        }
      ]
    }
  ]
}
EOF

# Deploy the index
firebase deploy --only firestore:indexes --project bravo-dev-465400
```

### What I Fixed

1. **JSON Serialization**: Fixed datetime objects being converted to ISO format before returning
2. **Query Optimization**: Temporarily removed the `order_by` clause to avoid index requirement
3. **Python Sorting**: Added sorting in Python code instead of Firestore query

The upload should work now even without the index, but creating the index will improve performance for users with many custom images.

### Index Creation URL

When you try to upload an image, if you still get the index error, the error message will contain a direct link to create the index. It will look like:

```
https://console.firebase.google.com/v1/r/project/bravo-dev-465400/firestore/indexes?create_composite=...
```

Just click that link and Firebase will create the index automatically.