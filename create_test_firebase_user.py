#!/usr/bin/env python3
"""
Create a test Firebase Auth user in dev environment to access copied user data.
This creates a Firebase Auth account that can log into the web UI.
"""

import firebase_admin
from firebase_admin import credentials, auth
import sys

def create_test_user(email, password, display_name="Test User"):
    """Create a Firebase Auth user"""
    
    # Initialize Firebase Admin if not already done
    try:
        firebase_admin.get_app()
        print("✅ Firebase Admin already initialized")
    except ValueError:
        # Initialize Firebase Admin with default credentials (uses gcloud auth)
        try:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                'projectId': 'bravo-dev-465400'
            })
            print("✅ Firebase Admin initialized for bravo-dev-465400")
        except Exception as e:
            print(f"❌ Failed to initialize Firebase Admin: {e}")
            sys.exit(1)
    
    try:
        # Check if user already exists
        try:
            existing_user = auth.get_user_by_email(email)
            print(f"\n⚠️  User with email {email} already exists!")
            print(f"   UID: {existing_user.uid}")
            print(f"   Display Name: {existing_user.display_name}")
            print(f"   Created: {existing_user.user_metadata.creation_timestamp}")
            
            confirm = input("\nDo you want to use this existing user? (yes/no): ").strip().lower()
            if confirm == 'yes':
                return existing_user.uid
            else:
                print("❌ Cancelled")
                return None
                
        except auth.UserNotFoundError:
            # User doesn't exist, create new one
            pass
        
        # Create the user
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=False
        )
        
        print(f"\n{'='*70}")
        print("✅ Firebase Auth User Created Successfully!")
        print(f"{'='*70}")
        print(f"Email:        {email}")
        print(f"Password:     {password}")
        print(f"UID:          {user.uid}")
        print(f"Display Name: {display_name}")
        print(f"{'='*70}\n")
        
        print("📝 Next Steps:")
        print("1. This Firebase Auth user (UID) represents an 'account' in Firestore")
        print("2. You can now create AAC user profiles under this account")
        print("3. Or you can manually update Firestore to link existing data to this UID")
        print(f"\nTo link existing data, update the account document ID from:")
        print(f"  OLD: ktWXqeaFI3di7lQGM09Zm0fSSru2")
        print(f"  NEW: {user.uid}")
        
        return user.uid
        
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create a test Firebase Auth user in dev environment')
    parser.add_argument('--email', required=True, help='Email address for the new user')
    parser.add_argument('--password', required=True, help='Password for the new user')
    parser.add_argument('--name', default='Test User Dev', help='Display name for the user')
    
    args = parser.parse_args()
    
    if len(args.password) < 6:
        print("❌ Error: Password must be at least 6 characters long")
        sys.exit(1)
    
    create_test_user(args.email, args.password, args.name)
