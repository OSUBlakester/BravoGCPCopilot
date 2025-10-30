#!/usr/bin/env python3
"""
Debug script to investigate the admin images browse 403 issue
"""

import asyncio
import os
import sys
from google.cloud import firestore
from firebase_admin import credentials, initialize_app, auth
import firebase_admin
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin SDK
try:
    # Try to get existing app first
    firebase_app = firebase_admin.get_app()
    print("Using existing Firebase app")
except ValueError:
    # Initialize new app
    if os.path.exists('bravo-aac-firebase-adminsdk-key.json'):
        cred = credentials.Certificate('bravo-aac-firebase-adminsdk-key.json')
        firebase_app = initialize_app(cred)
        print("Initialized Firebase app with service account key")
    else:
        print("ERROR: bravo-aac-firebase-adminsdk-key.json not found")
        sys.exit(1)

# Initialize Firestore
firestore_db = firestore.Client()

# Constants from server.py
FIRESTORE_ACCOUNTS_COLLECTION = "accounts"
FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION = "aac_users"

async def check_user_access_issue():
    """Check if the specific user ID exists and debug the 403 issue"""
    
    # The problematic user ID from the error
    problem_user_id = "6246c694-2b96-468d-a3bf-10abafd4fbee"
    
    print(f"Investigating user ID: {problem_user_id}")
    print("=" * 60)
    
    # First, let's find which accounts this user belongs to
    print("\n1. Searching for accounts that contain this user ID...")
    
    accounts_collection = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION)
    accounts = await asyncio.to_thread(accounts_collection.get)
    
    found_accounts = []
    
    for account_doc in accounts:
        account_id = account_doc.id
        account_data = account_doc.to_dict()
        
        # Check if this user exists under this account
        user_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION).document(problem_user_id)
        user_doc = await asyncio.to_thread(user_doc_ref.get)
        
        if user_doc.exists:
            found_accounts.append({
                'account_id': account_id,
                'account_email': account_data.get('email', 'Unknown'),
                'user_data': user_doc.to_dict()
            })
    
    print(f"Found user in {len(found_accounts)} account(s):")
    for account_info in found_accounts:
        print(f"  - Account ID: {account_info['account_id']}")
        print(f"    Email: {account_info['account_email']}")
        print(f"    User data: {account_info['user_data']}")
        print()
    
    if not found_accounts:
        print("❌ User ID not found in any account!")
        print("\nThis explains the 403 error. The user ID doesn't exist in Firestore.")
        print("\nPossible solutions:")
        print("1. Clear session storage and re-authenticate")
        print("2. Check if the user profile was accidentally deleted")
        print("3. Recreate the user profile")
        
        # Let's check if there are any users with similar IDs
        print("\n2. Looking for similar user IDs...")
        all_user_ids = set()
        
        for account_doc in accounts:
            account_id = account_doc.id
            users_collection = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
            users = await asyncio.to_thread(users_collection.get)
            
            for user_doc in users:
                all_user_ids.add(user_doc.id)
        
        # Look for IDs that are similar to the problem ID
        problem_prefix = problem_user_id[:8]  # First 8 characters
        similar_ids = [uid for uid in all_user_ids if uid.startswith(problem_prefix)]
        
        if similar_ids:
            print(f"Found {len(similar_ids)} user IDs with similar prefix '{problem_prefix}':")
            for uid in similar_ids[:10]:  # Show first 10
                print(f"  - {uid}")
        else:
            print(f"No user IDs found with similar prefix '{problem_prefix}'")
    
    return found_accounts

async def check_common_issues():
    """Check for common authentication issues"""
    print("\n3. Checking for common issues...")
    
    # Check for demo accounts
    demo_accounts = []
    accounts_collection = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION)
    accounts = await asyncio.to_thread(accounts_collection.get)
    
    for account_doc in accounts:
        account_data = account_doc.to_dict()
        email = account_data.get('email', '')
        if 'demo' in email.lower():
            demo_accounts.append({
                'account_id': account_doc.id,
                'email': email
            })
    
    if demo_accounts:
        print(f"Found {len(demo_accounts)} demo accounts:")
        for demo in demo_accounts:
            print(f"  - {demo['email']} ({demo['account_id']})")
    
    # Check admin account
    admin_account = None
    for account_doc in accounts:
        account_data = account_doc.to_dict()
        if account_data.get('email') == 'admin@talkwithbravo.com':
            admin_account = {
                'account_id': account_doc.id,
                'email': account_data.get('email'),
                'data': account_data
            }
            break
    
    if admin_account:
        print(f"\nAdmin account found: {admin_account['account_id']}")
        
        # Check users under admin account
        users_collection = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(admin_account['account_id']).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        users = await asyncio.to_thread(users_collection.get)
        
        print(f"Admin account has {len(users)} users:")
        for user_doc in users:
            user_data = user_doc.to_dict()
            print(f"  - {user_doc.id}: {user_data.get('name', 'Unnamed')}")
    else:
        print("\n❌ Admin account not found!")

async def main():
    print("Debug Admin Images Browse 403 Issue")
    print("="*50)
    
    found_accounts = await check_user_access_issue()
    await check_common_issues()
    
    print("\n" + "="*50)
    print("Debug Summary:")
    if found_accounts:
        print("✅ User ID exists in Firestore")
        print("The 403 error is likely caused by a different issue.")
        print("Check the server logs for more specific error messages.")
    else:
        print("❌ User ID does not exist in Firestore")
        print("This is the root cause of the 403 error.")
        print("\nRecommended fixes:")
        print("1. Clear browser session storage and re-authenticate")
        print("2. Use a different user profile that exists")
        print("3. Create the missing user profile")

if __name__ == "__main__":
    asyncio.run(main())