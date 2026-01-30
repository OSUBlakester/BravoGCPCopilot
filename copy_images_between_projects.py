#!/usr/bin/env python3
"""
Copy images from ONLY the bravo_images folder inside the aac-images bucket between GCP projects
⚠️  SAFETY: This script is hardcoded to ONLY copy files in the bravo_images/ folder.
⚠️  It will NEVER touch button_audio/, custom_images/, or any other folders.

Usage: python3 copy_images_between_projects.py <source_project> <dest_project> [--delete-existing]
Example: python3 copy_images_between_projects.py dev prod
Example: python3 copy_images_between_projects.py dev prod --delete-existing
"""

import sys
import argparse
from google.cloud import storage

# SAFETY: Hardcoded folder prefix - will NEVER touch other folders
ALLOWED_PREFIX = 'bravo_images/'

# Project configurations
PROJECTS = {
    'dev': 'bravo-dev-465400',
    'test': 'bravo-test-465400',
    'prod': 'bravo-prod-465323'
}

def delete_all_images(dest_project_id, dest_bucket_name):
    """Delete ONLY images in the bravo_images/ folder (hardcoded for safety)"""
    
    print(f"🗑️  Deleting images from gs://{dest_bucket_name}/{ALLOWED_PREFIX}...")
    print(f"   ⚠️  SAFETY: Only deleting files with prefix: {ALLOWED_PREFIX}")
    print()
    
    dest_client = storage.Client(project=dest_project_id)
    dest_bucket = dest_client.bucket(dest_bucket_name)
    
    if not dest_bucket.exists():
        print(f"⚠️  Destination bucket {dest_bucket_name} does not exist, nothing to delete")
        return
    
    # SAFETY: List ONLY blobs with the bravo_images/ prefix
    blobs = list(dest_bucket.list_blobs(prefix=ALLOWED_PREFIX))
    total_blobs = len(blobs)
    
    if total_blobs == 0:
        print("⚠️  No images found in destination bucket")
        return
    
    print(f"Found {total_blobs} images to delete...")
    print()
    
    deleted = 0
    errors = 0
    
    for i, blob in enumerate(blobs, 1):
        try:
            blob.delete()
            print(f"[{i}/{total_blobs}] ✅ Deleted: {blob.name}")
            deleted += 1
        except Exception as e:
            print(f"[{i}/{total_blobs}] ❌ Error deleting {blob.name}: {e}")
            errors += 1
    
    print()
    print("=" * 60)
    print(f"✅ Deleted: {deleted}")
    print(f"❌ Errors:  {errors}")
    print(f"📊 Total:   {total_blobs}")
    print("=" * 60)
    print()

def copy_images(source_project_id, dest_proje/ folder (hardcoded for safety)"""
    
    # SAFETY: Use the aac-images bucket with hardcoded prefix
    source_bucket_name = f"{source_project_id}-aac-images"
    dest_bucket_name = f"{dest_project_id}-aac-images"
    
    print(f"📋 Copying images")
    print(f"   From: gs://{source_bucket_name}/{ALLOWED_PREFIX} (project: {source_project_id})")
    print(f"   To:   gs://{dest_bucket_name}/{ALLOWED_PREFIX} (project: {dest_project_id})")
    print(f"   ⚠️  Hardcoded prefix: {ALLOWED_PREFIX} (for safety)")
    print(f"   ⚠️  Will NOT touch: button_audio/, custom_images/, or any other foldersct_id})")
    print(f"   ⚠️  Hardcoded bucket: {ALLOWED_BUCKET} (for safety)")
    print()
    
    # Initialize storage clients
    source_client = storage.Client(project=source_project_id)
    dest_client = storage.Client(project=dest_project_id)
    
    # Get buckets
    source_bucket = source_client.bucket(source_bucket_name)
    dest_bucket = dest_client.bucket(dest_bucket_name)
    
    # Ensure destination bucket exists
    if not dest_bucket.exists():
        print(f"❌ Destination bucket {dest_bucket_name} does not exist!")
        return
    
    # Delete existing images if requested
    if delete_existing:
        delete_all_images(dest_project_id, dest_bucket_name)
    SAFETY: List ONLY blobs with the bravo_images/ prefix
    blobs = list(source_bucket.list_blobs(prefix=ALLOWED_PREFIX))
    total_blobs = len(blobs)
    
    if total_blobs == 0:
        print(f"⚠️  No images found with prefix {ALLOWED_PREFIX}
        print("⚠️  No images found in source bucket")
        return
    
    print(f"Found {total_blobs} images to copy...")
    print()
    
    copied = 0
    skipped = 0
    errors = 0
    
    for i, source_blob in enumerate(blobs, 1):
        try:
            # Check if blob already exists in destination
            dest_blob = dest_bucket.blob(source_blob.name)
            
            if dest_blob.exists():
                print(f"[{i}/{total_blobs}] ⏭️  Skipping (already exists): {source_blob.name}")
                skipped += 1
            else:
                # Copy blob
                source_bucket.copy_blob(source_blob, dest_bucket, source_blob.name)
                print(f"[{i}/{total_blobs}] ✅ Copied: {source_blob.name}")
                copied += 1
                
        except Exception as e:
            print(f"[{i}/{total_blobs}] ❌ Error copying {source_blob.name}: {e}")
            errors += 1
    
    print()
    print("=" * 60)
    print(f"✅ Copied:  {copied}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"❌ Errors:  {errors}")
    print(f"📊 Total:   {total_blobs}")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(/ folder in aac-images bucket (hardcoded for safety)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 copy_images_between_projects.py dev prod
  python3 copy_images_between_projects.py dev prod --delete-existing

⚠️  SAFETY: This script only copies files in the bravo_images/ folder.
⚠️  It will never touch button_audio/, custom_images/, or any other folderucket.
⚠️  It will never touch aac-images or any other buckets.
        """
    )
    
    parser.add_argument('source', help='Source project (dev/test/prod or full project ID)')
    parser.add_argument('destination', help='Destination project (dev/test/prod or full project ID)')
    parser.add_argument('--delete-existing', action='store_true', 
                       help='Delete all existing images in destination before copying')
    
    args = parser.parse_args()
    
    # Convert shortcuts to project IDs
    source_project = PROJECTS.get(args.source, args.source)
    dest_project = PROJECTS.get(args.destination, args.destination)
    
    # Confirm with user
    source_bucket_name = f"{source_project}-aac-images"
    dest_bucket_name = f"{dest_project}-aac-images"
    
    print()
    print("⚠️  About to copy images:")
    print(f"   Source:      gs://{source_bucket_name}/{ALLOWED_PREFIX}")
    print(f"   Destination: gs://{dest_bucket_name}/{ALLOWED_PREFIX}")
    print(f"   Folder:      {ALLOWED_PREFIX} (hardcoded for safety)")
    if args.delete_existing:
        print(f"   ⚠️  DELETE EXISTING: Yes - all images in {ALLOWED_PREFIX} will be deleted first!")
    else:
        print(f"   DELETE EXISTING: No - existing images will be skipped")
    print()
    print("⚠️  SAFETY: This script ONLY touches files in the bravo_images/ folder.")
    print("⚠️  It will NEVER modify button_audio/, custom_images/, or any other folders.")
    print()
    
    confirm = input("Proceed? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Cancelled")
        sys.exit(0)
    
    print()
    copy_images(source_project, dest_project, args.delete_existing)

if __name__ == "__main__":
    main()
