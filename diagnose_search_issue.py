#!/usr/bin/env python3
"""
Diagnostic script to check what happened to image search functionality
after the repair process.
"""

import asyncio
import sys
from google.cloud import firestore
from datetime import datetime, timezone
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SearchDiagnostic:
    def __init__(self):
        self.firestore_db = firestore.Client()
    
    async def check_basic_search_terms(self):
        """Check if basic search terms are still findable"""
        basic_terms = ["hello", "good", "see", "happy", "time", "great", "wonderful", "joy", "chat", "talking"]
        
        logger.info("🔍 Checking basic search terms...")
        
        for term in basic_terms:
            logger.info(f"\n--- Searching for '{term}' ---")
            
            # Search in tags
            tag_query = self.firestore_db.collection("aac_images").where("tags", "array_contains", term)
            tag_docs = await asyncio.to_thread(tag_query.limit(5).get)
            
            logger.info(f"Found {len(tag_docs)} images with '{term}' in tags")
            for doc in tag_docs:
                data = doc.to_dict()
                logger.info(f"  📷 {data.get('concept', '')}/{data.get('subconcept', '')} - tags: {data.get('tags', [])[:5]}")
            
            # Search in subconcepts
            subconcept_query = self.firestore_db.collection("aac_images").where("subconcept", "==", term)
            subconcept_docs = await asyncio.to_thread(subconcept_query.limit(3).get)
            
            logger.info(f"Found {len(subconcept_docs)} images with subconcept = '{term}'")
            for doc in subconcept_docs:
                data = doc.to_dict()
                logger.info(f"  📷 {data.get('concept', '')}/{data.get('subconcept', '')} - tags: {data.get('tags', [])[:5]}")
    
    async def check_repair_impact(self):
        """Check what was changed by the repair process"""
        logger.info("\n🔧 Checking repair process impact...")
        
        # Find images that were repaired
        repaired_query = self.firestore_db.collection("aac_images").where("updated_by", "==", "repair_script_v2")
        repaired_docs = await asyncio.to_thread(repaired_query.limit(10).get)
        
        logger.info(f"Found {len(repaired_docs)} recently repaired images (showing first 10):")
        
        for doc in repaired_docs:
            data = doc.to_dict()
            repair_info = data.get('repair_info', {})
            original_subconcept = repair_info.get('original_subconcept', 'unknown')
            current_subconcept = data.get('subconcept', 'unknown')
            
            logger.info(f"  📷 {data.get('concept', '')}: '{original_subconcept}' → '{current_subconcept}'")
            logger.info(f"     Tags: {data.get('tags', [])[:7]}")
    
    async def check_specific_problem_cases(self):
        """Check specific cases that might be causing search issues"""
        logger.info("\n🎯 Checking specific problem cases...")
        
        # Check if there are images with very long subconcepts
        all_query = self.firestore_db.collection("aac_images").where("source", "==", "bravo_images")
        all_docs = await asyncio.to_thread(all_query.limit(50).get)
        
        long_subconcepts = []
        batch_prefixed = []
        
        for doc in all_docs:
            data = doc.to_dict()
            subconcept = data.get('subconcept', '')
            
            if len(subconcept.split('_')) > 3:
                long_subconcepts.append((subconcept, data.get('concept', '')))
            
            if subconcept.startswith(('batch_008', 'batch_009')):
                batch_prefixed.append((subconcept, data.get('concept', '')))
        
        logger.info(f"Found {len(long_subconcepts)} images with long subconcepts (>3 parts):")
        for subconcept, concept in long_subconcepts[:5]:
            logger.info(f"  📷 {concept}/{subconcept}")
        
        logger.info(f"Found {len(batch_prefixed)} images still with batch prefixes:")
        for subconcept, concept in batch_prefixed[:5]:
            logger.info(f"  📷 {concept}/{subconcept}")
    
    async def check_tag_structure(self):
        """Check if tag structure is correct"""
        logger.info("\n🏷️ Checking tag structure...")
        
        # Get some random images to check tag quality
        query = self.firestore_db.collection("aac_images").where("source", "==", "bravo_images")
        docs = await asyncio.to_thread(query.limit(10).get)
        
        for doc in docs:
            data = doc.to_dict()
            tags = data.get('tags', [])
            subconcept = data.get('subconcept', '')
            
            logger.info(f"📷 {data.get('concept', '')}/{subconcept}")
            logger.info(f"   Tags ({len(tags)}): {tags}")
            
            # Check if first tag matches searchable term
            if tags and subconcept:
                first_tag = tags[0].lower()
                searchable_term = subconcept.split('_')[-1].lower() if '_' in subconcept else subconcept.lower()
                
                if first_tag != searchable_term:
                    logger.warning(f"   ⚠️  First tag '{first_tag}' doesn't match searchable term '{searchable_term}'")

async def main():
    diagnostic = SearchDiagnostic()
    
    logger.info("🚀 Starting search functionality diagnostic...")
    
    await diagnostic.check_basic_search_terms()
    await diagnostic.check_repair_impact()
    await diagnostic.check_specific_problem_cases()
    await diagnostic.check_tag_structure()
    
    logger.info("\n✅ Diagnostic complete!")

if __name__ == "__main__":
    asyncio.run(main())