#!/usr/bin/env python3
"""
Fix account UID mapping by creating account documents for prod Firebase users
that match existing email addresses from dev accounts
"""

from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials, auth

# Initialize Firebase Admin for prod
try:
    prod_app = firebase_admin.get_app('prod')
except ValueError:
    cred = credentials.ApplicationDefault()
    prod_app = firebase_admin.initialize_app(cred, {'projectId': 'bravo-prod-465323'}, name='prod')

# Initialize Firestore
prod_db = firestore.Client(project='bravo-prod-465323')

# Get the current Firebase user
current_uid = 'ktWXqeaFI3di7lQGM09Zm0fSSru2'

try:
    user = auth.get_user(current_uid, app=prod_app)
    print(f'\nFirebase Auth User:')
    print(f'  UID: {user.uid}')
    print(f'  Email: {user.email}')
    print()

    # Check if this email exists in the accounts collection with a different UID
    accounts = list(prod_db.collection('accounts').stream())
    
    matching_account = None
    for acc in accounts:
        data = acc.to_dict()
        if data.get('email') == user.email:
            matching_account = (acc.id, data)
            print(f'Found account with same email but different UID!')
            print(f'  Old Account ID (from dev): {acc.id}')
            print(f'  New Account ID (prod Firebase): {user.uid}')
            print(f'  Email: {data.get("email")}')
            print(f'  Name: {data.get("account_name")}')
            break
    
    if matching_account:
        old_uid, account_data = matching_account
        
        print(f'\n⚠️  This will:')
        print(f'   1. Copy account data from {old_uid} to {user.uid}')
        print(f'   2. Keep the old account as backup')
        print()
        
        confirm = input('Proceed? (yes/no): ').strip().lower()
        if confirm == 'yes':
            # Create new account document with correct UID
            prod_db.collection('accounts').document(user.uid).set(account_data)
            print(f'✅ Created account document for {user.uid}')
            print(f'   You can now log in with {user.email}')
        else:
            print('❌ Cancelled')
    else:
        print(f'❌ No account found with email {user.email}')
        print(f'   Available accounts:')
        for acc in accounts:
            data = acc.to_dict()
            print(f'     - {data.get("email")}')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
