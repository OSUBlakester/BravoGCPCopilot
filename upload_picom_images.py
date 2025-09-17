#!/usr/bin/env python3
"""
Upload PiCom Images to Google Cloud Storage
This script uploads all 3,458 PiCom images to GCS for web access
"""

import os
import sys
from pathlib import Path
from google.cloud import storage
import json
from datetime import datetime

def upload_picom_images():
    """Upload all PiCom images to Google Cloud Storage"""
    
    # Configuration
    project_id = "bravo-test-465400"  # Your dev project
    bucket_name = "bravo-picom-symbols"  # We'll create this bucket
    picom_dir = Path("/Users/blakethomas/Documents/BravoGCPCopilot/PiComImages")
    
    print(f"🚀 Starting PiCom Image Upload")
    print(f"📁 Source: {picom_dir}")
    print(f"☁️  Destination: gs://{bucket_name}")
    
    # Initialize storage client
    try:
        client = storage.Client(project=project_id)
        print(f"✅ Connected to GCP project: {project_id}")
    except Exception as e:
        print(f"❌ Failed to connect to GCP: {e}")
        print("💡 Make sure you're authenticated: gcloud auth application-default login")
        return False
    
    # Create bucket if it doesn't exist
    try:
        bucket = client.bucket(bucket_name)
        if not bucket.exists():
            bucket = client.create_bucket(bucket_name, location="US")
            print(f"✅ Created bucket: {bucket_name}")
        else:
            print(f"✅ Using existing bucket: {bucket_name}")
    except Exception as e:
        print(f"❌ Bucket error: {e}")
        return False
    
    # Find all PNG images
    if not picom_dir.exists():
        print(f"❌ PiCom directory not found: {picom_dir}")
        return False
    
    png_files = list(picom_dir.rglob("*.png"))
    print(f"📊 Found {len(png_files)} PNG images to upload")
    
    if len(png_files) == 0:
        print("❌ No PNG files found!")
        return False
    
    # Upload images
    uploaded_count = 0
    failed_count = 0
    upload_log = []
    
    for i, image_path in enumerate(png_files):
        try:
            # Calculate relative path for blob name
            relative_path = image_path.relative_to(picom_dir)
            blob_name = f"symbols/{relative_path}"
            
            # Upload to Cloud Storage
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(str(image_path), content_type='image/png')
            
            # Get public URL (no need to make individual blobs public with uniform access)
            public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
            
            upload_log.append({
                "filename": image_path.name,
                "local_path": str(image_path),
                "blob_name": blob_name,
                "public_url": public_url,
                "uploaded_at": datetime.now().isoformat()
            })
            
            uploaded_count += 1
            
            # Progress indicator
            if i % 100 == 0 or i == len(png_files) - 1:
                progress = (i + 1) / len(png_files) * 100
                print(f"📤 Progress: {i+1}/{len(png_files)} ({progress:.1f}%) - {image_path.name}")
                
        except Exception as e:
            print(f"❌ Failed to upload {image_path.name}: {e}")
            failed_count += 1
            continue
    
    # Save upload log
    log_file = "picom_upload_log.json"
    with open(log_file, 'w') as f:
        json.dump({
            "upload_summary": {
                "total_files": len(png_files),
                "uploaded": uploaded_count,
                "failed": failed_count,
                "bucket_name": bucket_name,
                "project_id": project_id,
                "upload_date": datetime.now().isoformat()
            },
            "uploaded_files": upload_log
        }, f, indent=2)
    
    print(f"\n🎉 Upload Complete!")
    print(f"✅ Uploaded: {uploaded_count} images")
    print(f"❌ Failed: {failed_count} images")
    print(f"📄 Log saved: {log_file}")
    print(f"🌐 Base URL: https://storage.googleapis.com/{bucket_name}/symbols/")
    
    # Update server configuration
    print(f"\n📝 Next steps:")
    print(f"1. Update your server.py to use bucket: {bucket_name}")
    print(f"2. Test symbol processing at: https://your-dev-url.com/symbol-admin")
    print(f"3. Images will be available at: https://storage.googleapis.com/{bucket_name}/symbols/filename.png")
    
    return uploaded_count > 0

def test_bucket_access():
    """Test if we can access the bucket"""
    project_id = "bravo-test-465400"
    bucket_name = "bravo-picom-symbols"
    
    try:
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
        
        if bucket.exists():
            blobs = list(bucket.list_blobs(max_results=5))
            print(f"✅ Bucket exists with {len(blobs)} sample blobs")
            for blob in blobs:
                print(f"   - {blob.name}")
            return True
        else:
            print(f"❌ Bucket {bucket_name} does not exist")
            return False
            
    except Exception as e:
        print(f"❌ Bucket access error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_bucket_access()
    else:
        success = upload_picom_images()
        if success:
            print("\n🎯 Ready to test symbol processing!")
        else:
            print("\n❌ Upload failed - check errors above")