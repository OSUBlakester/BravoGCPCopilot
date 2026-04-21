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
import random
from pathlib import Path
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional
import base64
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
    def __init__(self, use_ai_tags: bool = True):
        self.project_id = CONFIG['gcp_project_id']
        self.bucket_name = f"{self.project_id}-aac-images"
        self.setup_clients()
        self.batch_size = 10
        self.processed_count = 0
        self.error_count = 0
        self.skipped_count = 0
        self.use_ai_tags = use_ai_tags
        self.ai_tags_requested = use_ai_tags
        self.tag_retry_attempts = 2
        self.inter_image_delay_seconds = 2.0
        self.ai_tag_success_count = 0
        self.ai_tag_fallback_count = 0
        self.ai_tag_rate_limit_streak = 0
        self.disable_ai_after_rate_limit = True
        self.rate_limit_streak_threshold = 3
        self.gemini_model_name = 'gemini-2.0-flash-001'
        self.gemini_key_source = 'unknown'
        self.gemini_key_fingerprint: Optional[str] = None
        self.force_retag = False
        
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
        
        # Folders to always skip
        SKIP_FOLDERS = {'originals_backup', 'logs', '.DS_Store'}
        
        # First, check for PNG images directly in base_path (flat directory of images)
        direct_images = [f for f in base_path.glob("*.png") if 'originals_backup' not in str(f)]
        if direct_images:
            # Determine concept from parent folder name
            concept = base_path.parent.name  # e.g., "batch_missing_images"
            logger.info(f"📄 Found {len(direct_images)} images directly in {base_path.name}")
            for image_file in direct_images:
                subconcept = image_file.stem  # filename without extension
                images.append((str(image_file), concept, subconcept))
            logger.info(f"🎯 Found {len(images)} images to process")
            return images
        
        # Scan all batch folders
        for batch_folder in base_path.glob("batch_*_output"):
            if not batch_folder.is_dir():
                continue
                
            logger.info(f"📁 Processing batch folder: {batch_folder.name}")
            
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
                if not concept_folder.is_dir() or concept_folder.name in SKIP_FOLDERS or concept_folder.name in ['failed_concepts.json', 'generation_progress.json']:
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
        
        # Handle non-batch folders (like Bravo_Bear_001)
        for folder in base_path.iterdir():
            if not folder.is_dir() or folder.name.startswith('batch_') or folder.name.startswith('.') or folder.name in SKIP_FOLDERS:
                continue
                
            logger.info(f"📁 Processing non-batch folder: {folder.name}")
            
            # Look for Categories subfolder (Bravo_Bear_001 structure)
            categories_folder = folder / 'Categories'
            if categories_folder.exists() and categories_folder.is_dir():
                logger.info(f"  📄 Found Categories folder in {folder.name}")
                for image_file in categories_folder.glob("*.png"):
                    # Skip images inside originals_backup
                    if 'originals_backup' in str(image_file):
                        continue
                    concept = folder.name
                    subconcept = image_file.stem  # Use filename without extension as subconcept
                    images.append((str(image_file), concept, subconcept))
                    
            # Also check for images directly in the folder
            else:
                direct_images = list(folder.glob("*.png"))
                if direct_images:
                    logger.info(f"  📄 Found {len(direct_images)} images directly in {folder.name}")
                    for image_file in direct_images:
                        concept = folder.name
                        subconcept = image_file.stem
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
    
    @staticmethod
    def _fingerprint_key(api_key: str) -> str:
        import hashlib
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:12]

    async def get_gemini_api_key(self) -> str:
        """Get Gemini API key from Secret Manager or environment, with source diagnostics."""
        secret_key = None
        try:
            secret_name = f"projects/{self.project_id}/secrets/bravo-google-api-key/versions/latest"
            response = await asyncio.to_thread(
                self.secret_client.access_secret_version,
                request={"name": secret_name}
            )
            secret_key = response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"Could not access Secret Manager for Gemini API key: {e}")

        google_api_key = os.environ.get('GOOGLE_API_KEY')
        gemini_api_key = os.environ.get('GEMINI_API_KEY')

        selected_key = None
        selected_source = None

        if secret_key:
            selected_key = secret_key
            selected_source = 'secret:bravo-google-api-key'
        elif google_api_key:
            selected_key = google_api_key
            selected_source = 'env:GOOGLE_API_KEY'
        elif gemini_api_key:
            selected_key = gemini_api_key
            selected_source = 'env:GEMINI_API_KEY'

        if not selected_key:
            raise Exception("Gemini API key not configured")

        # Helpful warning if secret and env values diverge.
        if secret_key and google_api_key and secret_key != google_api_key:
            logger.warning(
                "⚠️ Secret key and GOOGLE_API_KEY differ. "
                "Importer will use the Secret Manager key."
            )

        self.gemini_key_source = selected_source
        self.gemini_key_fingerprint = self._fingerprint_key(selected_key)

        logger.info(
            f"🔐 Gemini key source: {self.gemini_key_source}; "
            f"fingerprint: {self.gemini_key_fingerprint}"
        )

        return selected_key
    
    def _basic_fallback_tags(self, concept: str, subconcept: str) -> List[str]:
        """Generate deterministic fallback tags from concept/subconcept tokens."""
        searchable_subconcept = subconcept.replace('_', ' ').strip()
        searchable_concept = concept.replace('_', ' ').strip()

        fallback_tags: List[str] = []
        for candidate in [searchable_subconcept, searchable_concept]:
            if candidate and candidate.lower() not in [t.lower() for t in fallback_tags]:
                fallback_tags.append(candidate)

        token_source = searchable_subconcept.replace('-', ' ')
        for token in token_source.split():
            cleaned = token.strip().lower()
            if len(cleaned) < 3:
                continue
            if cleaned in {'and', 'the', 'for', 'with', 'from'}:
                continue
            if cleaned not in [t.lower() for t in fallback_tags]:
                fallback_tags.append(cleaned)

        return fallback_tags[:15]

    async def generate_image_tags(self, image_path: str, concept: str, subconcept: str) -> List[str]:
        """Use Gemini to analyze image and generate relevant tags"""
        fallback_tags = self._basic_fallback_tags(concept, subconcept)

        try:
            api_key = await self.get_gemini_api_key()
            genai.configure(api_key=api_key)
            
            model = genai.GenerativeModel(self.gemini_model_name)
            
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

            with open(image_path, 'rb') as f:
                image_bytes = f.read()

            image_data = base64.b64encode(image_bytes).decode()

            last_error = None
            for attempt in range(1, self.tag_retry_attempts + 1):
                try:
                    response = await asyncio.to_thread(
                        model.generate_content,
                        [prompt, {"mime_type": "image/png", "data": image_data}]
                    )

                    tags_text = (response.text or '').strip()
                    ai_tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]

                    searchable_subconcept = subconcept.replace('_', ' ')
                    searchable_concept = concept.replace('_', ' ')
                    final_tags = [searchable_subconcept, searchable_concept]

                    for tag in ai_tags:
                        if tag not in final_tags and tag.lower() not in [searchable_subconcept.lower(), searchable_concept.lower()]:
                            final_tags.append(tag)

                    self.ai_tag_rate_limit_streak = 0
                    self.ai_tag_success_count += 1
                    return final_tags[:15]
                except Exception as retry_err:
                    last_error = retry_err
                    err_text = str(retry_err)
                    is_retryable = (
                        '429' in err_text
                        or 'Resource exhausted' in err_text
                        or 'quota' in err_text.lower()
                    )
                    if attempt < self.tag_retry_attempts and is_retryable:
                        backoff_seconds = min(45.0, (2 ** attempt) + random.uniform(0.25, 1.5))
                        logger.warning(
                            f"⚠️ Gemini tagging rate-limited for {concept}/{subconcept} "
                            f"(attempt {attempt}/{self.tag_retry_attempts}). Retrying in {backoff_seconds:.1f}s"
                        )
                        await asyncio.sleep(backoff_seconds)
                        continue
                    raise last_error
                
        except Exception as e:
            err_text = str(e)
            is_rate_limit = (
                '429' in err_text
                or 'Resource exhausted' in err_text
                or 'quota' in err_text.lower()
            )
            if is_rate_limit:
                self.ai_tag_rate_limit_streak += 1
                logger.warning(
                    f"⚠️ AI tag generation rate-limited for {concept}/{subconcept}; "
                    f"using fallback tags (streak {self.ai_tag_rate_limit_streak})."
                )
                if self.disable_ai_after_rate_limit and self.ai_tag_rate_limit_streak >= self.rate_limit_streak_threshold:
                    self.use_ai_tags = False
                    logger.warning(
                        "🚦 Disabling AI tagging for the remainder of this import due to repeated rate limits. "
                        "Uploads will continue with fallback tags."
                    )
            else:
                logger.warning(f"⚠️ Error generating image tags: {e}")
            self.ai_tag_fallback_count += 1
            return fallback_tags
    
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

    async def update_image_in_firestore(self, doc_ref, image_url: str, concept: str, subconcept: str, tags: List[str], created_at=None) -> str:
        """Update an existing Firestore document in-place, preserving its document ID."""
        try:
            now = datetime.now(timezone.utc)
            doc_data = {
                "concept": concept,
                "subconcept": subconcept,
                "tags": tags,
                "image_url": image_url,
                "image_type": "global",
                "user_id": None,
                "created_at": created_at if created_at is not None else now,
                "updated_at": now,
                "created_by": "bulk_import_bravo",
                "approved": True,
                "source": "bravo_images"
            }
            await asyncio.to_thread(doc_ref.set, doc_data)
            return doc_ref.id
        except Exception as e:
            logger.error(f"❌ Error updating image in Firestore: {e}")
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

                preserved_tags: Optional[List[str]] = None
                existing_doc_ref = None  # reference to update in-place if replacing

                if existing and not getattr(self, 'replace_existing', False):
                    logger.info(f"⏭️ Skipping {concept}/{subconcept} - already exists")
                    results["skipped"] += 1
                    continue
                elif existing and getattr(self, 'replace_existing', False):
                    existing_doc_ref = existing[0].reference
                    existing_doc_data_raw = existing[0].to_dict() or {}
                    existing_created_at = existing_doc_data_raw.get('created_at')
                    if not self.force_retag:
                        try:
                            existing_doc_data = existing_doc_data_raw
                            existing_tags = existing_doc_data.get('tags') if isinstance(existing_doc_data, dict) else None
                            if isinstance(existing_tags, list) and existing_tags:
                                preserved_tags = [str(t).strip() for t in existing_tags if str(t).strip()]
                                logger.info(
                                    f"♻️ Reusing {len(preserved_tags)} existing tags for {concept}/{subconcept} "
                                    f"(use --force-retag to regenerate)"
                                )
                        except Exception as preserve_err:
                            logger.warning(f"⚠️ Could not preserve existing tags for {concept}/{subconcept}: {preserve_err}")

                    # Delete any duplicate entries beyond the first
                    for extra_doc in existing[1:]:
                        logger.info(f"🗑️ Removing duplicate {concept}/{subconcept} (doc: {extra_doc.id})")
                        await asyncio.to_thread(extra_doc.reference.delete)

                # Upload image to storage
                logger.info(f"📤 Uploading {concept}/{subconcept}")
                image_url = await self.upload_image_to_storage(image_path, concept, subconcept)

                if preserved_tags:
                    tags = preserved_tags[:15]
                elif self.use_ai_tags:
                    logger.info(f"🏷️ Generating tags for {concept}/{subconcept}")
                    tags = await self.generate_image_tags(image_path, concept, subconcept)
                else:
                    logger.info(f"🏷️ AI tagging disabled for {concept}/{subconcept}; using fallback tags")
                    tags = self._basic_fallback_tags(concept, subconcept)

                # Store in Firestore — update existing doc in-place (preserves doc ID) or create new
                logger.info(f"💾 Storing {concept}/{subconcept} in database")
                if existing_doc_ref is not None:
                    logger.info(f"🔄 Updating existing {concept}/{subconcept} (doc: {existing_doc_ref.id})")
                    doc_id = await self.update_image_in_firestore(existing_doc_ref, image_url, concept, subconcept, tags, created_at=existing_created_at)
                else:
                    doc_id = await self.store_image_in_firestore(image_url, concept, subconcept, tags)
                
                logger.info(f"✅ Successfully processed {concept}/{subconcept} -> {doc_id}")
                logger.info(f"🏷️ Tags: {', '.join(tags)}")
                
                results["processed"] += 1
                
                # Longer delay to avoid rate limits (especially for AI tagging)
                await asyncio.sleep(self.inter_image_delay_seconds)
                
            except Exception as e:
                logger.error(f"❌ Error processing {image_path}: {e}")
                results["errors"] += 1
                continue
        
        return results
    
    async def run_import(
        self,
        base_path: str,
        test_mode: bool = False,
        batch_size: int = 10,
        replace: bool = False,
        inter_image_delay: float = 2.0,
        tag_retry_attempts: int = 2,
        disable_ai_after_rate_limit: bool = True,
        rate_limit_streak_threshold: int = 3,
        gemini_model: str = 'gemini-2.0-flash-001',
        force_retag: bool = False,
    ) -> Dict[str, int]:
        """Run the bulk import process"""
        self.batch_size = batch_size
        self.replace_existing = replace
        self.inter_image_delay_seconds = max(0.0, inter_image_delay)
        self.tag_retry_attempts = max(1, int(tag_retry_attempts))
        self.disable_ai_after_rate_limit = bool(disable_ai_after_rate_limit)
        self.rate_limit_streak_threshold = max(1, int(rate_limit_streak_threshold))
        self.gemini_model_name = (gemini_model or 'gemini-2.0-flash-001').strip()
        self.force_retag = bool(force_retag)
        
        logger.info("🚀 Starting BravoImages bulk import")
        logger.info(f"📁 Source path: {base_path}")
        logger.info(f"📦 Batch size: {batch_size}")
        logger.info(f"🧪 Test mode: {test_mode}")
        logger.info(f"🔄 Replace existing: {replace}")
        logger.info(f"⏱️ Inter-image delay: {self.inter_image_delay_seconds:.1f}s")
        logger.info(f"🔁 Tag retry attempts: {self.tag_retry_attempts}")
        logger.info(f"🚦 Disable AI after rate limits: {self.disable_ai_after_rate_limit}")
        logger.info(f"📉 Rate-limit streak threshold: {self.rate_limit_streak_threshold}")
        logger.info(f"🤖 Gemini model for tagging: {self.gemini_model_name}")
        logger.info(f"♻️ Force retag on replace: {self.force_retag}")

        if self.use_ai_tags:
            # Prime key resolution once so logs clearly show source/fingerprint before processing.
            await self.get_gemini_api_key()
        
        # Find all images
        all_images = self.find_all_images(base_path)
        
        if not all_images:
            logger.error("❌ No images found to process")
            return {"processed": 0, "errors": 0, "skipped": 0}
        
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
        if self.ai_tags_requested:
            logger.info(f"   🏷️ AI tags success: {self.ai_tag_success_count}")
            logger.info(f"   🛟 AI tag fallbacks: {self.ai_tag_fallback_count}")
            logger.info(f"   🚦 AI tagging still enabled at end: {self.use_ai_tags}")
            if self.gemini_key_source and self.gemini_key_fingerprint:
                logger.info(
                    f"   🔐 Gemini key used: {self.gemini_key_source} "
                    f"(fp={self.gemini_key_fingerprint})"
                )

        return total_results

