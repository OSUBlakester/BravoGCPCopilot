#!/usr/bin/env python3
"""
Bulk import script for BravoImages to Firestore database with AI-generated tags.

This script will:
1. Scan all BravoImages batch folders
2. Upload images to Google Cloud Storage
3. Use Gemini to analyze and generate tags for each image
4. Store metadata in Firestore for querying via symbol_admin page

Usage: python bulk_import_bravo_images.py [--test] [--batch-size 10]
"""

import os
import asyncio
import logging
from pathlib import Path
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Tuple
import base64
import requests
from tqdm import tqdm

# Import configuration and dependencies from server.py
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
import google.generativeai as genai
from google.cloud import firestore, storage, secretmanager
import firebase_admin
from firebase_admin import credentials, firestore as admin_firestore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BravoImageImporter:
    def __init__(self):
        self.project_id = CONFIG['gcp_project_id']
        self.bucket_name = f"{self.project_id}-aac-images"
        self.setup_clients()
        self.batch_size = 10
        self.processed_count = 0
        self.error_count = 0
        self.skipped_count = 0
        
    def setup_clients(self):
        """Initialize Firebase, Firestore, and Storage clients"""
        try:
            # Initialize Firebase Admin if not already initialized
            if not firebase_admin._apps:
                # Use service account from config
                service_account_path = CONFIG.get('service_account_key_path')
                if service_account_path and os.path.exists(service_account_path):
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                else:
                    # Use default credentials
                    firebase_admin.initialize_app()
            
            # Initialize Firestore
            self.firestore_db = firestore.Client(project=self.project_id)
            
            # Initialize Cloud Storage
            self.storage_client = storage.Client(project=self.project_id)
            self.bucket = self.storage_client.bucket(self.bucket_name)
            
            # Initialize Secret Manager client
            self.secret_client = secretmanager.SecretManagerServiceClient()
            
            # Note: Bucket should already be configured for public access
            
            logger.info("✅ Successfully initialized Firebase, Firestore, and Storage clients")
            logger.info(f"📦 Using bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"❌ Error initializing clients: {e}")
            raise
    

    
    def find_all_images(self, base_path: str) -> List[Tuple[str, str, str]]:
        """
        Scan BravoImages folder and return list of (image_path, concept, subconcept)
        """
        images = []
        base_path = Path(base_path)
        
        if not base_path.exists():
            logger.error(f"❌ BravoImages folder not found: {base_path}")
            return images
        
        logger.info(f"🔍 Scanning {base_path} for images...")
        
        # Scan all batch folders
        for batch_folder in base_path.glob("batch_*_output"):
            if not batch_folder.is_dir():
                continue
                
            logger.info(f"📁 Processing {batch_folder.name}")
            
            # First, check for images directly in batch folder (like Alaska)
            direct_images = list(batch_folder.glob("*.png"))
            if direct_images:
                logger.info(f"  📄 Found {len(direct_images)} images directly in {batch_folder.name}")
                for image_file in direct_images:
                    # Extract subconcept from filename - handle multi-word concepts
                    # e.g., "can_you_help_20250929_174221.png" -> "can_you_help"
                    stem_parts = image_file.stem.split('_')
                    # Find where timestamp starts (8 digits)
                    timestamp_idx = -1
                    for i, part in enumerate(stem_parts):
                        if len(part) == 8 and part.isdigit():
                            timestamp_idx = i
                            break
                    
                    if timestamp_idx > 0:
                        subconcept = '_'.join(stem_parts[:timestamp_idx])
                    else:
                        # Fallback to original logic if no timestamp found
                        subconcept = stem_parts[0]
                    
                    concept = f"batch_{batch_folder.name.split('_')[1]}"  # e.g., "batch_009" 
                    images.append((str(image_file), concept, subconcept))
            
            # Then scan concept folders within each batch (original logic)
            for concept_folder in batch_folder.iterdir():
                if not concept_folder.is_dir() or concept_folder.name in ['logs', 'failed_concepts.json', 'generation_progress.json']:
                    continue
                
                concept = concept_folder.name
                
                # Find all PNG images in concept folder
                for image_file in concept_folder.glob("*.png"):
                    # Extract subconcept from filename - handle multi-word concepts
                    # e.g., "ask_for_help_20250927_172732.png" -> "ask_for_help"
                    stem_parts = image_file.stem.split('_')
                    # Find where timestamp starts (8 digits)
                    timestamp_idx = -1
                    for i, part in enumerate(stem_parts):
                        if len(part) == 8 and part.isdigit():
                            timestamp_idx = i
                            break
                    
                    if timestamp_idx > 0:
                        subconcept = '_'.join(stem_parts[:timestamp_idx])
                    else:
                        # Fallback to original logic if no timestamp found
                        subconcept = stem_parts[0]
                    
                    images.append((str(image_file), concept, subconcept))
        
        logger.info(f"🎯 Found {len(images)} images to process")
        return images
    
    async def upload_image_to_storage(self, image_path: str, concept: str, subconcept: str) -> str:
        """Upload image to Google Cloud Storage and return public URL"""
        try:
            # Create unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bravo_images/{concept}_{subconcept}_{timestamp}.png"
            
            # Read image file
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # Upload to storage
            blob = self.bucket.blob(filename)
            await asyncio.to_thread(blob.upload_from_string, image_bytes, content_type='image/png')
            
            # For uniform bucket-level access, don't try to make_public on individual blobs
            # The bucket should already be configured for public access
            # Return the public URL directly
            return f"https://storage.googleapis.com/{self.bucket_name}/{filename}"
            
        except Exception as e:
            logger.error(f"❌ Error uploading {image_path}: {e}")
            raise
    
    async def get_gemini_api_key(self) -> str:
        """Get Gemini API key from Secret Manager or environment"""
        try:
            secret_name = f"projects/{self.project_id}/secrets/bravo-google-api-key/versions/latest"
            response = await asyncio.to_thread(
                self.secret_client.access_secret_version, 
                request={"name": secret_name}
            )
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"Could not access Secret Manager for Gemini API key: {e}")
            # Fallback to environment variable
            api_key = os.environ.get('GEMINI_API_KEY')
            if api_key:
                return api_key
            else:
                raise Exception("Gemini API key not configured")
    
    async def generate_image_tags(self, image_url: str, concept: str, subconcept: str) -> List[str]:
        """Use Gemini to analyze image and generate relevant tags"""
        try:
            api_key = await self.get_gemini_api_key()
            genai.configure(api_key=api_key)
            
            model = genai.GenerativeModel('gemini-2.0-flash-001')
            
            prompt = f"""
            Analyze this image that represents "{subconcept}" from the category "{concept}".
            
            Generate 6-10 specific, descriptive tags that help people find and understand this image.
            
            Requirements:
            - Do NOT include "{concept}" or "{subconcept}" in your response (we'll add those separately)
            - Add visual descriptors (colors, shapes, features)
            - Include functional words (what it does, how it's used)
            - Add context words (where you'd find it, when you'd use it)
            - Use simple, common words people would actually search for
            - Avoid generic terms like "aac", "communication", "bravo_images"
            - Focus on what makes this image unique and searchable
            
            Return only the descriptive tags, separated by commas, no other text.
            
            Example format: brown, furry, sitting, friendly, companion, pet, animal
            """
            
            # Download image for analysis
            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                # Convert to base64 for Gemini
                image_data = base64.b64encode(response.content).decode()
                
                response = await asyncio.to_thread(
                    model.generate_content,
                    [prompt, {"mime_type": "image/png", "data": image_data}]
                )
                
                tags_text = response.text.strip()
                ai_tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
                
                # Build final tag list with subconcept-first priority
                # Convert underscores to spaces for better searchability
                searchable_subconcept = subconcept.replace('_', ' ')
                searchable_concept = concept.replace('_', ' ')
                final_tags = [searchable_subconcept, searchable_concept]  # Subconcept first, concept second
                
                # Add AI-generated descriptive tags (avoid duplicates)
                for tag in ai_tags:
                    if tag not in final_tags and tag.lower() not in [searchable_subconcept.lower(), searchable_concept.lower()]:
                        final_tags.append(tag)
                
                return final_tags[:15]  # Limit to 15 tags max
            else:
                logger.warning(f"⚠️ Failed to download image for analysis: {image_url}")
                return [subconcept.replace('_', ' '), concept.replace('_', ' ')]  # Subconcept first for better matching
                
        except Exception as e:
            logger.warning(f"⚠️ Error generating image tags: {e}")
            # Return only meaningful tags as fallback, subconcept first (with spaces)
            return [subconcept.replace('_', ' '), concept.replace('_', ' ')]
    
    async def store_image_in_firestore(self, image_url: str, concept: str, subconcept: str, tags: List[str]) -> str:
        """Store image metadata in Firestore"""
        try:
            doc_data = {
                "concept": concept,
                "subconcept": subconcept,
                "tags": tags,
                "image_url": image_url,
                "image_type": "global",
                "user_id": None,
                "created_at": datetime.now(timezone.utc),
                "created_by": "bulk_import_bravo",
                "approved": True,
                "source": "bravo_images"
            }
            
            # Store in Firestore
            doc_ref = await asyncio.to_thread(
                self.firestore_db.collection("aac_images").add,
                doc_data
            )
            doc_id = doc_ref[1].id
            
            return doc_id
            
        except Exception as e:
            logger.error(f"❌ Error storing image in Firestore: {e}")
            raise
    
    async def process_image_batch(self, images_batch: List[Tuple[str, str, str]]) -> Dict:
        """Process a batch of images"""
        results = {
            "processed": 0,
            "errors": 0,
            "skipped": 0
        }
        
        for image_path, concept, subconcept in images_batch:
            try:
                # Check if image already exists in database
                existing = await asyncio.to_thread(
                    self.firestore_db.collection("aac_images")
                    .where("concept", "==", concept)
                    .where("subconcept", "==", subconcept)
                    .where("source", "==", "bravo_images")
                    .limit(1)
                    .get
                )
                
                if existing:
                    logger.info(f"⏭️ Skipping {concept}/{subconcept} - already exists")
                    results["skipped"] += 1
                    continue
                
                # Upload image to storage
                logger.info(f"📤 Uploading {concept}/{subconcept}")
                image_url = await self.upload_image_to_storage(image_path, concept, subconcept)
                
                # Generate tags using AI
                logger.info(f"🏷️ Generating tags for {concept}/{subconcept}")
                tags = await self.generate_image_tags(image_url, concept, subconcept)
                
                # Store in Firestore
                logger.info(f"💾 Storing {concept}/{subconcept} in database")
                doc_id = await self.store_image_in_firestore(image_url, concept, subconcept, tags)
                
                logger.info(f"✅ Successfully processed {concept}/{subconcept} -> {doc_id}")
                logger.info(f"🏷️ Tags: {', '.join(tags)}")
                
                results["processed"] += 1
                
                # Longer delay to avoid rate limits (especially for AI tagging)
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error processing {image_path}: {e}")
                results["errors"] += 1
                continue
        
        return results
    
    async def run_import(self, base_path: str, test_mode: bool = False, batch_size: int = 10):
        """Run the bulk import process"""
        self.batch_size = batch_size
        
        logger.info("🚀 Starting BravoImages bulk import")
        logger.info(f"📁 Source path: {base_path}")
        logger.info(f"📦 Batch size: {batch_size}")
        logger.info(f"🧪 Test mode: {test_mode}")
        
        # Find all images
        all_images = self.find_all_images(base_path)
        
        if not all_images:
            logger.error("❌ No images found to process")
            return
        
        # In test mode, only process first 5 images
        if test_mode:
            all_images = all_images[:5]
            logger.info(f"🧪 Test mode: Processing only {len(all_images)} images")
        
        # Process in batches
        total_batches = (len(all_images) + batch_size - 1) // batch_size
        logger.info(f"📊 Processing {len(all_images)} images in {total_batches} batches")
        
        total_results = {"processed": 0, "errors": 0, "skipped": 0}
        
        for i in range(0, len(all_images), batch_size):
            batch_num = (i // batch_size) + 1
            batch = all_images[i:i + batch_size]
            
            logger.info(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} images)")
            
            try:
                batch_results = await self.process_image_batch(batch)
                
                # Update totals
                for key in total_results:
                    total_results[key] += batch_results[key]
                
                logger.info(f"📈 Batch {batch_num} complete: {batch_results}")
                
            except Exception as e:
                logger.error(f"❌ Error processing batch {batch_num}: {e}")
                total_results["errors"] += len(batch)
        
        # Final summary
        logger.info("🎉 Bulk import complete!")
        logger.info(f"📊 Final Results:")
        logger.info(f"   ✅ Processed: {total_results['processed']}")
        logger.info(f"   ⏭️ Skipped: {total_results['skipped']}")
        logger.info(f"   ❌ Errors: {total_results['errors']}")
        logger.info(f"   📁 Total: {len(all_images)}")

async def main():
    parser = argparse.ArgumentParser(description='Bulk import BravoImages to Firestore')
    parser.add_argument('--test', action='store_true', 
                       help='Test mode: process only 5 images')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of images to process in each batch (default: 10)')
    parser.add_argument('--path', type=str, 
                       default='/Users/blakethomas/Documents/BravoGCPCopilot/BravoImages',
                       help='Path to BravoImages folder')
    
    args = parser.parse_args()
    
    try:
        importer = BravoImageImporter()
        await importer.run_import(args.path, args.test, args.batch_size)
        
    except KeyboardInterrupt:
        logger.info("🛑 Import interrupted by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())