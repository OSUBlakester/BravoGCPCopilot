#!/usr/bin/env python3
"""
Delete unindexed images from the bravo_images folder
⚠️  This will permanently delete files from GCS buckets!
"""

import sys
from google.cloud import storage

def delete_unindexed_images(project_id, file_list_path):
    """Delete images listed in the unindexed images file"""
    
    print(f"\n{'='*70}")
    print(f"Deleting unindexed images from: {project_id}")
    print(f"{'='*70}\n")
    
    # Read the file list
    print(f"Reading file list from: {file_list_path}")
    with open(file_list_path, 'r') as f:
        lines = f.readlines()
    
    # Skip the header lines and get file paths
    files_to_delete = []
    for line in lines:
        line = line.strip()
        if line.startswith('bravo_images/'):
            files_to_delete.append(line)
    
    print(f"Found {len(files_to_delete)} files to delete\n")
    
    if len(files_to_delete) == 0:
        print("❌ No files to delete!")
        return
    
    # Show sample
    print("Sample files to delete (first 10):")
    for i, filepath in enumerate(files_to_delete[:10], 1):
        print(f"  {i}. {filepath}")
    if len(files_to_delete) > 10:
        print(f"  ... and {len(files_to_delete) - 10} more")
    print()
    
    # Confirm
    print("⚠️  WARNING: This will PERMANENTLY delete these files!")
    print(f"⚠️  Project: {project_id}")
    print(f"⚠️  Total files: {len(files_to_delete)}")
    print()
    
    confirm = input("Type 'DELETE' to confirm: ").strip()
    if confirm != 'DELETE':
        print("❌ Cancelled - deletion aborted")
        sys.exit(0)
    
    # Initialize storage client
    storage_client = storage.Client(project=project_id)
    bucket_name = f"{project_id}-aac-images"
    bucket = storage_client.bucket(bucket_name)
    
    print(f"\n{'='*70}")
    print("Deleting files...")
    print(f"{'='*70}\n")
    
    deleted = 0
    errors = 0
    
    for i, filepath in enumerate(files_to_delete, 1):
        try:
            blob = bucket.blob(filepath)
            
            # Check if blob exists before trying to delete
            if blob.exists():
                blob.delete()
                print(f"[{i}/{len(files_to_delete)}] ✅ Deleted: {filepath}")
                deleted += 1
            else:
                print(f"[{i}/{len(files_to_delete)}] ⏭️  Skipped (doesn't exist): {filepath}")
        except Exception as e:
            print(f"[{i}/{len(files_to_delete)}] ❌ Error deleting {filepath}: {e}")
            errors += 1
    
    print(f"\n{'='*70}")
    print("Summary:")
    print(f"{'='*70}")
    print(f"✅ Deleted: {deleted}")
    print(f"❌ Errors:  {errors}")
    print(f"📊 Total:   {len(files_to_delete)}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Delete unindexed images from bravo_images folder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 delete_unindexed_images.py dev unindexed_images_bravo_dev_465400.txt
  python3 delete_unindexed_images.py prod unindexed_images_bravo_prod_465323.txt

⚠️  WARNING: This permanently deletes files from GCS!
        """
    )
    
    parser.add_argument('project', help='Project (dev/test/prod or full project ID)')
    parser.add_argument('file_list', help='Path to the file containing list of unindexed images')
    
    args = parser.parse_args()
    
    # Project mapping
    PROJECTS = {
        'dev': 'bravo-dev-465400',
        'test': 'bravo-test-465400',
        'prod': 'bravo-prod-465323'
    }
    
    project_id = PROJECTS.get(args.project, args.project)
    
    delete_unindexed_images(project_id, args.file_list)
