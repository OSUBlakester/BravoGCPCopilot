#!/usr/bin/env python3
"""
Check the contents of aac-images buckets to see what's in each folder
"""

from google.cloud import storage
from collections import defaultdict

def analyze_bucket(project_id, bucket_name):
    """Analyze the contents of a bucket by folder/prefix"""
    
    print(f"\n{'='*70}")
    print(f"Analyzing: gs://{bucket_name} (project: {project_id})")
    print(f"{'='*70}\n")
    
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    
    if not bucket.exists():
        print(f"❌ Bucket does not exist!")
        return
    
    # Count files by folder prefix
    folder_counts = defaultdict(int)
    
    print("Listing all files...")
    all_blobs = list(bucket.list_blobs())
    
    for blob in all_blobs:
        # Get the top-level folder (prefix before first /)
        if '/' in blob.name:
            folder = blob.name.split('/')[0] + '/'
        else:
            folder = '(root)'
        folder_counts[folder] += 1
    
    print(f"\nTotal files in bucket: {len(all_blobs)}")
    print(f"\nBreakdown by folder:\n")
    
    for folder in sorted(folder_counts.keys()):
        count = folder_counts[folder]
        print(f"  {folder:<30} {count:>6} files")
    
    # Show some sample files from bravo_images/
    print(f"\n{'='*70}")
    print("Sample files from bravo_images/ folder:")
    print(f"{'='*70}\n")
    
    bravo_blobs = list(bucket.list_blobs(prefix='bravo_images/', max_results=10))
    for blob in bravo_blobs:
        print(f"  {blob.name}")
    
    if len(bravo_blobs) == 10:
        print(f"  ... (showing first 10 of {folder_counts.get('bravo_images/', 0)} files)")

# Check dev
analyze_bucket('bravo-dev-465400', 'bravo-dev-465400-aac-images')

# Check prod
analyze_bucket('bravo-prod-465323', 'bravo-prod-465323-aac-images')

print(f"\n{'='*70}\n")
