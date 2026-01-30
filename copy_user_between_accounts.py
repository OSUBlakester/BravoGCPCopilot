#!/usr/bin/env python3
"""
Copy a user/profile from one account to another (across projects or within same project)
"""

from google.cloud import firestore
import uuid

def copy_subcollection(source_doc_ref, dest_doc_ref, subcoll_name, source_db, dest_db, batch_size=100):
    """Recursively copy a subcollection with batching for large collections"""
    
    print(f"  📂 Copying subcollection: {subcoll_name}")
    
    source_subcoll = source_doc_ref.collection(subcoll_name)
    dest_subcoll = dest_doc_ref.collection(subcoll_name)
    
    doc_count = 0
    batch = dest_db.batch()
    batch_count = 0
    
    # Stream documents
    docs = source_subcoll.stream()
    
    for doc in docs:
        doc_data = doc.to_dict()
        
        # Add to batch
        batch.set(dest_subcoll.document(doc.id), doc_data)
        batch_count += 1
        doc_count += 1
        
        # Commit batch when it reaches batch_size
        if batch_count >= batch_size:
            batch.commit()
            print(f"    💾 Committed batch ({doc_count} docs so far)")
            batch = dest_db.batch()
            batch_count = 0
        
        # Recursively copy any nested subcollections
        for nested_subcoll in doc.reference.collections():
            copy_subcollection(doc.reference, dest_subcoll.document(doc.id), nested_subcoll.id, source_db, dest_db)
    
    # Commit any remaining documents
    if batch_count > 0:
        batch.commit()
    
    print(f"    ✅ Copied {doc_count} documents from {subcoll_name}")
    return doc_count

def copy_user(source_project, source_account_id, source_user_id, 
              dest_project, dest_account_id, dest_user_id=None):
    """Copy a user and all subcollections from source to destination"""
    
    # Initialize clients
    source_db = firestore.Client(project=source_project)
    dest_db = firestore.Client(project=dest_project)
    
    # Generate new user ID if not provided
    if not dest_user_id:
        dest_user_id = str(uuid.uuid4())
    
    print(f"\n{'='*70}")
    print("Copy User Configuration:")
    print(f"{'='*70}")
    print(f"Source:")
    print(f"  Project:  {source_project}")
    print(f"  Account:  {source_account_id}")
    print(f"  User:     {source_user_id}")
    print(f"\nDestination:")
    print(f"  Project:  {dest_project}")
    print(f"  Account:  {dest_account_id}")
    print(f"  User:     {dest_user_id}")
    print(f"{'='*70}\n")
    
    # Get source user document
    source_user_ref = source_db.collection('accounts').document(source_account_id).collection('users').document(source_user_id)
    source_user_doc = source_user_ref.get()
    
    if not source_user_doc.exists:
        print(f"❌ Source user does not exist!")
        return
    
    source_user_data = source_user_doc.to_dict()
    print(f"✅ Found source user")
    print(f"   User name: {source_user_data.get('userName', 'N/A')}")
    print(f"   Device name: {source_user_data.get('deviceName', 'N/A')}")
    
    # Check destination user
    dest_user_ref = dest_db.collection('accounts').document(dest_account_id).collection('users').document(dest_user_id)
    dest_user_doc = dest_user_ref.get()
    
    if dest_user_doc.exists:
        print(f"\n⚠️  WARNING: Destination user already exists!")
        confirm = input("Overwrite? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Cancelled")
            return
    
    # Copy user document
    print(f"\n📄 Copying user document...")
    dest_user_ref.set(source_user_data)
    print(f"   ✅ User document copied")
    
    # Get all subcollections
    subcollections = list(source_user_ref.collections())
    print(f"\n📁 Found {len(subcollections)} subcollections to copy")
    
    total_docs = 0
    for subcoll in subcollections:
        docs_copied = copy_subcollection(source_user_ref, dest_user_ref, subcoll.id, source_db, dest_db)
        total_docs += docs_copied
    
    print(f"\n{'='*70}")
    print("✅ Copy Complete!")
    print(f"{'='*70}")
    print(f"User ID: {dest_user_id}")
    print(f"User Name: {source_user_data.get('userName', 'N/A')}")
    print(f"Device Name: {source_user_data.get('deviceName', 'N/A')}")
    print(f"Subcollections: {len(subcollections)}")
    print(f"Total documents: {total_docs}")
    print(f"{'='*70}\n")
    
    return dest_user_id

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Copy a user/profile between accounts')
    parser.add_argument('--source-project', default='bravo-dev-465400', 
                       help='Source GCP project ID')
    parser.add_argument('--source-account', required=True,
                       help='Source account ID')
    parser.add_argument('--source-user', required=True,
                       help='Source user ID')
    parser.add_argument('--dest-project', default='bravo-prod-465323',
                       help='Destination GCP project ID')
    parser.add_argument('--dest-account', required=True,
                       help='Destination account ID')
    parser.add_argument('--dest-user', default=None,
                       help='Destination user ID (auto-generated if not provided)')
    
    args = parser.parse_args()
    
    copy_user(
        args.source_project,
        args.source_account,
        args.source_user,
        args.dest_project,
        args.dest_account,
        args.dest_user
    )
