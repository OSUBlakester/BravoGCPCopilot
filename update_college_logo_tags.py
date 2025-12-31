#!/usr/bin/env python3
"""
Update tags for college logo images in Firestore.

This script will:
1. Find all images from the College_Logos folder
2. Parse the filename to extract school name and mascot name
3. Update tags:
   - Tag 0: Remove hyphens (e.g., "Air Force Falcons")
   - Tag 1: School name only (e.g., "Air Force")
   - Tag 2: Mascot name only (e.g., "Falcons")
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('update_college_tags.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CollegeLogoTagUpdater:
    def __init__(self):
        self.project_id = CONFIG['gcp_project_id']
        self.setup_firestore()
        self.updated_count = 0
        self.error_count = 0
        
    def setup_firestore(self):
        """Initialize Firestore client"""
        try:
            # Initialize Firebase Admin if not already initialized
            if not firebase_admin._apps:
                service_account_path = CONFIG.get('service_account_key_path')
                if service_account_path and os.path.exists(service_account_path):
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()
            
            self.firestore_db = firestore.Client(project=self.project_id)
            logger.info("✅ Successfully initialized Firestore client")
            
        except Exception as e:
            logger.error(f"❌ Error initializing Firestore: {e}")
            raise
    
    def parse_college_name(self, filename: str) -> Tuple[str, str, str]:
        """
        Parse college logo filename to extract school and mascot names.
        
        Args:
            filename: e.g., "Air-Force-Falcons" or "Alabama-Crimson-Tide"
            
        Returns:
            Tuple of (full_name_with_spaces, school_name, mascot_name)
            
        Examples:
            "Air-Force-Falcons" -> ("Air Force Falcons", "Air Force", "Falcons")
            "Alabama-Crimson-Tide" -> ("Alabama Crimson Tide", "Alabama", "Crimson Tide")
            "Central-Florida-Knights" -> ("Central Florida Knights", "Central Florida", "Knights")
        """
        # Remove extension if present
        name = Path(filename).stem
        
        # Remove hyphens to get full name with spaces
        full_name = name.replace('-', ' ')
        
        # Split into words
        words = name.split('-')
        
        if len(words) < 2:
            # If there's only one word, return it as both school and mascot
            return (full_name, full_name, full_name)
        
        # The mascot name is typically the last 1-2 words
        # For multi-word mascots like "Crimson Tide", "Yellow Jackets", "Sun Devils"
        # we need to check if the last word is commonly part of a multi-word mascot
        
        # Common multi-word mascot patterns
        two_word_mascots = [
            'crimson tide', 'yellow jackets', 'sun devils', 'golden bears',
            'fighting illini', 'blue devils', 'golden eagles', 'black knights',
            'red raiders', 'blue hens', 'green wave', 'rainbow warriors',
            'golden gophers', 'scarlet knights', 'mean green', 'ragin cajuns'
        ]
        
        # Check if last two words form a known multi-word mascot
        if len(words) >= 2:
            last_two = '-'.join(words[-2:]).lower()
            if last_two in two_word_mascots:
                # Multi-word mascot
                mascot_name = ' '.join(words[-2:])
                school_name = ' '.join(words[:-2])
            else:
                # Single-word mascot
                mascot_name = words[-1]
                school_name = ' '.join(words[:-1])
        else:
            # Fallback
            mascot_name = words[-1]
            school_name = ' '.join(words[:-1])
        
        return (full_name, school_name, mascot_name)
    
    def find_college_logo_images(self) -> List[dict]:
        """
        Query Firestore for all images from College_Logos folder.
        Returns list of image documents.
        """
        try:
            images_ref = self.firestore_db.collection('aac_images')
            
            # Search for images with concept = "College_Logos"
            query = images_ref.where(filter=firestore.FieldFilter('concept', '==', 'College_Logos'))
            docs = list(query.stream())
            
            logger.info(f"📊 Found {len(docs)} college logo images to update")
            
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
            
        except Exception as e:
            logger.error(f"❌ Error querying Firestore: {e}")
            return []
    
    def update_image_tags(self, image_id: str, current_tags: List[str], subconcept: str) -> bool:
        """
        Update tags for a single image.
        
        Args:
            image_id: Firestore document ID
            current_tags: Current tags array
            subconcept: The subconcept (filename without extension)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse the subconcept to get school and mascot names
            full_name, school_name, mascot_name = self.parse_college_name(subconcept)
            
            # Build new tags array
            new_tags = [
                full_name,      # Tag 0: Full name with spaces (no hyphens)
                school_name,    # Tag 1: School name only
                mascot_name     # Tag 2: Mascot name only
            ]
            
            # Keep any additional AI-generated tags (beyond the first 2)
            if len(current_tags) > 2:
                new_tags.extend(current_tags[2:])
            
            # Update Firestore document
            self.firestore_db.collection('aac_images').document(image_id).update({
                'tags': new_tags
            })
            
            logger.info(f"✅ Updated: {subconcept}")
            logger.info(f"   Tag 0: {new_tags[0]}")
            logger.info(f"   Tag 1: {new_tags[1]}")
            logger.info(f"   Tag 2: {new_tags[2]}")
            
            self.updated_count += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating {image_id}: {e}")
            self.error_count += 1
            return False
    
    def run(self):
        """Main execution method"""
        logger.info("🚀 Starting college logo tag update process...")
        
        # Find all college logo images
        images = self.find_college_logo_images()
        
        if not images:
            logger.warning("⚠️ No college logo images found")
            return
        
        # Update each image
        for image in images:
            image_id = image['id']
            current_tags = image.get('tags', [])
            subconcept = image.get('subconcept', '')
            
            if not subconcept:
                logger.warning(f"⚠️ Skipping image {image_id} - no subconcept")
                continue
            
            self.update_image_tags(image_id, current_tags, subconcept)
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info(f"✨ Update complete!")
        logger.info(f"   Images updated: {self.updated_count}")
        logger.info(f"   Errors: {self.error_count}")
        logger.info("="*60)

def main():
    updater = CollegeLogoTagUpdater()
    updater.run()

if __name__ == "__main__":
    main()
