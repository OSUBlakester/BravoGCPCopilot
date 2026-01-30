#!/usr/bin/env python3
"""
Check account data in production Firestore
"""

from google.cloud import firestore

prod_db = firestore.Client(project='bravo-prod-465323')
account_id = 'ktWXqeaFI3di7lQGM09Zm0fSSru2'

print(f'\n=== Checking account: {account_id} ===\n')

# Check account document
account_ref = prod_db.collection('accounts').document(account_id)
account_doc = account_ref.get()

print(f'Account document exists: {account_doc.exists}')
if account_doc.exists:
    account_data = account_doc.to_dict()
    print(f'Account data:')
    for key, value in account_data.items():
        print(f'  {key}: {value}')
else:
    print('❌ Account document does not exist!')

print('\n=== Users in this account ===\n')

# List all users
users_ref = account_ref.collection('users')
users = users_ref.stream()

user_count = 0
for user in users:
    user_count += 1
    user_data = user.to_dict()
    print(f'User ID: {user.id}')
    print(f'  Document exists: True')
    print(f'  Data fields: {list(user_data.keys())}')
    if 'userName' in user_data:
        print(f'  User Name: {user_data["userName"]}')
    if 'deviceName' in user_data:
        print(f'  Device Name: {user_data["deviceName"]}')
    
    # Check subcollections
    subcollections = list(user.reference.collections())
    if subcollections:
        print(f'  Subcollections: {[s.id for s in subcollections]}')
    print()

if user_count == 0:
    print('❌ No users found in this account!')
else:
    print(f'\n✅ Total users found: {user_count}')

print('\n=== Checking all accounts ===\n')
all_accounts = prod_db.collection('accounts').stream()
for acc in all_accounts:
    acc_data = acc.to_dict()
    email = acc_data.get('email', 'No email')
    print(f'Account: {acc.id}')
    print(f'  Email: {email}')
    
    # Count users
    users_in_account = list(acc.reference.collection('users').stream())
    print(f'  Users: {len(users_in_account)}')
    print()
