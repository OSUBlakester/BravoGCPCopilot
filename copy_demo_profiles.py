#!/usr/bin/env python3
"""
Script to copy AAC user profiles from demo@talkwithbravo.com to demoreadonly@talkwithbravo.com
This is a one-time migration script for setting up the demo readonly account.
"""

import asyncio
import argparse
import logging
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials, auth
import uuid
from datetime import datetime as dt
import json
import sys
import os

# Add the current directory to the path to import config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import configuration
try:
    from config import FIRESTORE_PROJECT_ID, FIRESTORE_ACCOUNTS_COLLECTION, FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION
except ImportError:
    print("Error: Could not import config.py. Make sure it exists and contains the required constants.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Firebase Admin (if not already done)
try:
    firebase_admin.get_app()
except ValueError:
    # Initialize Firebase Admin with default credentials
    try:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    except Exception as e:
        logging.error(f"Failed to initialize Firebase Admin: {e}")
        sys.exit(1)

# Initialize Firestore
try:
    firestore_db = firestore.Client(project=FIRESTORE_PROJECT_ID)
except Exception as e:
    logging.error(f"Failed to initialize Firestore client: {e}")
    sys.exit(1)

async def get_account_id_by_email(email):
    """Get the account ID for a given email address"""
    try:
        # Get user by email from Firebase Auth
        user_record = auth.get_user_by_email(email)
        account_id = user_record.uid
        logging.info(f"Found account ID {account_id} for email {email}")
        return account_id
    except auth.UserNotFoundError:
        logging.error(f"No user found with email: {email}")
        return None
    except Exception as e:
        logging.error(f"Error getting account for email {email}: {e}")
        return None

async def get_users_from_account(account_id):
    """Get all AAC users from an account"""
    try:
        users_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        users_docs = users_ref.stream()
        
        users = []
        for doc in users_docs:
            user_data = doc.to_dict()
            user_data['aac_user_id'] = doc.id
            users.append(user_data)
        
        logging.info(f"Found {len(users)} users in account {account_id}")
        return users
    except Exception as e:
        logging.error(f"Error getting users from account {account_id}: {e}")
        return []


def copy_subcollection_recursive(source_doc_ref, target_doc_ref):
    """Recursively copy all nested subcollections from one user doc to another."""
    for subcollection in source_doc_ref.collections():
        source_subcoll = source_doc_ref.collection(subcollection.id)
        target_subcoll = target_doc_ref.collection(subcollection.id)

        for doc in source_subcoll.stream():
            doc_data = doc.to_dict()
            target_doc = target_subcoll.document(doc.id)
            target_doc.set(doc_data)
            copy_subcollection_recursive(doc.reference, target_doc)


def delete_subcollections_recursive(doc_ref):
    """Recursively delete all nested subcollections under a document."""
    for subcollection in doc_ref.collections():
        for doc in subcollection.stream():
            delete_subcollections_recursive(doc.reference)
            doc.reference.delete()

async def copy_user_data(source_account_id, source_user_id, target_account_id, target_user_id):
    """Copy all user data from source to target"""
    try:
        # Source paths
        source_user_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(source_account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION).document(source_user_id)
        
        # Target paths
        target_user_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(target_account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION).document(target_user_id)

        await asyncio.to_thread(copy_subcollection_recursive, source_user_ref, target_user_ref)
        
        logging.info(f"Successfully copied all data from {source_user_id} to {target_user_id}")
        
    except Exception as e:
        logging.error(f"Error copying user data from {source_user_id} to {target_user_id}: {e}")
        raise

async def create_user_in_account(account_id, user_data, new_user_id=None):
    """Create a new user in the target account"""
    try:
        if not new_user_id:
            new_user_id = str(uuid.uuid4())
        
        # Create user document
        user_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION).document(new_user_id)
        
        # Prepare user data (remove the aac_user_id as it will be the document ID)
        clean_user_data = {k: v for k, v in user_data.items() if k != 'aac_user_id'}
        clean_user_data['created_at'] = dt.now().isoformat()
        clean_user_data['last_updated'] = dt.now().isoformat()
        
        # Set the user document
        user_ref.set(clean_user_data)
        
        logging.info(f"Created user {new_user_id} in account {account_id} with display name: {clean_user_data.get('display_name', 'Unknown')}")
        return new_user_id
        
    except Exception as e:
        logging.error(f"Error creating user in account {account_id}: {e}")
        raise

async def delete_all_users_from_account(account_id):
    """Delete all AAC users from an account"""
    try:
        users_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        users_docs = users_ref.stream()
        
        deleted_count = 0
        for doc in users_docs:
            user_data = doc.to_dict()
            display_name = user_data.get('display_name', 'Unknown')

            user_doc_ref = users_ref.document(doc.id)
            await asyncio.to_thread(delete_subcollections_recursive, user_doc_ref)
            
            # Delete the user document itself
            doc.reference.delete()
            deleted_count += 1
            logging.info(f"Deleted user {doc.id} ({display_name}) from account {account_id}")
        
        logging.info(f"Successfully deleted {deleted_count} users from account {account_id}")
        return deleted_count
        
    except Exception as e:
        logging.error(f"Error deleting users from account {account_id}: {e}")
        raise

async def update_account_user_limit(account_id, new_limit):
    """Update the user limit for an account"""
    try:
        account_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id)
        account_ref.update({
            "num_users_allowed": new_limit,
            "last_updated": dt.now().isoformat()
        })
        logging.info(f"Updated account {account_id} user limit to {new_limit}")
    except Exception as e:
        logging.error(f"Error updating account user limit: {e}")


