#!/usr/bin/env python3
"""
Fix Underscore Tags - Replace underscores with spaces in existing tags

Many BravoImages have tags with underscores (e.g., "can_you_help") which makes them
harder to search for. This script finds all tags containing underscores and
replaces them with spaces for better searchability.

Examples:
- "can_you_help" -> "can you help"
- "ask_for_help" -> "ask for help"  
- "communication_tablet" -> "communication tablet"

Usage: python fix_underscore_tags.py
"""

import logging
from google.cloud import firestore
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_underscore_tags.log'),
        logging.StreamHandler()
    ]
)

def has_underscores_in_tags(tags):
    """Check if any tags contain underscores"""
    return any('_' in tag for tag in tags if tag)

def fix_tags(tags):
    """Replace underscores with spaces in tags"""
    return [tag.replace('_', ' ') if tag else tag for tag in tags]

def should_update_tags(tags):
    """Check if tags need to be updated (contain underscores)"""
    if not tags:
        return False, None
    
    if not has_underscores_in_tags(tags):
        return False, None
        
    fixed_tags = fix_tags(tags)
    return True, fixed_tags

def fix_underscore_tags():
    """Fix underscore tags by replacing underscores with spaces."""
    
    logging.info("� Starting underscore tags fix...")
    
    # Initialize Firestore
    db = firestore.Client()
    symbols_ref = db.collection('aac_images')
    
    # Find all BravoImages that might have underscore tags
    logging.info("🔍 Finding images with underscore tags...")
    
    # Get all images from bravo_images source
    query = symbols_ref.where('source', '==', 'bravo_images')
    all_images = list(query.stream())
    
    logging.info(f"Found {len(all_images)} BravoImages to check")
    
    images_to_update = []
    total_checked = 0
    
    for doc in all_images:
        total_checked += 1
        image_data = doc.to_dict()
        tags = image_data.get('tags', [])
        
        should_update, fixed_tags = should_update_tags(tags)
        
        if should_update:
            images_to_update.append({
                'doc_id': doc.id,
                'current_tags': tags,
                'fixed_tags': fixed_tags
            })
            
        if total_checked % 100 == 0:
            logging.info(f"Checked {total_checked} images...")
    
    logging.info(f"Found {len(images_to_update)} images that need underscore fixes")
    
    if not images_to_update:
        logging.info("✅ No images need underscore fixes!")
        return
    
    # Show examples
    logging.info("\n📋 Examples of changes to be made:")
    for i, img in enumerate(images_to_update[:5]):
        original = img['current_tags'][:3]  # Show first 3 tags
        fixed = img['fixed_tags'][:3]       # Show first 3 fixed tags
        logging.info(f"  {i+1}. {original} -> {fixed}")
    
    if len(images_to_update) > 5:
        logging.info(f"  ... and {len(images_to_update) - 5} more")
    
    # Confirm before proceeding
    print(f"\n🤔 Ready to fix underscore tags in {len(images_to_update)} images?")
    print("This will replace underscores with spaces in tags for better searchability.")
    response = input("Continue? (y/N): ").strip().lower()
    
    if response != 'y':
        logging.info("❌ Operation cancelled by user")
        return
    
    # Update images
    logging.info(f"� Fixing underscore tags in {len(images_to_update)} images...")
    
    batch = db.batch()
    batch_count = 0
    updated_count = 0
    
    for img in images_to_update:
        doc_ref = symbols_ref.document(img['doc_id'])
        
        batch.update(doc_ref, {
            'tags': img['fixed_tags'],
            'updated_by': 'underscore_fix_script',
            'underscore_fix_date': datetime.now()
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
    
    logging.info(f"✅ Successfully fixed underscore tags in {updated_count} images!")
    
    # Verify the fix
    logging.info("\n🔍 Verifying the fix...")
    
    # Test a few search terms that should now work with spaces
    test_terms = ['can you help', 'ask for help', 'want to go']
    
    for term in test_terms:
        query = symbols_ref.where('tags', 'array_contains', term)
        results = list(query.limit(3).stream())
        
        if results:
            logging.info(f"✅ Search for '{term}' now finds {len(results)} images")
        else:
            logging.info(f"⚠️  Search for '{term}' still finds 0 images")
    
    logging.info("\n🎉 Underscore tags fix complete!")

if __name__ == "__main__":
    fix_underscore_tags()