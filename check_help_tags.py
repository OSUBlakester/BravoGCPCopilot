#!/usr/bin/env python3
"""
Quick script to check what tags exist for help-related images
"""
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
from google.cloud import firestore
import json

# Set up environment
os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', CONFIG['service_account_key_path'])

async def check_help_images():
    """Check what tags exist for images that should be help-related"""
    
    try:
        # Initialize Firestore client
        db = firestore.Client(project=CONFIG['gcp_project_id'])
        
        print("🔍 Searching for help-related images...")
        
        # Get all bravo_images
        query = db.collection('aac_images').where('source', '==', 'bravo_images')
        docs = query.stream()
        
        help_related = []
        all_subconcepts = set()
        
        for doc in docs:
            data = doc.to_dict()
            subconcept = data.get('subconcept', '')
            concept = data.get('concept', '')
            tags = data.get('tags', [])
            
            all_subconcepts.add(subconcept)
            
            # Look for help-related terms
            search_terms = ['help', 'can', 'ask']
            is_help_related = (
                any(term in subconcept.lower() for term in search_terms) or
                any(term in concept.lower() for term in search_terms) or
                any(any(term in tag.lower() for term in search_terms) for tag in tags)
            )
            
            if is_help_related:
                help_related.append({
                    'subconcept': subconcept,
                    'concept': concept,
                    'tags': tags,
                    'filename_match': any(term in subconcept.lower() for term in ['help', 'can', 'ask'])
                })
        
        print(f"\n📊 Found {len(help_related)} help-related images:")
        print("=" * 60)
        
        for img in help_related:
            print(f"Subconcept: {img['subconcept']}")
            print(f"Concept: {img['concept']}")
            print(f"Tags: {', '.join(img['tags'])}")
            print(f"Filename match: {img['filename_match']}")
            print("-" * 40)
        
        print(f"\n🏷️ Sample of all subconcepts (first 20):")
        sorted_subconcepts = sorted(list(all_subconcepts))[:20]
        for sc in sorted_subconcepts:
            print(f"  - {sc}")
        
        # Check specifically for truncated help terms
        truncated = [sc for sc in all_subconcepts if sc in ['can', 'ask', 'help']]
        if truncated:
            print(f"\n⚠️  Found likely truncated subconcepts: {truncated}")
            print("These probably came from multi-word filenames that were cut off.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_help_images())