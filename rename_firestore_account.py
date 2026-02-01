#!/usr/bin/env python3
"""
Rename/migrate a Firestore account document ID from one UID to another.
Useful when you need to link existing Firestore data to a new Firebase Auth user.
"""

from google.cloud import firestore
import sys

def copy_account_data(source_account_id, dest_account_id, project_id='bravo-dev-465400'):
    """Copy all data from one account to another, then delete the source"""
    
    db = firestore.Client(project=project_id)
    
    print(f"\n{'='*70}")
    print("Rename Firestore Account")
    print(f"{'='*70}")
    print(f"Project:  {project_id}")
    print(f"From:     {source_account_id}")
    print(f"To:       {dest_account_id}")
    print(f"{'='*70}\n")
    
    # Get source account
    source_ref = db.collection('accounts').document(source_account_id)
    source_doc = source_ref.get()
    
    if not source_doc.exists:
        print(f"❌ Source account {source_account_id} does not exist!")
        return False
    
    # Check if destination already exists
    dest_ref = db.collection('accounts').document(dest_account_id)
    dest_doc = dest_ref.get()
    
    if dest_doc.exists:
        print(f"⚠️  WARNING: Destination account {dest_account_id} already exists!")
        confirm = input("Overwrite? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Cancelled")
            return False
    
    # Copy account document
    print("\n📄 Copying account document...")
    account_data = source_doc.to_dict()
    dest_ref.set(account_data)
    print("   ✅ Account document copied")
    
    # Get all subcollections (users)
    print("\n📁 Copying subcollections...")
    subcollections = list(source_ref.collections())
    print(f"   Found {len(subcollections)} subcollections")
    
    total_docs = 0
    for subcoll in subcollections:
        print(f"\n  📂 Copying subcollection: {subcoll.id}")
        docs = subcoll.stream()
        doc_count = 0
        
        for doc in docs:
            doc_data = doc.to_dict()
            dest_subcoll_ref = dest_ref.collection(subcoll.id).document(doc.id)
            dest_subcoll_ref.set(doc_data)
            doc_count += 1
            
            # Copy nested subcollections (chat_history, button_logs, etc.)
            nested_colls = list(doc.reference.collections())
            for nested in nested_colls:
                print(f"    📂 Copying nested: {nested.id}")
                nested_docs = nested.stream()
                nested_count = 0
                
                for nested_doc in nested_docs:
                    nested_data = nested_doc.to_dict()
                    dest_nested_ref = dest_subcoll_ref.collection(nested.id).document(nested_doc.id)
                    dest_nested_ref.set(nested_data)
                    nested_count += 1
                
                print(f"       ✅ Copied {nested_count} documents from {nested.id}")
                total_docs += nested_count
        
        print(f"    ✅ Copied {doc_count} documents from {subcoll.id}")
        total_docs += doc_count
    
    print(f"\n✅ All data copied successfully!")
    print(f"   Total documents: {total_docs}")
    
    # Delete source
    print(f"\n🗑️  Deleting source account...")
    confirm = input(f"Delete source account {source_account_id}? (yes/no): ").strip().lower()
    if confirm == 'yes':
        # Delete all subcollections first
        for subcoll in subcollections:
            docs = subcoll.stream()
            for doc in docs:
                # Delete nested subcollections
                nested_colls = list(doc.reference.collections())
                for nested in nested_colls:
                    nested_docs = nested.stream()
                    for nested_doc in nested_docs:
                        nested_doc.reference.delete()
                doc.reference.delete()
        
        # Delete main account document
        source_ref.delete()
        print("   ✅ Source account deleted")
    else:
        print("   ⚠️  Source account kept (you can delete it manually later)")
    
    print(f"\n{'='*70}")
    print("✅ Migration Complete!")
    print(f"{'='*70}")
    print(f"New Account ID: {dest_account_id}")
    print(f"Total documents: {total_docs}")
    print(f"{'='*70}\n")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Rename a Firestore account document ID')
    parser.add_argument('--source-account', required=True,
                       help='Source account ID (Firebase Auth UID)')
    parser.add_argument('--dest-account', required=True,
                       help='Destination account ID (new Firebase Auth UID)')
    parser.add_argument('--project', default='bravo-dev-465400',
                       help='GCP project ID')
    
    args = parser.parse_args()
    
    copy_account_data(args.source_account, args.dest_account, args.project)
