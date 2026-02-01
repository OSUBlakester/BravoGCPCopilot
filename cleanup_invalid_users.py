#!/usr/bin/env python3
"""
Clean up invalid user documents that were copied from dev to prod
"""

from google.cloud import firestore

prod_db = firestore.Client(project='bravo-prod-465323')

# Get all accounts
accounts = list(prod_db.collection('accounts').stream())

print(f'\nChecking {len(accounts)} accounts for invalid users...\n')

total_users = 0
invalid_users = []

for account in accounts:
    account_id = account.id
    account_data = account.to_dict()
    
    # Get users subcollection
    users_ref = prod_db.collection('accounts').document(account_id).collection('users')
    users = list(users_ref.stream())
    
    if users:
        print(f'Account: {account_data.get("email")} ({account_id})')
        print(f'  Users: {len(users)}')
        
        for user in users:
            total_users += 1
            data = user.to_dict()
            has_created_at = 'created_at' in data
            
            if not has_created_at:
                invalid_users.append({
                    'account_id': account_id,
                    'account_email': account_data.get('email'),
                    'user_id': user.id,
                    'display_name': data.get('display_name', 'N/A'),
                    'fields': list(data.keys())
                })
                print(f'    ❌ INVALID: {user.id} - {data.get("display_name")} (no created_at)')
            else:
                print(f'    ✅ Valid: {user.id} - {data.get("display_name")}')
        print()

print('\n' + '=' * 60)
print(f'Total users found: {total_users}')
print(f'Invalid users: {len(invalid_users)}')

if invalid_users:
    print('\n⚠️  Invalid users that should be deleted:')
    for inv in invalid_users:
        print(f'  - {inv["account_email"]}: {inv["user_id"]} ({inv["display_name"]})')
    
    print()
    confirm = input('Delete these invalid users? (yes/no): ').strip().lower()
    
    if confirm == 'yes':
        for inv in invalid_users:
            try:
                prod_db.collection('accounts').document(inv['account_id']).collection('users').document(inv['user_id']).delete()
                print(f'  ✅ Deleted {inv["user_id"]} from {inv["account_email"]}')
            except Exception as e:
                print(f'  ❌ Error deleting {inv["user_id"]}: {e}')
        print('\n✅ Cleanup complete!')
    else:
        print('\n❌ Cancelled')
else:
    print('\n✅ No invalid users found!')