async def main():
    parser = argparse.ArgumentParser(description='Bulk import BravoImages to Firestore')
    parser.add_argument('--test', action='store_true', 
                       help='Test mode: process only 5 images')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of images to process in each batch (default: 10)')
    parser.add_argument('--path', type=str, 
                       default=str(Path(__file__).resolve().parent / 'BravoImages'),
                       help='Path to BravoImages folder')
    parser.add_argument('--replace', action='store_true',
                       help='Replace existing images instead of skipping')
    parser.add_argument('--no-ai-tags', action='store_true',
                       help='Disable Gemini tagging and use fallback tags only')
    parser.add_argument('--inter-image-delay', type=float, default=2.0,
                       help='Seconds to wait between images to reduce API rate limits (default: 2.0)')
    parser.add_argument('--tag-retries', type=int, default=2,
                       help='How many attempts to make for AI tag generation per image (default: 2)')
    parser.add_argument('--disable-ai-after-rate-limit', action='store_true', default=True,
                       help='Disable AI tagging for the rest of the run after repeated 429s (default: enabled)')
    parser.add_argument('--keep-ai-after-rate-limit', action='store_true',
                       help='Do not disable AI tagging after repeated 429s')
    parser.add_argument('--rate-limit-streak-threshold', type=int, default=3,
                       help='Consecutive 429 fallback count before AI tagging is disabled (default: 3)')
    parser.add_argument('--gemini-model', type=str, default='gemini-2.0-flash-001',
                       help='Gemini model used for image tagging (default: gemini-2.0-flash-001)')
    parser.add_argument('--force-retag', action='store_true',
                       help='When replacing existing documents, regenerate tags instead of reusing existing tags')
    
    args = parser.parse_args()
    
    try:
        importer = BravoImageImporter(use_ai_tags=not args.no_ai_tags)
        results = await importer.run_import(
            args.path,
            args.test,
            args.batch_size,
            args.replace,
            args.inter_image_delay,
            args.tag_retries,
            (False if args.keep_ai_after_rate_limit else args.disable_ai_after_rate_limit),
            args.rate_limit_streak_threshold,
            args.gemini_model,
            args.force_retag,
        )

        if results.get('errors', 0) > 0:
            raise SystemExit(1)
        
    except KeyboardInterrupt:
        logger.info("🛑 Import interrupted by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())