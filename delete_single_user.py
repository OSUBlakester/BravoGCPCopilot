#!/usr/bin/env python3
"""
Delete a single specific user document
"""

from google.cloud import firestore

prod_db = firestore.Client(project='bravo-prod-465323')

account_id = 'ktWXqeaFI3di7lQGM09Zm0fSSru2'

# The remaining 3 invalid users
invalid_user_ids = [
    '5d4da3c2-dfa6-43ae-9ff0-6b8064c29ec1',
    'd7f9e4fe-f4a1-430b-894b-7d42035f55d6',
    'f06a04ad-7397-4cc9-b873-0d55a89d691f'
]

for user_id in invalid_user_ids:
    print(f'\nDeleting user: {user_id}\n')

    user_ref = prod_db.collection('accounts').document(account_id).collection('users').document(user_id)

    # Check if document exists
    doc = user_ref.get()
    print(f'Document exists: {doc.exists}')

    if doc.exists:
        data = doc.to_dict()
        print(f'Document has data: {data}')
    else:
        print('Document has no data (italics in console)')

    # List any subcollections
    subcollections = list(user_ref.collections())
    print(f'Subcollections: {len(subcollections)}')
    for subcoll in subcollections:
        print(f'  - {subcoll.id}')

    print('Attempting to delete...')

    try:
        # Try to delete the document
        user_ref.delete()
        print('✅ Successfully deleted!')
    except Exception as e:
        print(f'❌ Error: {e}')
        print(f'Error type: {type(e).__name__}')

print('\n✅ All invalid users deleted!')
