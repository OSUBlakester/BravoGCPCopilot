#!/usr/bin/env python3
"""
Diagnostic script to examine image_url patterns in Firestore
This helps understand how filenames are stored and how to match them properly
"""

import asyncio
import firebase_admin
from firebase_admin import credentials, firestore
import config
import re
from collections import defaultdict

class FirestoreImageAnalyzer:
    def __init__(self):
        self.firestore_db = None
        self.setup_clients()
    
    def setup_clients(self):
        """Initialize Firebase and Firestore clients"""
        try:
            if not firebase_admin._apps:
                service_account_path = config.CONFIG.get('service_account_key_path')
                if service_account_path:
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()
            
            self.firestore_db = firestore.Client(project=config.CONFIG.get('gcp_project_id'))
            print("✅ Connected to Firestore")
            
        except Exception as e:
            print(f"❌ Error initializing clients: {e}")
            raise
    
    async def analyze_image_urls(self):
        """Analyze image_url patterns in Firestore"""
        print("🔍 Analyzing image_url patterns in Firestore...")
        
        # Get a sample of bravo_images records
        query = (self.firestore_db.collection("aac_images")
                .where("source", "==", "bravo_images")
                .limit(20))  # Just get first 20 for analysis
        
        docs = await asyncio.to_thread(query.get)
        
        print(f"\n📊 Found {len(docs)} sample records:")
        print("="*80)
        
        patterns = defaultdict(int)
        
        for i, doc in enumerate(docs):
            data = doc.to_dict()
            concept = data.get('concept', 'unknown')
            subconcept = data.get('subconcept', 'unknown')
            image_url = data.get('image_url', '')
            
            print(f"{i+1:2d}. Concept: {concept}")
            print(f"    Subconcept: {subconcept}")
            print(f"    Image URL: {image_url}")
            
            # Extract filename from URL
            if image_url:
                filename = image_url.split('/')[-1]
                print(f"    Filename: {filename}")
                
                # Analyze filename pattern
                timestamp_match = re.search(r'(\d{8}_\d{6})', filename)
                if timestamp_match:
                    print(f"    Timestamp: {timestamp_match.group(1)}")
                    patterns['has_timestamp'] += 1
                else:
                    patterns['no_timestamp'] += 1
                
                # Check if concept/subconcept appear in filename
                if concept in filename:
                    patterns['concept_in_filename'] += 1
                if subconcept in filename:
                    patterns['subconcept_in_filename'] += 1
            
            print()
        
        print("📈 Pattern Analysis:")
        print("="*40)
        for pattern, count in patterns.items():
            print(f"  {pattern}: {count}")
        
        return docs
    
    async def search_for_specific_files(self):
        """Search for the specific files in Delete_Images folder"""
        print("\n🔍 Searching for specific files from Delete_Images folder...")
        
        # These are the files you're trying to delete
        target_files = [
            'less_20250926_200905.png',
            'far_20250927_110350.png', 
            'low_20250927_110336.png',
            'near_20250927_110343.png',
            'high_20250927_110328.png'
        ]
        
        for filename in target_files:
            print(f"\n🎯 Searching for: {filename}")
            
            # Search strategies
            found = False
            
            # Strategy 1: Exact filename match
            query = self.firestore_db.collection("aac_images").where("source", "==", "bravo_images")
            docs = await asyncio.to_thread(query.get)
            
            for doc in docs:
                data = doc.to_dict()
                image_url = data.get('image_url', '')
                if filename in image_url:
                    print(f"  ✅ EXACT MATCH: {image_url}")
                    print(f"     Concept: {data.get('concept')}, Subconcept: {data.get('subconcept')}")
                    found = True
            
            # Strategy 2: Timestamp match
            if not found:
                timestamp_match = re.search(r'(\d{8}_\d{6})', filename)
                if timestamp_match:
                    timestamp = timestamp_match.group(1)
                    print(f"  🕒 Searching by timestamp: {timestamp}")
                    
                    for doc in docs:
                        data = doc.to_dict()
                        image_url = data.get('image_url', '')
                        if timestamp in image_url:
                            print(f"    📅 TIMESTAMP MATCH: {image_url}")
                            print(f"       Concept: {data.get('concept')}, Subconcept: {data.get('subconcept')}")
                            found = True
            
            # Strategy 3: Subconcept match
            if not found:
                subconcept = filename.split('_')[0]  # Extract first part
                print(f"  🔍 Searching by subconcept: {subconcept}")
                
                for doc in docs:
                    data = doc.to_dict()
                    if data.get('subconcept') == subconcept:
                        print(f"    🎯 SUBCONCEPT MATCH: {data.get('image_url')}")
                        print(f"       Concept: {data.get('concept')}, Subconcept: {data.get('subconcept')}")
                        found = True
            
            if not found:
                print(f"  ❌ No matches found for {filename}")
    
    async def run_analysis(self):
        """Run the complete analysis"""
        await self.analyze_image_urls()
        await self.search_for_specific_files()

async def main():
    analyzer = FirestoreImageAnalyzer()
    await analyzer.run_analysis()

if __name__ == "__main__":
    asyncio.run(main())