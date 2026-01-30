#!/usr/bin/env python3
"""
List all users under the specified account and clean up invalid ones
"""

from google.cloud import firestore

prod_db = firestore.Client(project='bravo-prod-465323')

# The account you're logged into
account_id = 'ktWXqeaFI3di7lQGM09Zm0fSSru2'

# Get users subcollection
users_ref = prod_db.collection('accounts').document(account_id).collection('users')

# Use list_documents to get ALL documents including ones without data
all_user_refs = users_ref.list_documents()

print(f'\nListing ALL user documents under account {account_id}:\n')

valid_users = []
invalid_users = []

for user_ref in all_user_refs:
    user_id = user_ref.id
    
    # Try to get the document data
    try:
        doc = user_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            has_created_at = 'created_at' in data
            display_name = data.get('display_name', 'N/A')
            
            if has_created_at:
                valid_users.append({
                    'id': user_id,
                    'display_name': display_name,
                    'ref': user_ref
                })
                print(f'✅ VALID: {user_id}')
                print(f'   Display Name: {display_name}')
                print(f'   Fields: {list(data.keys())}')
            else:
                invalid_users.append({
                    'id': user_id,
                    'display_name': display_name,
                    'ref': user_ref,
                    'data': data
                })
                print(f'❌ INVALID: {user_id}')
                print(f'   Display Name: {display_name}')
                print(f'   Fields: {list(data.keys())}')
                print(f'   Missing: created_at')
        else:
            # Document path exists but has no data (shown in italics in console)
            invalid_users.append({
                'id': user_id,
                'display_name': 'NO DATA',
                'ref': user_ref,
                'data': None
            })
            print(f'❌ INVALID (italics): {user_id}')
            print(f'   No document data - path only')
            
        print()
        
    except Exception as e:
        print(f'⚠️  Error reading {user_id}: {e}\n')

print('=' * 60)
print(f'Valid users: {len(valid_users)}')
print(f'Invalid users: {len(invalid_users)}')
print('=' * 60)

if invalid_users:
    print('\n⚠️  These invalid users will be DELETED:')
    for inv in invalid_users:
        print(f'  - {inv["id"]} ({inv["display_name"]})')
    
    print()
    confirm = input('Delete these invalid users? (yes/no): ').strip().lower()
    
    if confirm == 'yes':
        for inv in invalid_users:
            try:
                inv['ref'].delete()
                print(f'  ✅ Deleted {inv["id"]}')
            except Exception as e:
                print(f'  ❌ Error deleting {inv["id"]}: {e}')
        print('\n✅ Cleanup complete!')
        print(f'Remaining valid users: {len(valid_users)}')
    else:
        print('\n❌ Cancelled')
else:
    print('\n✅ No invalid users found!')
