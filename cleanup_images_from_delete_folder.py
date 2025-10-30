#!/usr/bin/env python3
"""
Firestore Image Cleanup Script

This script helps remove unwanted images from the Firestore database by:
1. Scanning a Delete_Images folder for images to remove
2. Finding matching records in Firestore based on filename patterns
3. Deleting the matching records from the aac_images collection
4. Providing detailed reports of what was deleted

Usage:
1. Create a Delete_Images folder in your project root
2. Move unwanted images from BravoImages subfolders to Delete_Images (maintaining structure is optional)
3. Run: python3 cleanup_images_from_delete_folder.py [--dry-run] [--verbose]

The script will:
- Match images by filename pattern (concept_subconcept_timestamp.png)
- Handle both exact matches and fuzzy matches
- Provide detailed logging and confirmation prompts
- Support dry-run mode for testing
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import re
import json

# Firebase and Google Cloud imports
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as firestore_client

# Configuration
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'image_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ImageCleanupManager:
    def __init__(self, project_id: str = None, dry_run: bool = False, verbose: bool = False):
        self.project_id = project_id or config.CONFIG.get('gcp_project_id')
        self.dry_run = dry_run
        self.verbose = verbose
        self.firestore_db = None
        self.delete_folder = Path("Delete_Images")
        
        # Statistics
        self.stats = {
            'images_found': 0,
            'firestore_matches': 0,
            'exact_matches': 0,
            'fuzzy_matches': 0,
            'deleted_count': 0,
            'errors': 0,
            'skipped': 0
        }
        
        self.setup_clients()
        
    def setup_clients(self):
        """Initialize Firebase and Firestore clients"""
        try:
            # Initialize Firebase Admin if not already initialized
            if not firebase_admin._apps:
                service_account_path = config.CONFIG.get('service_account_key_path')
                if service_account_path and os.path.exists(service_account_path):
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()
            
            # Initialize Firestore
            self.firestore_db = firestore.Client(project=self.project_id)
            
            logger.info("✅ Successfully initialized Firebase and Firestore clients")
            logger.info(f"🗃️ Using project: {self.project_id}")
            
        except Exception as e:
            logger.error(f"❌ Error initializing clients: {e}")
            raise
    
    def find_images_to_delete(self) -> List[Tuple[str, str, str, str]]:
        """
        Scan Delete_Images folder and return list of (image_path, concept, subconcept, original_filename)
        """
        images_to_delete = []
        
        if not self.delete_folder.exists():
            logger.error(f"❌ Delete folder not found: {self.delete_folder}")
            logger.info("💡 Please create a 'Delete_Images' folder and move unwanted images there")
            return images_to_delete
        
        logger.info(f"🔍 Scanning {self.delete_folder} for images to delete...")
        
        # Find all PNG images recursively
        png_files = list(self.delete_folder.rglob("*.png"))
        
        logger.info(f"📸 Found {len(png_files)} PNG files in Delete_Images folder")
        
        for image_file in png_files:
            try:
                # Parse filename to extract concept/subconcept
                concept, subconcept = self.parse_filename(image_file.name)
                if concept and subconcept:
                    images_to_delete.append((
                        str(image_file), 
                        concept, 
                        subconcept, 
                        image_file.name
                    ))
                    if self.verbose:
                        logger.debug(f"  📄 {image_file.name} -> concept: {concept}, subconcept: {subconcept}")
                else:
                    logger.warning(f"⚠️ Could not parse filename: {image_file.name}")
                    self.stats['skipped'] += 1
                    
            except Exception as e:
                logger.error(f"❌ Error processing {image_file}: {e}")
                self.stats['errors'] += 1
        
        self.stats['images_found'] = len(images_to_delete)
        logger.info(f"🎯 Parsed {len(images_to_delete)} images ready for deletion")
        return images_to_delete
    
    def parse_filename(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse filename to extract concept and subconcept
        
        Expected formats:
        - concept_subconcept_timestamp.png (e.g., "animals_cat_20250926_110616.png")
        - multi_word_concept_timestamp.png (e.g., "ask_for_help_20250927_172732.png")
        - batch_direct_concept_timestamp.png (e.g., "can_you_help_20250929_174221.png")
        """
        try:
            # Remove .png extension
            stem = filename.replace('.png', '')
            parts = stem.split('_')
            
            if len(parts) < 3:
                return None, None
            
            # Find timestamp part (should be 8 digits followed by 6 digits)
            timestamp_idx = -1
            time_idx = -1
            
            for i in range(len(parts) - 1):
                if (len(parts[i]) == 8 and parts[i].isdigit() and 
                    i + 1 < len(parts) and len(parts[i + 1]) == 6 and parts[i + 1].isdigit()):
                    timestamp_idx = i
                    time_idx = i + 1
                    break
            
            if timestamp_idx < 1:
                # Try alternative: just look for 8-digit part
                for i, part in enumerate(parts):
                    if len(part) == 8 and part.isdigit():
                        timestamp_idx = i
                        break
            
            if timestamp_idx < 1:
                logger.warning(f"Could not find timestamp in filename: {filename}")
                return None, None
            
            # Everything before timestamp is the subconcept
            subconcept_parts = parts[:timestamp_idx]
            subconcept = '_'.join(subconcept_parts)
            
            # Determine concept based on common patterns
            concept = self.determine_concept(subconcept, filename)
            
            return concept, subconcept
            
        except Exception as e:
            logger.error(f"Error parsing filename {filename}: {e}")
            return None, None
    
    def determine_concept(self, subconcept: str, filename: str) -> str:
        """
        Determine the concept category based on subconcept and filename
        """
        # Known concept mappings from your BravoImages structure
        concept_mappings = {
            # Animals
            'ant': 'animals', 'bear': 'animals', 'bee': 'animals', 'bird': 'animals', 
            'butterfly': 'animals', 'cat': 'animals', 'chicken': 'animals', 'cow': 'animals',
            'dog': 'animals', 'dolphin': 'animals', 'duck': 'animals', 'eagle': 'animals', 
            'elephant': 'animals', 'fish': 'animals', 'frog': 'animals', 'giraffe': 'animals',
            'horse': 'animals', 'lion': 'animals', 'monkey': 'animals', 'mouse': 'animals', 
            'owl': 'animals', 'parrot': 'animals', 'penguin': 'animals', 'pig': 'animals',
            'rabbit': 'animals', 'sheep': 'animals', 'snake': 'animals', 'spider': 'animals', 
            'tiger': 'animals', 'turtle': 'animals', 'whale': 'animals', 'zebra': 'animals',
            
            # Colors
            'red': 'colors', 'blue': 'colors', 'green': 'colors', 'yellow': 'colors', 
            'orange': 'colors', 'purple': 'colors', 'pink': 'colors', 'black': 'colors',
            'white': 'colors', 'brown': 'colors', 'gray': 'colors', 'grey': 'colors',
            
            # Actions
            'run': 'actions', 'walk': 'actions', 'jump': 'actions', 'sit': 'actions', 
            'stand': 'actions', 'eat': 'actions', 'drink': 'actions', 'sleep': 'actions',
            'play': 'actions', 'read': 'actions', 'write': 'actions', 'draw': 'actions', 
            'sing': 'actions', 'dance': 'actions',
            
            # Emotions
            'happy': 'emotions', 'sad': 'emotions', 'angry': 'emotions', 'excited': 'emotions', 
            'scared': 'emotions', 'surprised': 'emotions', 'confused': 'emotions', 
            'proud': 'emotions', 'shy': 'emotions', 'calm': 'emotions',
            
            # Objects
            'chair': 'objects', 'table': 'objects', 'book': 'objects', 'ball': 'objects', 
            'toy': 'objects', 'car': 'objects', 'house': 'objects', 'tree': 'objects',
            'flower': 'objects', 'apple': 'objects', 'banana': 'objects',
            
            # People
            'mom': 'people', 'dad': 'people', 'teacher': 'people', 'friend': 'people', 
            'baby': 'people', 'child': 'people', 'person': 'people',
            
            # Places
            'home': 'places', 'school': 'places', 'park': 'places', 'store': 'places', 
            'hospital': 'places', 'restaurant': 'places',
            
            # Abstract concepts
            'help': 'abstract', 'please': 'abstract', 'thank_you': 'abstract', 'sorry': 'abstract', 
            'yes': 'abstract', 'no': 'abstract', 'more': 'abstract', 'stop': 'abstract',
            'go': 'abstract', 'good': 'abstract', 'bad': 'abstract'
        }
        
        # Check if subconcept matches any known mappings
        for key, concept in concept_mappings.items():
            if subconcept.startswith(key) or key in subconcept:
                return concept
        
        # Check if filename indicates batch processing
        if 'batch_' in filename:
            # Extract batch number from filename path or name
            batch_match = re.search(r'batch_(\d+)', filename)
            if batch_match:
                return f"batch_{batch_match.group(1)}"
        
        # Default fallback - try to infer from common patterns
        if any(word in subconcept.lower() for word in ['help', 'please', 'thank', 'sorry']):
            return 'abstract'
        elif any(word in subconcept.lower() for word in ['happy', 'sad', 'angry', 'feel']):
            return 'emotions'
        elif any(word in subconcept.lower() for word in ['run', 'walk', 'eat', 'play']):
            return 'actions'
        else:
            return 'unknown'
    
    async def find_firestore_matches(self, images_to_delete: List[Tuple[str, str, str, str]]) -> List[Dict]:
        """
        Find matching records in Firestore for the images to delete
        """
        matches = []
        
        logger.info(f"🔍 Searching Firestore for {len(images_to_delete)} images...")
        
        for image_path, concept, subconcept, filename in images_to_delete:
            try:
                # Try filename-based matching first (most precise)
                filename_matches = await self.find_filename_matches(filename)
                if filename_matches:
                    matches.extend(filename_matches)
                    self.stats['exact_matches'] += len(filename_matches)
                    if self.verbose:
                        logger.info(f"✅ Found {len(filename_matches)} exact filename matches for {filename}")
                    continue
                
                # Extract timestamp from filename for fallback matching
                timestamp = self.extract_timestamp_from_filename(filename)
                
                # Try timestamp-based matching (second most precise)
                if timestamp:
                    timestamp_matches = await self.find_timestamp_matches(concept, subconcept, timestamp, filename)
                    if timestamp_matches:
                        matches.extend(timestamp_matches)
                        self.stats['exact_matches'] += len(timestamp_matches)
                        if self.verbose:
                            logger.info(f"✅ Found {len(timestamp_matches)} timestamp matches for {filename}")
                        continue
                
                # Try exact concept+subconcept matches (less reliable)
                exact_matches = await self.find_exact_matches(concept, subconcept, filename)
                if exact_matches:
                    # Filter exact matches by timestamp if possible
                    filtered_matches = self.filter_matches_by_timestamp(exact_matches, timestamp, filename)
                    if filtered_matches:
                        matches.extend(filtered_matches)
                        self.stats['exact_matches'] += len(filtered_matches)
                        if self.verbose:
                            logger.info(f"✅ Found {len(filtered_matches)} filtered exact matches for {filename}")
                    else:
                        logger.warning(f"⚠️ Found {len(exact_matches)} concept/subconcept matches for {filename}, but none match timestamp - skipping for safety")
                else:
                    logger.warning(f"⚠️ No matches found for {filename}")
                        
            except Exception as e:
                logger.error(f"❌ Error searching for {filename}: {e}")
                self.stats['errors'] += 1
        
        self.stats['firestore_matches'] = len(matches)
        logger.info(f"🎯 Found {len(matches)} total Firestore records to delete")
        return matches
    
    def extract_timestamp_from_filename(self, filename: str) -> Optional[str]:
        """Extract timestamp from filename (YYYYMMDD_HHMMSS format)"""
        try:
            # Look for pattern: 8digits_6digits
            import re
            pattern = r'(\d{8})_(\d{6})'
            match = re.search(pattern, filename)
            if match:
                return f"{match.group(1)}_{match.group(2)}"
            return None
        except Exception as e:
            logger.error(f"Error extracting timestamp from {filename}: {e}")
            return None
    
    async def find_filename_matches(self, filename: str) -> List[Dict]:
        """Find matches by searching for the exact filename in the image_url field"""
        matches = []
        
        try:
            # Get all bravo_images records and check if filename appears in image_url
            query = (self.firestore_db.collection("aac_images")
                    .where("source", "==", "bravo_images"))
            
            docs = await asyncio.to_thread(query.get)
            
            # Remove .png extension from filename for comparison
            filename_stem = filename.replace('.png', '')
            
            for doc in docs:
                data = doc.to_dict()
                image_url = data.get('image_url', '')
                
                # Check if the filename (without .png) appears in the image_url
                # This handles cases where the stored filename might have different extensions
                # or be part of a longer URL path
                if filename_stem in image_url or filename in image_url:
                    data['firestore_id'] = doc.id
                    data['match_type'] = 'filename_exact'
                    matches.append(data)
                    if self.verbose:
                        logger.debug(f"  📍 Filename match: {filename} found in {image_url}")
            
            if matches:
                logger.info(f"  🎯 Found {len(matches)} records with filename '{filename}' in image_url")
            else:
                logger.info(f"  ❌ No records found with filename '{filename}' in image_url")
                        
        except Exception as e:
            logger.error(f"Error in filename match query: {e}")
        
        return matches
    
    async def find_timestamp_matches(self, concept: str, subconcept: str, timestamp: str, filename: str) -> List[Dict]:
        """Find matches by looking for the timestamp in the image_url"""
        matches = []
        
        try:
            # Get all records with matching concept and subconcept
            query = (self.firestore_db.collection("aac_images")
                    .where("source", "==", "bravo_images")
                    .where("concept", "==", concept)
                    .where("subconcept", "==", subconcept))
            
            docs = await asyncio.to_thread(query.get)
            
            for doc in docs:
                data = doc.to_dict()
                image_url = data.get('image_url', '')
                
                # Check if the timestamp appears in the image_url
                if timestamp in image_url:
                    data['firestore_id'] = doc.id
                    data['match_type'] = 'timestamp_exact'
                    matches.append(data)
                    if self.verbose:
                        logger.debug(f"  📍 Timestamp match: {image_url}")
                        
        except Exception as e:
            logger.error(f"Error in timestamp match query: {e}")
        
        return matches
    
    def filter_matches_by_timestamp(self, matches: List[Dict], timestamp: Optional[str], filename: str) -> List[Dict]:
        """Filter matches by timestamp if available"""
        if not timestamp:
            # If no timestamp, return all matches but warn if multiple
            if len(matches) > 1:
                logger.warning(f"⚠️ Multiple matches found for {filename} but no timestamp to filter - returning all {len(matches)} matches")
            return matches
        
        # Filter by timestamp in image_url
        filtered = []
        for match in matches:
            image_url = match.get('image_url', '')
            if timestamp in image_url:
                filtered.append(match)
            elif self.verbose:
                logger.debug(f"  🚫 Filtered out: {image_url} (timestamp mismatch)")
        
        if not filtered and matches:
            logger.warning(f"⚠️ No timestamp matches found for {filename}, but {len(matches)} concept/subconcept matches exist")
            # Return empty list for safety - don't delete if timestamp doesn't match
            return []
        
        return filtered
    
    async def find_exact_matches(self, concept: str, subconcept: str, filename: str) -> List[Dict]:
        """Find exact matches in Firestore"""
        matches = []
        
        try:
            # Query by concept and subconcept
            query = (self.firestore_db.collection("aac_images")
                    .where("source", "==", "bravo_images")
                    .where("concept", "==", concept)
                    .where("subconcept", "==", subconcept))
            
            docs = await asyncio.to_thread(query.get)
            
            for doc in docs:
                data = doc.to_dict()
                data['firestore_id'] = doc.id
                data['match_type'] = 'exact'
                matches.append(data)
                
        except Exception as e:
            logger.error(f"Error in exact match query: {e}")
        
        return matches
    
    async def find_fuzzy_matches(self, concept: str, subconcept: str, filename: str) -> List[Dict]:
        """Find fuzzy matches using different strategies - more conservative now"""
        matches = []
        
        logger.warning(f"⚠️ Using fuzzy matching for {filename} - this is less precise!")
        
        try:
            # Strategy 1: Match by subconcept only (but warn about multiple matches)
            query1 = (self.firestore_db.collection("aac_images")
                     .where("source", "==", "bravo_images")
                     .where("subconcept", "==", subconcept))
            
            docs1 = await asyncio.to_thread(query1.get)
            for doc in docs1:
                data = doc.to_dict()
                data['firestore_id'] = doc.id
                data['match_type'] = 'fuzzy_subconcept'
                matches.append(data)
            
            if len(matches) > 1:
                logger.warning(f"⚠️ Found {len(matches)} records with subconcept '{subconcept}' - may delete more than intended!")
            
            # Strategy 2: Match by tags containing subconcept (only if no subconcept matches)
            if not matches:
                # Convert subconcept underscores to spaces for tag matching
                searchable_subconcept = subconcept.replace('_', ' ')
                query2 = (self.firestore_db.collection("aac_images")
                         .where("source", "==", "bravo_images")
                         .where("tags", "array_contains", searchable_subconcept))
                
                docs2 = await asyncio.to_thread(query2.get)
                for doc in docs2:
                    data = doc.to_dict()
                    data['firestore_id'] = doc.id
                    data['match_type'] = 'fuzzy_tags'
                    matches.append(data)
            
            # Strategy 3: Partial filename match in image_url
            if not matches:
                # Extract base name without timestamp for partial matching
                base_name = subconcept.replace('_', '')[:10]  # First 10 chars
                
                # Get all bravo_images and check URLs
                all_query = (self.firestore_db.collection("aac_images")
                           .where("source", "==", "bravo_images"))
                
                all_docs = await asyncio.to_thread(all_query.get)
                for doc in all_docs:
                    data = doc.to_dict()
                    image_url = data.get('image_url', '')
                    if base_name.lower() in image_url.lower():
                        data['firestore_id'] = doc.id
                        data['match_type'] = 'fuzzy_url'
                        matches.append(data)
                        
                        # Limit fuzzy URL matches to prevent too many
                        if len(matches) >= 5:
                            break
                            
        except Exception as e:
            logger.error(f"Error in fuzzy match query: {e}")
        
        return matches
    
    async def delete_firestore_records(self, matches: List[Dict]) -> int:
        """Delete the matched records from Firestore"""
        deleted_count = 0
        
        if self.dry_run:
            logger.info("🧪 DRY RUN MODE - No actual deletions will be performed")
            return len(matches)  # Return what would be deleted
        
        logger.info(f"🗑️ Deleting {len(matches)} records from Firestore...")
        
        for match in matches:
            try:
                doc_id = match['firestore_id']
                concept = match.get('concept', 'unknown')
                subconcept = match.get('subconcept', 'unknown')
                match_type = match.get('match_type', 'unknown')
                
                # Delete the document
                await asyncio.to_thread(
                    self.firestore_db.collection("aac_images").document(doc_id).delete
                )
                
                deleted_count += 1
                if self.verbose:
                    logger.info(f"  ✅ Deleted {concept}/{subconcept} (ID: {doc_id[:8]}..., Type: {match_type})")
                
            except Exception as e:
                logger.error(f"❌ Error deleting record {match.get('firestore_id', 'unknown')}: {e}")
                self.stats['errors'] += 1
        
        self.stats['deleted_count'] = deleted_count
        return deleted_count
    
    def generate_report(self, matches: List[Dict]) -> str:
        """Generate a detailed report of what will be/was deleted"""
        report_lines = [
            f"\n{'='*60}",
            f"FIRESTORE IMAGE CLEANUP REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Mode: {'DRY RUN' if self.dry_run else 'LIVE DELETION'}",
            f"{'='*60}",
            f"",
            f"SUMMARY:",
            f"  Images found in Delete_Images folder: {self.stats['images_found']}",
            f"  Firestore matches found: {self.stats['firestore_matches']}",
            f"    - Exact/Timestamp matches: {self.stats['exact_matches']}",
            f"    - Fuzzy matches: {self.stats['fuzzy_matches']}",
            f"  Records deleted: {self.stats['deleted_count']}",
            f"  Errors encountered: {self.stats['errors']}",
            f"  Files skipped: {self.stats['skipped']}",
            f"",
            f"DETAILED BREAKDOWN:",
        ]
        
        # Group matches by type
        by_type = {}
        for match in matches:
            match_type = match.get('match_type', 'unknown')
            if match_type not in by_type:
                by_type[match_type] = []
            by_type[match_type].append(match)
        
        for match_type, type_matches in by_type.items():
            report_lines.append(f"\n  {match_type.upper()} MATCHES ({len(type_matches)}):")
            for match in type_matches:  # Show all matches now for better visibility
                concept = match.get('concept', 'unknown')
                subconcept = match.get('subconcept', 'unknown')
                doc_id = match.get('firestore_id', 'unknown')[:8]
                image_url = match.get('image_url', '')
                url_part = image_url.split('/')[-1] if image_url else 'no_url'
                
                # Show more detail for verification
                report_lines.append(f"    - {concept}/{subconcept}")
                report_lines.append(f"      ID: {doc_id}...")
                report_lines.append(f"      URL: {url_part}")
                
                # Extract timestamp from URL for verification
                if image_url:
                    import re
                    timestamp_match = re.search(r'(\d{8}_\d{6})', image_url)
                    if timestamp_match:
                        report_lines.append(f"      Timestamp: {timestamp_match.group(1)}")
                report_lines.append("")
        
        # Add safety warnings for fuzzy matches
        fuzzy_count = sum(len(matches) for match_type, matches in by_type.items() if 'fuzzy' in match_type.lower())
        if fuzzy_count > 0:
            report_lines.extend([
                f"⚠️  WARNING: {fuzzy_count} fuzzy matches found!",
                f"   These may not be the exact images you intended to delete.",
                f"   Review the URLs above carefully before proceeding.",
                f"",
            ])
        
        report_lines.extend([
            f"{'='*60}",
            f"END REPORT",
            f"{'='*60}"
        ])
        
        return '\n'.join(report_lines)
    
    def save_backup_data(self, matches: List[Dict]) -> str:
        """Save backup data before deletion"""
        backup_file = f"firestore_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            # Convert datetime objects to strings for JSON serialization
            backup_data = []
            for match in matches:
                clean_match = {}
                for key, value in match.items():
                    if hasattr(value, 'isoformat'):  # datetime object
                        clean_match[key] = value.isoformat()
                    else:
                        clean_match[key] = value
                backup_data.append(clean_match)
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"💾 Backup data saved to: {backup_file}")
            return backup_file
            
        except Exception as e:
            logger.error(f"❌ Error saving backup: {e}")
            return None
    
    async def run_cleanup(self):
        """Run the complete cleanup process"""
        logger.info("🚀 Starting Firestore Image Cleanup Process")
        logger.info(f"📁 Project: {self.project_id}")
        logger.info(f"🧪 Dry Run: {self.dry_run}")
        logger.info(f"🔍 Verbose: {self.verbose}")
        
        try:
            # Step 1: Find images to delete
            images_to_delete = self.find_images_to_delete()
            if not images_to_delete:
                logger.warning("⚠️ No images found in Delete_Images folder. Exiting.")
                return
            
            # Step 2: Find matching Firestore records
            matches = await self.find_firestore_matches(images_to_delete)
            if not matches:
                logger.warning("⚠️ No matching Firestore records found. Nothing to delete.")
                return
            
            # Step 3: Generate and display report
            report = self.generate_report(matches)
            print(report)
            
            # Step 4: Save backup
            backup_file = self.save_backup_data(matches)
            
            # Step 5: Confirmation (unless dry run)
            if not self.dry_run:
                print(f"\n⚠️  WARNING: This will permanently delete {len(matches)} records from Firestore!")
                print(f"📄 Backup saved to: {backup_file}")
                
                confirmation = input("\nAre you sure you want to proceed? Type 'DELETE' to confirm: ")
                if confirmation != 'DELETE':
                    logger.info("❌ Operation cancelled by user.")
                    return
            
            # Step 6: Perform deletion
            deleted_count = await self.delete_firestore_records(matches)
            
            # Step 7: Final report
            mode_text = "would be deleted" if self.dry_run else "deleted"
            logger.info(f"✅ Cleanup complete! {deleted_count} records {mode_text}.")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup process: {e}")
            raise

def main():
    """Main function with command line argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up Firestore images based on Delete_Images folder')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--project-id', type=str,
                       help='GCP Project ID (uses config default if not specified)')
    
    args = parser.parse_args()
    
    # Create cleanup manager
    manager = ImageCleanupManager(
        project_id=args.project_id,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    # Run cleanup
    asyncio.run(manager.run_cleanup())

if __name__ == "__main__":
    main()