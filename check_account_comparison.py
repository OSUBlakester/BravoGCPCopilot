#!/usr/bin/env python3
"""
Compare account data between dev and prod
"""

from google.cloud import firestore

dev_db = firestore.Client(project='bravo-dev-465400')
prod_db = firestore.Client(project='bravo-prod-465323')

# The prod Firebase UID
prod_account_id = 'ktWXqeaFI3di7lQGM09Zm0fSSru2'

print(f'\n=== PROD Account: {prod_account_id} ===\n')

prod_account_ref = prod_db.collection('accounts').document(prod_account_id)
prod_account_doc = prod_account_ref.get()

print(f'Document exists: {prod_account_doc.exists}')
if prod_account_doc.exists:
    data = prod_account_doc.to_dict()
    print(f'Document has data: {data is not None and len(data) > 0}')
    if data:
        print(f'Fields: {list(data.keys())}')
        for key, value in data.items():
            print(f'  {key}: {value}')
else:
    print('Document has no data (phantom document)')

# Check subcollections
subcollections = list(prod_account_ref.collections())
print(f'\nSubcollections: {[s.id for s in subcollections]}')

# Count users
users = list(prod_account_ref.collection('users').stream())
print(f'Users in account: {len(users)}')
for user in users:
    user_data = user.to_dict()
    print(f'  - {user.id}: {user_data.get("userName", user_data.get("deviceName", "Unknown"))}')

print('\n=== DEV Accounts (to find matching email) ===\n')

# List all dev accounts to find the one with email bradythomas99@gmail.com
dev_accounts = dev_db.collection('accounts').stream()
for acc in dev_accounts:
    acc_data = acc.to_dict()
    email = acc_data.get('email', '')
    if email == 'bradythomas99@gmail.com':
        print(f'Found matching account in dev:')
        print(f'  Account ID: {acc.id}')
        print(f'  Email: {email}')
        print(f'  Fields: {list(acc_data.keys())}')
        print(f'\n  Full data:')
        for key, value in acc_data.items():
            print(f'    {key}: {value}')
