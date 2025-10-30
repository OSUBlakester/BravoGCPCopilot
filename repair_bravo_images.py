#!/usr/bin/env python3
"""
Repair script to fix truncated subconcepts and regenerate tags for BravoImages
without re-importing the images themselves.
"""
import asyncio
import os
import sys
import re
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
import google.generativeai as genai
from google.cloud import firestore, secretmanager
import json

class BravoImageRepairer:
    def __init__(self):
        self.project_id = CONFIG['gcp_project_id']
        self.setup_clients()
    
    def setup_clients(self):
        """Initialize GCP clients"""
        os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', CONFIG['service_account_key_path'])
        self.firestore_db = firestore.Client(project=self.project_id)
        self.secret_client = secretmanager.SecretManagerServiceClient()
        print("✅ Clients initialized")
    
    async def get_gemini_api_key(self) -> str:
        """Get Gemini API key from Secret Manager"""
        try:
            secret_name = f"projects/{self.project_id}/secrets/bravo-google-api-key/versions/latest"
            response = await asyncio.to_thread(
                self.secret_client.access_secret_version, 
                request={"name": secret_name}
            )
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"❌ Could not get Gemini API key: {e}")
            raise
    
    async def find_problematic_images(self):
        """Find ALL images with potentially truncated subconcepts"""
        print("🔍 Scanning for ALL potentially truncated images...")
        
        query = self.firestore_db.collection('aac_images').where('source', '==', 'bravo_images')
        docs = await asyncio.to_thread(query.get)
        
        problematic = []
        all_images_checked = 0
        
        for doc in docs:
            data = doc.to_dict()
            subconcept = data.get('subconcept', '')
            image_url = data.get('image_url', '')
            all_images_checked += 1
            
            # Try to reconstruct the original filename from the image_url for ALL images
            # URL format: https://storage.googleapis.com/bucket/bravo_images/concept_subconcept_timestamp.png
            try:
                filename = image_url.split('/')[-1]  # Get just the filename
                # Remove the concept prefix and timestamp suffix to get original subconcept
                parts = filename.replace('.png', '').split('_')
                
                # Find timestamp (8 digits) and time (6 digits)
                timestamp_idx = -1
                for i, part in enumerate(parts[1:], 1):  # Skip first part (concept)
                    if len(part) == 8 and part.isdigit():
                        timestamp_idx = i
                        break
                
                if timestamp_idx > 1:
                    # Reconstruct original subconcept
                    original_subconcept = '_'.join(parts[1:timestamp_idx])
                    
                    # Check if the current subconcept is different/truncated
                    if original_subconcept != subconcept:
                        # Additional check: only flag as problematic if the original is longer
                        # or contains underscores (multi-word)
                        if len(original_subconcept) > len(subconcept) or '_' in original_subconcept:
                            problematic.append({
                                'doc_id': doc.id,
                                'current_subconcept': subconcept,
                                'reconstructed_subconcept': original_subconcept,
                                'concept': data.get('concept', ''),
                                'image_url': image_url,
                                'current_tags': data.get('tags', [])
                            })
            
            except Exception as e:
                print(f"⚠️  Could not parse filename for {subconcept}: {e}")
        
        print(f"📊 Checked {all_images_checked} total images")
        print(f"🔧 Found {len(problematic)} images that need repair")
        
        # Show some examples of what we found
        if problematic:
            print(f"\n📝 Sample of problematic images:")
            for i, img in enumerate(problematic[:5]):  # Show first 5
                print(f"  {i+1}. '{img['current_subconcept']}' → '{img['reconstructed_subconcept']}'")
            if len(problematic) > 5:
                print(f"  ... and {len(problematic) - 5} more")
        
        return problematic
    
    async def generate_new_tags(self, image_url: str, concept: str, subconcept: str) -> list:
        """Generate new tags using Gemini"""
        try:
            api_key = await self.get_gemini_api_key()
            genai.configure(api_key=api_key)
            
            model = genai.GenerativeModel('gemini-2.0-flash-001')
            
            prompt = f"""
            Analyze this image that represents "{subconcept}" from the category "{concept}".
            
            Generate 6-10 specific, descriptive tags that help people find and understand this image.
            
            Requirements:
            - Focus on what this image shows and means
            - Include words people would search for (like "help", "assistance", "support" for help-related images)
            - Add visual descriptors and functional words
            - Use simple, common search terms
            - Return ONLY a JSON array of strings, no other text
            
            Example: ["help", "assistance", "support", "asking", "question", "aid", "guidance", "red", "person"]
            """
            
            response = await asyncio.to_thread(
                model.generate_content, 
                [prompt, {"image": {"data": image_url}}]
            )
            
            # Parse the JSON response
            tag_text = response.text.strip()
            if tag_text.startswith('```json'):
                tag_text = tag_text.replace('```json', '').replace('```', '').strip()
            
            tags = json.loads(tag_text)
            return tags if isinstance(tags, list) else []
            
        except Exception as e:
            print(f"❌ Error generating tags for {subconcept}: {e}")
            return []
    
    async def repair_image(self, image_info: dict, dry_run: bool = True):
        """Repair a single image entry"""
        doc_id = image_info['doc_id']
        old_subconcept = image_info['current_subconcept']
        new_subconcept = image_info['reconstructed_subconcept']
        
        print(f"🔧 Repairing: '{old_subconcept}' → '{new_subconcept}'")
        
        if not dry_run:
            # Generate new tags
            new_tags = await self.generate_new_tags(
                image_info['image_url'], 
                image_info['concept'], 
                new_subconcept
            )
            
            # Always include the subconcept itself in tags (split on underscores)
            subconcept_tags = new_subconcept.split('_')
            all_tags = list(set(new_tags + subconcept_tags))
            
            # Update the document
            doc_ref = self.firestore_db.collection('aac_images').document(doc_id)
            await asyncio.to_thread(doc_ref.update, {
                'subconcept': new_subconcept,
                'tags': all_tags
            })
            
            print(f"  ✅ Updated with tags: {all_tags}")
        else:
            print(f"  🧪 [DRY RUN] Would update with new subconcept and regenerated tags")
    
    async def repair_all(self, dry_run: bool = True):
        """Find and repair all problematic images"""
        problematic = await self.find_problematic_images()
        
        if not problematic:
            print("🎉 No problematic images found!")
            return
        
        print(f"\n📋 Images to repair:")
        for img in problematic:
            print(f"  • '{img['current_subconcept']}' → '{img['reconstructed_subconcept']}'")
        
        if dry_run:
            print(f"\n🧪 DRY RUN MODE - No changes will be made")
            print(f"Run with --fix to actually update the database")
        else:
            print(f"\n🚀 REPAIR MODE - Updating database...")
        
        for img in problematic:
            await self.repair_image(img, dry_run)
        
        print(f"\n✅ Repair {'simulation' if dry_run else 'process'} complete!")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Repair BravoImages with truncated subconcepts')
    parser.add_argument('--fix', action='store_true', help='Actually fix the images (default is dry run)')
    args = parser.parse_args()
    
    repairer = BravoImageRepairer()
    await repairer.repair_all(dry_run=not args.fix)

if __name__ == "__main__":
    asyncio.run(main())