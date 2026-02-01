#!/usr/bin/env python3
"""
Identify images in the bucket that are NOT indexed in Firestore
"""

from google.cloud import firestore, storage

def find_unindexed_images(project_id):
    """Find images in bucket that aren't in Firestore"""
    
    print(f"\n{'='*70}")
    print(f"Analyzing project: {project_id}")
    print(f"{'='*70}\n")
    
    # Initialize clients
    db = firestore.Client(project=project_id)
    storage_client = storage.Client(project=project_id)
    
    bucket_name = f"{project_id}-aac-images"
    bucket = storage_client.bucket(bucket_name)
    
    # Get all files from bravo_images/ folder
    print("Loading files from bucket...")
    bucket_files = set()
    for blob in bucket.list_blobs(prefix='bravo_images/'):
        # Store just the filename without the prefix
        filename = blob.name.replace('bravo_images/', '')
        if filename:  # Skip if it's just the folder itself
            bucket_files.add(blob.name)
    
    print(f"  Found {len(bucket_files)} files in gs://{bucket_name}/bravo_images/\n")
    
    # Get all indexed images from Firestore
    print("Loading indexed images from Firestore...")
    firestore_files = set()
    
    for doc in db.collection('aac_images').stream():
        data = doc.to_dict()
        # The image_url field contains the full GCS URL
        image_url = data.get('image_url', '')
        if 'bravo_images/' in image_url:
            # Extract the path: bravo_images/filename.png
            # URL format: https://storage.googleapis.com/{bucket}/bravo_images/filename.png
            path = image_url.split('bravo_images/')[-1].split('?')[0]  # Remove query params
            firestore_files.add(f"bravo_images/{path}")
    
    print(f"  Found {len(firestore_files)} images indexed in Firestore\n")
    
    # Find unindexed files
    unindexed = bucket_files - firestore_files
    
    print(f"\n{'='*70}")
    print(f"Results:")
    print(f"{'='*70}\n")
    print(f"Total bucket files:     {len(bucket_files)}")
    print(f"Indexed in Firestore:   {len(firestore_files)}")
    print(f"NOT indexed:            {len(unindexed)}")
    
    if unindexed:
        print(f"\n{'='*70}")
        print("Sample of unindexed files (first 20):")
        print(f"{'='*70}\n")
        
        for i, filepath in enumerate(sorted(unindexed)[:20], 1):
            print(f"{i:3}. {filepath}")
        
        if len(unindexed) > 20:
            print(f"\n... and {len(unindexed) - 20} more unindexed files")
        
        # Save full list to file
        output_file = f'unindexed_images_{project_id.replace("-", "_")}.txt'
        with open(output_file, 'w') as f:
            f.write(f"Unindexed images in {project_id}\n")
            f.write(f"{'='*70}\n\n")
            f.write(f"Total: {len(unindexed)} files\n\n")
            for filepath in sorted(unindexed):
                f.write(f"{filepath}\n")
        
        print(f"\n✅ Full list saved to: {output_file}")
    
    return unindexed

# Analyze dev environment
unindexed_dev = find_unindexed_images('bravo-dev-465400')

# Analyze prod environment
unindexed_prod = find_unindexed_images('bravo-prod-465323')

print(f"\n{'='*70}\n")
