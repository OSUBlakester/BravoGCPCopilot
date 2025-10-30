#!/usr/bin/env python3
"""
Fix Search Terms - Add Original Searchable Terms Back to Tags

After the repair process changed subconcepts from 'tablet' to 'communication_tablet',
users can no longer search for 'tablet' because it's not in the tags anymore.

This script adds the original searchable terms back to the tags array while keeping
the full subconcept names.
"""

import logging
from google.cloud import firestore
import re
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_search_terms.log'),
        logging.StreamHandler()
    ]
)

def extract_searchable_term(subconcept):
    """
    Extract the searchable term from a subconcept.
    Examples:
    - 'communication_tablet' -> 'tablet'
    - 'actions_catch' -> 'catch'
    - 'negative_descriptors_torn' -> 'torn'
    - 'batch_009_enthusiastic' -> 'enthusiastic'
    """
    # Split by underscore and take the last part
    parts = subconcept.split('_')
    if len(parts) >= 2:
        return parts[-1].lower()
    return subconcept.lower()

def should_add_searchable_term(tags, subconcept):
    """
    Check if we should add the searchable term to tags.
    Only add if:
    1. The subconcept has an underscore (was repaired)
    2. The searchable term isn't already in tags
    3. The searchable term is meaningful (not just a number or single letter)
    """
    if '_' not in subconcept:
        return False, None
    
    searchable_term = extract_searchable_term(subconcept)
    
    # Skip if already in tags (case insensitive)
    tags_lower = [tag.lower() for tag in tags]
    if searchable_term in tags_lower:
        return False, None
    
    # Skip meaningless terms
    if len(searchable_term) <= 1 or searchable_term.isdigit():
        return False, None
    
    # Skip batch numbers
    if subconcept.startswith('batch_') and searchable_term.isdigit():
        return False, None
    
    return True, searchable_term

def fix_search_terms():
    """Fix search terms by adding original searchable terms back to tags."""
    
    logging.info("🚀 Starting search terms fix...")
    
    # Initialize Firestore
    db = firestore.Client()
    symbols_ref = db.collection('aac_images')  # Fixed collection name
    
    # Find images that were repaired and might need searchable terms added
    logging.info("🔍 Finding images that need searchable terms added...")
    
    # Get all images that were updated by the repair script
    query = symbols_ref.where('updated_by', '==', 'repair_script_v2')
    repaired_images = list(query.stream())
    
    logging.info(f"Found {len(repaired_images)} repaired images to check")
    
    images_to_update = []
    total_checked = 0
    
    for doc in repaired_images:
        total_checked += 1
        image_data = doc.to_dict()
        subconcept = image_data.get('subconcept', '')
        tags = image_data.get('tags', [])
        
        should_add, searchable_term = should_add_searchable_term(tags, subconcept)
        
        if should_add:
            images_to_update.append({
                'doc_id': doc.id,
                'subconcept': subconcept,
                'searchable_term': searchable_term,
                'current_tags': tags
            })
            
        if total_checked % 100 == 0:
            logging.info(f"Checked {total_checked} images...")
    
    logging.info(f"Found {len(images_to_update)} images that need searchable terms added")
    
    if not images_to_update:
        logging.info("✅ No images need searchable terms added!")
        return
    
    # Show examples
    logging.info("\n📋 Examples of changes to be made:")
    for i, img in enumerate(images_to_update[:5]):
        logging.info(f"  {i+1}. {img['subconcept']} -> add '{img['searchable_term']}' to tags")
    
    if len(images_to_update) > 5:
        logging.info(f"  ... and {len(images_to_update) - 5} more")
    
    # Confirm before proceeding
    print(f"\n🤔 Ready to add searchable terms to {len(images_to_update)} images?")
    print("This will make images searchable by their original terms (e.g., 'tablet', 'catch', etc.)")
    response = input("Continue? (y/N): ").strip().lower()
    
    if response != 'y':
        logging.info("❌ Operation cancelled by user")
        return
    
    # Update images
    logging.info(f"🔧 Adding searchable terms to {len(images_to_update)} images...")
    
    batch = db.batch()
    batch_count = 0
    updated_count = 0
    
    for img in images_to_update:
        doc_ref = symbols_ref.document(img['doc_id'])
        
        # Add the searchable term to tags
        new_tags = img['current_tags'] + [img['searchable_term']]
        
        batch.update(doc_ref, {
            'tags': new_tags,
            'updated_by': 'search_fix_script',
            'search_fix_date': datetime.now(),
            'search_fix_added_term': img['searchable_term']
        })
        
        batch_count += 1
        updated_count += 1
        
        # Commit batch every 500 operations
        if batch_count >= 500:
            batch.commit()
            logging.info(f"  Committed batch of {batch_count} updates (total: {updated_count})")
            batch = db.batch()
            batch_count = 0
    
    # Commit final batch
    if batch_count > 0:
        batch.commit()
        logging.info(f"  Committed final batch of {batch_count} updates")
    
    logging.info(f"✅ Successfully added searchable terms to {updated_count} images!")
    
    # Verify the fix
    logging.info("\n🔍 Verifying the fix...")
    
    # Test a few search terms
    test_terms = ['tablet', 'catch', 'torn', 'fan']
    
    for term in test_terms:
        query = symbols_ref.where('tags', 'array_contains', term)
        results = list(query.limit(3).stream())
        
        if results:
            logging.info(f"✅ Search for '{term}' now finds {len(results)} images")
            for doc in results[:2]:
                data = doc.to_dict()
                logging.info(f"   📷 {data.get('subconcept', 'unknown')} - tags: {data.get('tags', [])[:5]}...")
        else:
            logging.info(f"⚠️  Search for '{term}' still finds 0 images")
    
    logging.info("\n🎉 Search terms fix complete!")

if __name__ == "__main__":
    fix_search_terms()