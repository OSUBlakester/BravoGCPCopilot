#!/usr/bin/env python3
"""
Delete a specific user and all subcollections
"""

from google.cloud import firestore

def delete_collection(coll_ref, batch_size=100):
    """Recursively delete a collection"""
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        # Delete subcollections first
        for subcoll in doc.reference.collections():
            delete_collection(subcoll, batch_size)
        
        # Then delete the document
        doc.reference.delete()
        deleted += 1
        print(f'    Deleted: {doc.id}')

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)
    
    return deleted

# Configuration
project = 'bravo-prod-465323'
account_id = 'EhELukYIzHdPxR6ZzcW5w4cXRE52'
user_id = '7eb4a21d-34ab-4cbe-9d06-84779e0b5d87'

print(f'\n{"="*70}')
print(f'Delete User Configuration:')
print(f'{"="*70}')
print(f'Project:  {project}')
print(f'Account:  {account_id}')
print(f'User:     {user_id}')
print(f'{"="*70}\n')

db = firestore.Client(project=project)
user_ref = db.collection('accounts').document(account_id).collection('users').document(user_id)

# Check if user exists
user_doc = user_ref.get()
if not user_doc.exists:
    print(f'❌ User does not exist!')
    exit(0)

user_data = user_doc.to_dict()
print(f'✅ Found user:')
print(f'   User name: {user_data.get("userName", "N/A")}')
print(f'   Device name: {user_data.get("deviceName", "N/A")}')

# Get subcollections
subcollections = list(user_ref.collections())
print(f'\n📁 Found {len(subcollections)} subcollections')

# Confirm deletion
print(f'\n⚠️  WARNING: This will permanently delete this user and all data!')
confirm = input('Continue? (yes/no): ').strip().lower()

if confirm != 'yes':
    print('❌ Cancelled')
    exit(0)

print(f'\n🗑️  Deleting user and all subcollections...\n')

# Delete all subcollections
for subcoll in subcollections:
    print(f'  📂 Deleting subcollection: {subcoll.id}')
    deleted = delete_collection(subcoll)
    print(f'    ✅ Deleted {deleted} documents from {subcoll.id}')

# Delete the user document itself
try:
    user_ref.delete()
    print(f'\n✅ User document deleted')
except Exception as e:
    print(f'\n❌ Error deleting user: {e}')
    exit(1)

print(f'\n{"="*70}')
print('✅ User deletion complete!')
print(f'{"="*70}\n')
