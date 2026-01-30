#!/usr/bin/env python3
"""
Force delete invalid user documents and their subcollections
"""

from google.cloud import firestore

def delete_collection(coll_ref, batch_size=100):
    """Delete all documents in a collection"""
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        # Delete subcollections first
        for subcoll in doc.reference.collections():
            delete_collection(subcoll, batch_size)
        
        # Delete the document
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

    return deleted

prod_db = firestore.Client(project='bravo-prod-465323')
account_id = 'ktWXqeaFI3di7lQGM09Zm0fSSru2'

users_ref = prod_db.collection('accounts').document(account_id).collection('users')
all_user_refs = list(users_ref.list_documents())

print(f'Found {len(all_user_refs)} user documents\n')

invalid_ids = []

for user_ref in all_user_refs:
    doc = user_ref.get()
    if not doc.exists:
        invalid_ids.append(user_ref.id)
        print(f'❌ INVALID (no data): {user_ref.id}')

if invalid_ids:
    print(f'\n⚠️  Will forcefully delete {len(invalid_ids)} invalid documents')
    confirm = input('Proceed? (yes/no): ').strip().lower()
    
    if confirm == 'yes':
        for user_id in invalid_ids:
            user_doc_ref = users_ref.document(user_id)
            
            # Check and delete subcollections
            for subcoll in user_doc_ref.collections():
                print(f'  Deleting subcollection: {subcoll.id}')
                delete_collection(subcoll)
            
            # Force delete the document
            user_doc_ref.delete()
            print(f'  ✅ Deleted {user_id}')
        
        print(f'\n✅ Deleted {len(invalid_ids)} documents')
        
        # Verify
        remaining = list(users_ref.list_documents())
        print(f'\nRemaining users: {len(remaining)}')
        for ref in remaining:
            doc = ref.get()
            if doc.exists:
                print(f'  ✅ {ref.id} - {doc.to_dict().get("display_name")}')
    else:
        print('❌ Cancelled')
else:
    print('✅ No invalid documents found')
