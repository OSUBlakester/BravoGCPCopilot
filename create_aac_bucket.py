#!/usr/bin/env python3
"""
Script to create the AAC Images bucket if it doesn't exist
"""
import os
from google.cloud import storage

def create_aac_images_bucket():
    """Create AAC images bucket if it doesn't exist"""
    try:
        # Get project ID from environment or config
        project_id = os.environ.get('GCP_PROJECT_ID', 'bravo-dev-465400')
        bucket_name = f"{project_id}-aac-images"
        
        # Initialize storage client
        storage_client = storage.Client(project=project_id)
        
        # Check if bucket exists
        bucket = storage_client.bucket(bucket_name)
        
        if bucket.exists():
            print(f"✅ AAC images bucket already exists: {bucket_name}")
        else:
            # Create bucket
            bucket = storage_client.create_bucket(bucket_name, location="US-CENTRAL1")
            print(f"✅ Created AAC images bucket: {bucket_name}")
            
        # Set CORS policy for web access
        bucket.cors = [
            {
                "origin": ["*"],
                "method": ["GET", "HEAD"],
                "responseHeader": ["Content-Type"],
                "maxAgeSeconds": 3600
            }
        ]
        bucket.patch()
        print(f"✅ CORS policy set for bucket: {bucket_name}")
        
    except Exception as e:
        print(f"❌ Error creating AAC images bucket: {e}")
        raise

if __name__ == "__main__":
    create_aac_images_bucket()
