#!/usr/bin/env python3
"""
Extended Symbol Import Pipeline for Bravo AAC
Adds new symbol sources to expand the database beyond PiCom symbols
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import requests
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SymbolImporter:
    """Import symbols from various sources into Bravo AAC database"""
    
    def __init__(self):
        self.descriptive_words = [
            # Missing positive descriptive words
            "fantastic", "awesome", "amazing", "incredible", "wonderful", 
            "brilliant", "excellent", "outstanding", "magnificent", "superb",
            "marvelous", "terrific", "fabulous", "spectacular", "phenomenal",
            
            # Enhanced emotional range
            "ecstatic", "delighted", "thrilled", "overjoyed", "euphoric",
            "content", "peaceful", "serene", "calm", "relaxed",
            "anxious", "worried", "concerned", "nervous", "stressed",
            "frustrated", "annoyed", "irritated", "disappointed", "overwhelmed",
            
            # Activity descriptors
            "energetic", "dynamic", "active", "lively", "vibrant",
            "gentle", "smooth", "rough", "intense", "mild",
            "creative", "artistic", "musical", "athletic", "academic",
            
            # Social descriptors  
            "friendly", "kind", "generous", "helpful", "supportive",
            "social", "outgoing", "shy", "quiet", "confident"
        ]
        
    def analyze_missing_words(self) -> List[str]:
        """Analyze what descriptive words are missing from current database"""
        logger.info("Analyzing missing descriptive words...")
        
        # This would connect to your Firestore to check existing tags
        # For now, return the full list as candidates
        return self.descriptive_words
    
    def fetch_openmoji_symbols(self, words_needed: List[str]) -> List[Dict]:
        """Fetch OpenMoji symbols for missing words"""
        logger.info(f"Fetching OpenMoji symbols for {len(words_needed)} words...")
        
        symbols = []
        
        # OpenMoji API endpoint (if available) or download their JSON catalog
        try:
            # Download OpenMoji data catalog
            catalog_url = "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/data/openmoji.csv"
            response = requests.get(catalog_url)
            
            # Parse and filter for relevant symbols
            # This is a simplified example - you'd need to implement CSV parsing
            # and keyword matching logic
            
            for word in words_needed[:10]:  # Limit for initial test
                symbol_data = {
                    "name": word,
                    "source": "openmoji",
                    "description": f"OpenMoji symbol for {word}",
                    "tags": [word, "emotion" if word in ["fantastic", "awesome"] else "descriptor"],
                    "categories": ["emotions" if word in ["fantastic", "awesome"] else "descriptors"],
                    "age_groups": ["all"],
                    "difficulty_level": "simple",
                    "search_weight": 2,
                    "source_url": f"https://openmoji.org/library/emoji-{word}/",
                    "processing_status": "needs_import",
                    "created_at": datetime.utcnow().isoformat()
                }
                symbols.append(symbol_data)
                
        except Exception as e:
            logger.error(f"Error fetching OpenMoji symbols: {e}")
            
        logger.info(f"Found {len(symbols)} candidate symbols")
        return symbols
    
    def prepare_import_data(self, symbols: List[Dict]) -> Dict:
        """Prepare symbol data for import into existing pipeline"""
        
        import_data = {
            "source": "extended_symbols",
            "created_at": datetime.utcnow().isoformat(),
            "total_symbols": len(symbols),
            "symbols": symbols,
            "processing_instructions": {
                "batch_size": 25,
                "requires_ai_enhancement": True,
                "target_collection": "aac_symbols"
            }
        }
        
        # Save to file for processing
        output_file = "extended_symbols_import.json"
        with open(output_file, 'w') as f:
            json.dump(import_data, f, indent=2)
            
        logger.info(f"Import data saved to {output_file}")
        return import_data
    
    async def run_import_pipeline(self):
        """Run the complete import pipeline"""
        logger.info("🚀 Starting Extended Symbol Import Pipeline")
        
        # Step 1: Analyze missing words
        missing_words = self.analyze_missing_words()
        logger.info(f"Found {len(missing_words)} descriptive words to add")
        
        # Step 2: Fetch symbols from sources
        new_symbols = self.fetch_openmoji_symbols(missing_words)
        
        # Step 3: Prepare for import
        import_data = self.prepare_import_data(new_symbols)
        
        logger.info("✅ Extended symbol import pipeline complete")
        logger.info(f"📁 Import file created: extended_symbols_import.json")
        logger.info(f"🎯 Ready to import {len(new_symbols)} new symbols")
        
        return import_data

async def main():
    """Main function to run the import pipeline"""
    importer = SymbolImporter()
    await importer.run_import_pipeline()
    
    print("\n🎯 Next Steps:")
    print("1. Review the generated 'extended_symbols_import.json' file")
    print("2. Modify your existing process-batch endpoint to handle extended symbols")
    print("3. Import symbols using your admin interface")
    print("4. Test with LLM-generated content for better matching")

if __name__ == "__main__":
    asyncio.run(main())