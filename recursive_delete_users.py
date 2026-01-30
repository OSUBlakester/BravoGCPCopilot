#!/usr/bin/env python3
"""
Recursively delete user documents including all subcollections
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
        print(f'  Deleted: {doc.id}')

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)
    
    return deleted

prod_db = firestore.Client(project='bravo-prod-465323')
account_id = 'ktWXqeaFI3di7lQGM09Zm0fSSru2'

# The 4 invalid user IDs
invalid_user_ids = [
    '26a8f8e9-b23c-42a3-839a-e8a0e903234f',
    '5d4da3c2-dfa6-43ae-9ff0-6b8064c29ec1',
    'd7f9e4fe-f4a1-430b-894b-7d42035f55d6',
    'f06a04ad-7397-4cc9-b873-0d55a89d691f'
]

print(f'\nRecursively deleting invalid users and all subcollections...\n')

for user_id in invalid_user_ids:
    print(f'Deleting user: {user_id}')
    user_ref = prod_db.collection('accounts').document(account_id).collection('users').document(user_id)
    
    # Delete all subcollections
    for subcoll in user_ref.collections():
        print(f'  Deleting subcollection: {subcoll.id}')
        delete_collection(subcoll)
    
    # Delete the user document itself
    try:
        user_ref.delete()
        print(f'  ✅ Deleted user document\n')
    except Exception as e:
        print(f'  ⚠️  Error: {e}\n')

print('✅ Recursive deletion complete!')
