#!/usr/bin/env python3
"""
List all users in an account
"""

from google.cloud import firestore

project = 'bravo-prod-465323'
account_id = 'EhELukYIzHdPxR6ZzcW5w4cXRE52'

print(f'\n{"="*70}')
print(f'Listing Users in Account')
print(f'{"="*70}')
print(f'Project:  {project}')
print(f'Account:  {account_id}')
print(f'{"="*70}\n')

db = firestore.Client(project=project)
users_ref = db.collection('accounts').document(account_id).collection('users')

users = list(users_ref.stream())
print(f'Found {len(users)} users:\n')

for user in users:
    user_data = user.to_dict()
    user_name = user_data.get('userName', 'N/A')
    device_name = user_data.get('deviceName', 'N/A')
    
    print(f'User ID: {user.id}')
    print(f'  User Name: {user_name}')
    print(f'  Device Name: {device_name}')
    print()

print(f'{"="*70}\n')