def parse_args():
    parser = argparse.ArgumentParser(description="Copy demo profiles from a read-write account to a read-only account")
    parser.add_argument("--source-email", default="demo@talkwithbravo.com", help="Source Firebase Auth email (used if --source-account-id is not provided)")
    parser.add_argument("--target-email", default="demoreadonly@talkwithbravo.com", help="Target Firebase Auth email (used if --target-account-id is not provided)")
    parser.add_argument("--source-account-id", default=None, help="Direct source Firestore account ID (skips Firebase Auth lookup)")
    parser.add_argument("--target-account-id", default=None, help="Direct target Firestore account ID (skips Firebase Auth lookup)")
    parser.add_argument("--yes", action="store_true", help="Skip interactive confirmation prompt")
    return parser.parse_args()

async def main():
    args = parse_args()

    print("🚀 Starting profile copy process...")
    print("=" * 60)

    source_email = args.source_email
    target_email = args.target_email

    source_account_id = args.source_account_id
    target_account_id = args.target_account_id

    if source_account_id:
        print(f"📌 Using source account ID: {source_account_id}")
    else:
        print(f"📧 Getting account ID for {source_email}...")
        source_account_id = await get_account_id_by_email(source_email)
        if not source_account_id:
            print(f"❌ Could not find source account for {source_email}")
            return

    if target_account_id:
        print(f"📌 Using target account ID: {target_account_id}")
    else:
        print(f"📧 Getting account ID for {target_email}...")
        target_account_id = await get_account_id_by_email(target_email)
        if not target_account_id:
            print(f"❌ Could not find target account for {target_email}")
            return
    
    print(f"✅ Source Account ID: {source_account_id}")
    print(f"✅ Target Account ID: {target_account_id}")
    print()
    
    # Get users from source account
    print(f"👥 Getting profiles from {source_email}...")
    source_users = await get_users_from_account(source_account_id)
    
    if not source_users:
        print(f"❌ No profiles found in {source_email}")
        return
    
    print(f"✅ Found {len(source_users)} profiles:")
    for i, user in enumerate(source_users, 1):
        display_name = user.get('display_name', 'Unknown')
        print(f"   {i}. {display_name} (ID: {user['aac_user_id']})")
    print()
    
    # Check if target account already has users
    print(f"🔍 Checking existing profiles in {target_email}...")
    existing_target_users = await get_users_from_account(target_account_id)
    
    if existing_target_users:
        print(f"⚠️  Found {len(existing_target_users)} existing profiles in target account:")
        for user in existing_target_users:
            display_name = user.get('display_name', 'Unknown')
            print(f"   - {display_name}")
        print(f"\n🚨 WARNING: This will DELETE all {len(existing_target_users)} existing profiles and replace them with the {len(source_users)} profiles from the source account.")
    else:
        print("✅ Target account is empty, ready to copy profiles")
    print()
    
    # Confirm the operation
    print("🚨 CONFIRMATION REQUIRED 🚨")
    if existing_target_users:
        print(f"This will:")
        print(f"   1. DELETE {len(existing_target_users)} existing profiles in {target_email}")
        print(f"   2. COPY {len(source_users)} profiles from {source_email}")
        print(f"   3. Result: {target_email} will have exactly {len(source_users)} profiles (replacing all existing ones)")
    else:
        print(f"This will copy {len(source_users)} profiles from:")
        print(f"   FROM: {source_email}")
        print(f"   TO:   {target_email}")
    print()
    if not args.yes:
        response = input("Are you sure you want to proceed? (y/N): ").lower()
        if response != 'y':
            print("❌ Operation cancelled by user")
            return
    else:
        print("✅ Confirmation bypassed with --yes")
    
    print()
    print("🔄 Starting profile replacement process...")
    print("=" * 60)
    
    # Delete existing profiles if any
    if existing_target_users:
        print(f"🗑️  Deleting {len(existing_target_users)} existing profiles from {target_email}...")
        try:
            deleted_count = await delete_all_users_from_account(target_account_id)
            print(f"   ✅ Successfully deleted {deleted_count} existing profiles")
        except Exception as e:
            print(f"   ❌ Error deleting existing profiles: {e}")
            print("❌ Aborting operation due to deletion error")
            return
        print()
    
    # Copy each user
    copied_count = 0
    for i, user in enumerate(source_users, 1):
        display_name = user.get('display_name', 'Unknown')
        source_user_id = user['aac_user_id']
        
        print(f"📋 [{i}/{len(source_users)}] Copying profile: {display_name}")
        
        try:
            # Create new user in target account
            new_user_id = await create_user_in_account(target_account_id, user)
            
            # Copy all user data
            await copy_user_data(source_account_id, source_user_id, target_account_id, new_user_id)
            
            copied_count += 1
            print(f"   ✅ Successfully copied {display_name}")
            
        except Exception as e:
            print(f"   ❌ Failed to copy {display_name}: {e}")
            continue
    
    print()
    print("🔧 Updating account settings...")
    
    # Update target account user limit
    new_user_limit = copied_count + 2  # +2 for buffer
    await update_account_user_limit(target_account_id, new_user_limit)
    
    print()
    print("🎉 PROFILE REPLACEMENT COMPLETE!")
    print("=" * 60)
    print(f"✅ Successfully copied {copied_count} out of {len(source_users)} profiles")
    print(f"📧 Target account: {target_email}")
    print(f"👥 Total profiles in target: {copied_count}")
    print(f"🔧 Updated user limit to: {new_user_limit}")
    print()
    print("🔍 Summary of copied profiles:")
    for i, user in enumerate(source_users, 1):
        if i <= copied_count:
            display_name = user.get('display_name', 'Unknown')
            print(f"   ✅ {display_name}")
    
    print()
    print("🚀 The demoreadonly@talkwithbravo.com account is now ready!")
    print("   You can use it for demo purposes on your landing page.")

if __name__ == "__main__":
    asyncio.run(main())
