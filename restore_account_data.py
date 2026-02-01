#!/usr/bin/env python3
"""
Restore missing account document fields in production
"""

from google.cloud import firestore

prod_db = firestore.Client(project='bravo-prod-465323')
account_id = 'ktWXqeaFI3di7lQGM09Zm0fSSru2'

# The account data that should exist (based on typical account structure)
account_data = {
    'email': 'bradythomas99@gmail.com',
    'accountType': 'personal',  # or 'admin' if this is an admin account
    'address': '',
    'createdAt': firestore.SERVER_TIMESTAMP,
}

print(f'\n=== Restoring account document: {account_id} ===\n')

account_ref = prod_db.collection('accounts').document(account_id)

# Check current state
current_doc = account_ref.get()
if current_doc.exists:
    current_data = current_doc.to_dict()
    print(f'Current fields: {list(current_data.keys())}')
    print(f'Current data: {current_data}')
else:
    print('Document does not exist')

print(f'\nUpdating account document with required fields...')

# Update with merge to preserve any existing data and subcollections
account_ref.set(account_data, merge=True)

print('✅ Account document updated!')

# Verify
updated_doc = account_ref.get()
if updated_doc.exists:
    updated_data = updated_doc.to_dict()
    print(f'\nUpdated fields: {list(updated_data.keys())}')
    print(f'Updated data: {updated_data}')
