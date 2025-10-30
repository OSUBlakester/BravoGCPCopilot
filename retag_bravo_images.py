#!/usr/bin/env python3
"""
Repair BravoImages with truncated subconcepts and poor tags.

This script:
1. Finds images with truncated subconcepts (e.g., "can" should be "can_you_help")
2. Reconstructs the full subconcept from the filename 
3. Re-generates appropriate tags using the corrected subconcept
4. Fixes images that only have basic fallback tags

This will make multi-word images searchable again!

Usage:
  python3 retag_bravo_images.py           # Repair all problematic images
  python3 retag_bravo_images.py 50        # Repair first 50 images only
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import List
import sys

# Import from the main script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from bulk_import_bravo_images import BravoImageImporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('retag_bravo_images.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BravoImageRetagger(BravoImageImporter):
    async def generate_image_tags(self, image_url: str, concept: str, subconcept: str) -> List[str]:
        """Generate image tags, ensuring no batch prefixes and making terms searchable"""
        # Clean subconcept to completely remove any batch prefixes
        clean_subconcept = subconcept
        if '_' in clean_subconcept:
            parts = clean_subconcept.split('_')
            # Remove batch prefix if present: batch_009_piercing -> piercing
            if len(parts) >= 2 and parts[0].startswith('batch_'):
                clean_subconcept = '_'.join(parts[2:]) if len(parts) > 2 else parts[1]
        
        # Clean concept too, just in case
        clean_concept = concept
        if '_' in clean_concept:
            parts = clean_concept.split('_')
            # Remove batch prefix if present
            if len(parts) >= 2 and parts[0].startswith('batch_'):
                clean_concept = '_'.join(parts[2:]) if len(parts) > 2 else parts[1]
        
        # Extract the actual searchable term from the subconcept
        # For "food_pork" -> primary term should be "pork"
        # For "batch_009_texas" -> primary term should be "texas"  
        # For "piercing" -> primary term should be "piercing"
        searchable_term = clean_subconcept
        if '_' in clean_subconcept:
            parts = clean_subconcept.split('_')
            # Remove any batch prefixes first
            if parts[0].startswith('batch_'):
                parts = parts[1:]
            # Take the last meaningful part as the primary searchable term
            if len(parts) > 0:
                searchable_term = parts[-1]
        
        # Call parent method to get AI-generated tags
        tags = await super().generate_image_tags(image_url, clean_concept, clean_subconcept)
        
        # Build final tag list with searchable term first and NO batch prefixes
        final_tags = [searchable_term]
        
        # Add concept if it's different from searchable term and doesn't contain batch
        if (clean_concept != searchable_term and 
            clean_concept not in final_tags and 
            not clean_concept.startswith('batch_') and 
            'batch_' not in clean_concept.lower()):
            final_tags.append(clean_concept)
        
        # Add AI-generated tags, strictly filtering out ALL batch references
        if tags:
            for tag in tags:
                if (tag and 
                    tag not in final_tags and 
                    not tag.startswith('batch_') and 
                    'batch_' not in tag.lower() and
                    tag != clean_subconcept and  # Don't add the full subconcept
                    tag != subconcept):  # Don't add the original subconcept either
                    final_tags.append(tag)
        
        # Final safety check: remove any batch references that somehow got through
        final_tags = [tag for tag in final_tags if 'batch_' not in tag.lower()]
        
        # Ensure the searchable term is first and present
        if searchable_term not in final_tags:
            final_tags.insert(0, searchable_term)
        elif final_tags[0] != searchable_term:
            final_tags.remove(searchable_term)
            final_tags.insert(0, searchable_term)
        
        return final_tags[:15]  # Limit to 15 tags max
        
        # Fallback if no tags generated
        return [searchable_term, clean_concept] if searchable_term != clean_concept else [searchable_term]

    async def find_images_needing_repair(self) -> List[dict]:
        """Find images with truncated subconcepts or needing better tags"""
        try:
            import re
            
            # Query ALL BravoImages (using the correct collection name)
            query = self.firestore_db.collection("aac_images").where("source", "==", "bravo_images")  # Fixed collection name
            docs = await asyncio.to_thread(query.get)
            
            images_to_repair = []
            total_checked = 0
            
            for doc in docs:
                total_checked += 1
                data = doc.to_dict()
                
                if not data:
                    continue
                
                # SMART RESUME: Skip images that have already been repaired
                updated_by = data.get('updated_by', '')
                repair_info = data.get('repair_info', {})
                
                # If already repaired by this script, skip it
                if updated_by == 'repair_script_v2' or repair_info:
                    continue
                    
                subconcept = data.get('subconcept', '')
                image_url = data.get('image_url', '')
                tags = data.get('tags', [])
                
                repair_needed = False
                repair_reason = []
                
                # 1. Check for truncated subconcepts (NEW FEATURE)
                if subconcept and image_url:
                    # Extract filename from URL
                    filename = image_url.split('/')[-1] if '/' in image_url else ''
                    
                    if filename:
                        # Check if this looks like a truncated subconcept
                        # Pattern: subconcept is single word but filename suggests multi-word
                        if '_' not in subconcept and len(subconcept.split()) == 1:
                            # Check if filename has multiple words (indicated by underscores before timestamp)
                            name_without_ext = filename.rsplit('.', 1)[0]
                            parts = name_without_ext.split('_')
                            
                            # Look for timestamp pattern (YYYYMMDD_HHMMSS)
                            timestamp_found = False
                            timestamp_index = -1
                            
                            for i, part in enumerate(parts):
                                if re.match(r'^\d{8}$', part) and i + 1 < len(parts) and re.match(r'^\d{6}$', parts[i + 1]):
                                    timestamp_found = True
                                    timestamp_index = i
                                    break
                            
                            if timestamp_found and timestamp_index > 0:
                                # Reconstruct the full subconcept
                                reconstructed_parts = parts[:timestamp_index]
                                
                                # Remove batch prefixes (batch_008, batch_009, etc.)
                                if len(reconstructed_parts) > 0 and reconstructed_parts[0].startswith('batch_'):
                                    reconstructed_parts = reconstructed_parts[1:]
                                
                                # Only proceed if we have meaningful parts after removing batch prefix
                                if len(reconstructed_parts) > 0:
                                    reconstructed_subconcept = '_'.join(reconstructed_parts)
                                    
                                    # Only flag for repair if the current subconcept is actually truncated
                                    # or if it includes batch prefixes that shouldn't be there
                                    needs_repair = False
                                    
                                    # Case 1: Current subconcept is shorter than what we reconstructed
                                    if len(subconcept.split('_')) < len(reconstructed_parts):
                                        needs_repair = True
                                    
                                    # Case 2: Current subconcept contains batch prefix
                                    elif subconcept.startswith(('batch_008', 'batch_009')):
                                        needs_repair = True
                                    
                                    if needs_repair and reconstructed_subconcept != subconcept:
                                        repair_needed = True
                                        repair_reason.append(f"truncated_subconcept: '{subconcept}' → '{reconstructed_subconcept}'")
                                        data['reconstructed_subconcept'] = reconstructed_subconcept
                
                # 2. Check for poor tagging (EXISTING FEATURE)
                truly_generic_tags = {'aac', 'bravo_images'}
                has_truly_generic = any(tag.lower() in truly_generic_tags for tag in tags)
                too_few_tags = len(tags) < 4
                wrong_priority = len(tags) > 0 and tags[0].lower() != subconcept.lower()
                
                if has_truly_generic:
                    repair_needed = True
                    repair_reason.append("has_generic_tags")
                if too_few_tags:
                    repair_needed = True
                    repair_reason.append("too_few_tags")
                if wrong_priority:
                    repair_needed = True
                    repair_reason.append("wrong_priority")
                
                if repair_needed:
                    images_to_repair.append({
                        'id': doc.id,
                        'concept': data.get('concept'),
                        'subconcept': data.get('subconcept'),
                        'reconstructed_subconcept': data.get('reconstructed_subconcept'),
                        'image_url': data.get('image_url'),
                        'current_tags': tags,
                        'repair_reasons': repair_reason,
                        'filename': filename
                    })
            
            logger.info(f"📊 Checked {total_checked} total images")
            logger.info(f"🔧 Found {len(images_to_repair)} images needing repair")
            
            # Show breakdown of repair reasons
            reason_counts = {}
            for img in images_to_repair:
                for reason in img['repair_reasons']:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            logger.info("🔍 Repair reasons breakdown:")
            for reason, count in reason_counts.items():
                logger.info(f"   - {reason}: {count} images")
            
            return images_to_repair
            
        except Exception as e:
            logger.error(f"Error finding images to repair: {e}")
            return []
    
    async def repair_image(self, image_data: dict) -> bool:
        """Repair subconcepts and re-generate tags for a single image"""
        try:
            concept = image_data['concept']
            original_subconcept = image_data['subconcept']
            reconstructed_subconcept = image_data.get('reconstructed_subconcept')
            image_url = image_data['image_url']
            doc_id = image_data['id']
            repair_reasons = image_data.get('repair_reasons', [])
            
            # Use reconstructed subconcept if available, otherwise original
            final_subconcept = reconstructed_subconcept if reconstructed_subconcept else original_subconcept
            
            logger.info(f"🔧 Repairing {concept}/{original_subconcept}")
            if reconstructed_subconcept:
                logger.info(f"   📝 Subconcept: '{original_subconcept}' → '{reconstructed_subconcept}'")
            logger.info(f"   🎯 Reasons: {', '.join(repair_reasons)}")
            
            # Generate new tags using the corrected subconcept
            new_tags = await self.generate_image_tags(image_url, concept, final_subconcept)
            
            # Prepare update data
            update_data = {
                'tags': new_tags,
                'updated_at': datetime.now(timezone.utc),
                'updated_by': 'repair_script_v2'
            }
            
            # If subconcept was reconstructed, update it
            if reconstructed_subconcept:
                update_data['subconcept'] = reconstructed_subconcept
                update_data['repair_info'] = {
                    'original_subconcept': original_subconcept,
                    'repair_method': 'filename_reconstruction',
                    'repair_reasons': repair_reasons,
                    'repaired_at': datetime.now(timezone.utc).isoformat()
                }
            
            # Update in Firestore (using correct collection name)
            doc_ref = self.firestore_db.collection("aac_images").document(doc_id)
            await asyncio.to_thread(doc_ref.update, update_data)
            
            logger.info(f"✅ Repaired {concept}/{final_subconcept}")
            logger.info(f"🏷️ New tags: {', '.join(new_tags)}")
            
            return True
            
        except Exception as e:
            error_concept = image_data.get('concept', 'unknown')
            error_subconcept = image_data.get('subconcept', 'unknown')
            logger.error(f"❌ Error repairing {error_concept}/{error_subconcept}: {e}")
            return False
    
    async def run_repair(self, batch_size: int = 5, max_repairs: int = None):
        """Repair images with truncated subconcepts and poor tags"""
        logger.info("🔧 Starting BravoImages repair process")
        
        # Find images needing repair
        images_to_repair = await self.find_images_needing_repair()
        
        if not images_to_repair:
            logger.info("✅ All images are already properly configured!")
            return
        
        # Limit repairs if specified
        if max_repairs and len(images_to_repair) > max_repairs:
            logger.info(f"⚠️ Limiting to first {max_repairs} repairs (out of {len(images_to_repair)} found)")
            images_to_repair = images_to_repair[:max_repairs]
            
        logger.info(f"📊 Repairing {len(images_to_repair)} images in batches of {batch_size}")
        
        success_count = 0
        error_count = 0
        subconcept_repairs = 0
        
        # Process in batches
        for i in range(0, len(images_to_repair), batch_size):
            batch = images_to_repair[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(images_to_repair) + batch_size - 1) // batch_size
            
            logger.info(f"🔄 Processing batch {batch_num}/{total_batches}")
            
            for image_data in batch:
                try:
                    success = await self.repair_image(image_data)
                    if success:
                        success_count += 1
                        # Count subconcept repairs
                        if image_data.get('reconstructed_subconcept'):
                            subconcept_repairs += 1
                    else:
                        error_count += 1
                    
                    # Rate limiting - slower to avoid quota issues
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"❌ Batch error: {e}")
                    error_count += 1
        
        logger.info("🎉 Repair process complete!")
        logger.info(f"📊 Results: ✅ {success_count} success, ❌ {error_count} errors")
        logger.info(f"🔧 Subconcept repairs: {subconcept_repairs} images had truncated subconcepts fixed")

async def main():
    try:
        import sys
        
        # Parse command line arguments
        max_repairs = None
        if len(sys.argv) > 1:
            try:
                max_repairs = int(sys.argv[1])
                logger.info(f"🎯 Limiting to {max_repairs} repairs")
            except ValueError:
                logger.info("💡 Usage: python3 retag_bravo_images.py [max_repairs]")
                logger.info("💡 Example: python3 retag_bravo_images.py 50")
                return
        
        # Create repairer instance
        repairer = BravoImageRetagger()
        
        # Run repair process
        await repairer.run_repair(batch_size=5, max_repairs=max_repairs)
        
        logger.info("✨ Multi-word image searches should now work correctly!")
        
    except KeyboardInterrupt:
        logger.info("🛑 Repair process interrupted by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())