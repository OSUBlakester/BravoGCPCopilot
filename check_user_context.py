#!/usr/bin/env python3
"""
Check what context data is available for a user to help debug LLM issues
"""

from google.cloud import firestore
import json

# Configuration
project = 'bravo-prod-465323'
account_id = input("Enter account ID: ").strip()
user_id = input("Enter user ID: ").strip()

print(f'\n{"="*70}')
print(f'Checking Context Data for User')
print(f'{"="*70}')
print(f'Project:  {project}')
print(f'Account:  {account_id}')
print(f'User:     {user_id}')
print(f'{"="*70}\n')

db = firestore.Client(project=project)

# Check user info (narrative, current state)
print("📋 USER INFO (info/user_narrative):")
print("-" * 70)
user_info_ref = db.collection('accounts').document(account_id).collection('users').document(user_id).collection('info').document('user_narrative')
user_info = user_info_ref.get()
if user_info.exists:
    data = user_info.to_dict()
    print(f"Narrative: {data.get('narrative', 'N/A')[:200]}...")
    print(f"Current Mood: {data.get('currentMood', 'Not set')}")
    print(json.dumps(data, indent=2))
else:
    print("❌ No user_narrative document found")

print("\n📍 CURRENT STATE (info/current_state):")
print("-" * 70)
current_state_ref = db.collection('accounts').document(account_id).collection('users').document(user_id).collection('info').document('current_state')
current_state = current_state_ref.get()
if current_state.exists:
    data = current_state.to_dict()
    print(json.dumps(data, indent=2))
else:
    print("❌ No current_state document found")

print("\n📅 DIARY ENTRIES (first 5):")
print("-" * 70)
diary_ref = db.collection('accounts').document(account_id).collection('users').document(user_id).collection('diary_entries')
diary_entries = list(diary_ref.order_by('date', direction=firestore.Query.DESCENDING).limit(5).stream())
if diary_entries:
    for entry in diary_entries:
        data = entry.to_dict()
        print(f"\nDate: {data.get('date')}")
        print(f"Title: {data.get('title', 'N/A')}")
        print(f"Entry: {data.get('entry', 'N/A')[:150]}...")
else:
    print("❌ No diary entries found")

print("\n👥 FRIENDS & FAMILY (info/friends_family):")
print("-" * 70)
friends_ref = db.collection('accounts').document(account_id).collection('users').document(user_id).collection('info').document('friends_family')
friends = friends_ref.get()
if friends.exists:
    data = friends.to_dict()
    print(json.dumps(data, indent=2))
else:
    print("❌ No friends_family document found")

print(f'\n{"="*70}')
print('✅ Context check complete')
print(f'{"="*70}\n')
