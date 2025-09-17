#!/usr/bin/env python3
"""
Upload a small test batch of PiCom images to verify everything works
"""

import os
from pathlib import Path
from google.cloud import storage
import json

def upload_test_batch():
    """Upload first 10 images as a test"""
    
    project_id = "bravo-test-465400"
    bucket_name = "bravo-picom-symbols"
    picom_dir = Path("/Users/blakethomas/Documents/BravoGCPCopilot/PiComImages")
    
    print(f"🧪 Testing PiCom Image Upload (10 images)")
    
    # Initialize storage client
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    
    # Get first 10 PNG files
    png_files = list(picom_dir.rglob("*.png"))[:10]
    print(f"📊 Testing with {len(png_files)} images")
    
    uploaded_urls = []
    
    for i, image_path in enumerate(png_files):
        try:
            # Calculate relative path for blob name
            relative_path = image_path.relative_to(picom_dir)
            blob_name = f"symbols/{relative_path}"
            
            # Upload to Cloud Storage
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(str(image_path), content_type='image/png')
            
            # Get public URL
            public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
            uploaded_urls.append({
                "filename": image_path.name,
                "url": public_url
            })
            
            print(f"✅ {i+1}/10: {image_path.name}")
                
        except Exception as e:
            print(f"❌ Failed: {image_path.name}: {e}")
    
    print(f"\n🎉 Test Complete! Uploaded {len(uploaded_urls)} images")
    print("\n📋 Sample URLs:")
    for item in uploaded_urls[:3]:
        print(f"   {item['filename']}: {item['url']}")
    
    print(f"\n🌐 Test one: {uploaded_urls[0]['url'] if uploaded_urls else 'No uploads'}")
    
    return len(uploaded_urls) > 0

if __name__ == "__main__":
    upload_test_batch()