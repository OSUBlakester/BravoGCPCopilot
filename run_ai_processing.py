#!/usr/bin/env python3
"""
Script to run AI tagging on PiCom symbols locally
This bypasses the authentication requirements of the web endpoints
"""

import os
import sys
import asyncio
import json
from pathlib import Path
import logging

# Add the current directory to Python path for imports
sys.path.insert(0, '/Users/blakethomas/Documents/BravoGCPCopilot')

# Setup logging
logging.basicConfig(level=logging.INFO)

async def run_ai_symbol_processing():
    """Run the AI symbol processing pipeline"""
    try:
        # Import server functions
        from server import initialize_firebase, get_gemini_api_key, generate_image_tags
        import google.generativeai as genai
        from google.cloud import firestore
        
        print("🚀 Starting AI Symbol Processing Pipeline")
        print("=" * 50)
        
        # Initialize Firebase
        initialize_firebase()
        db = firestore.Client()
        
        # Step 1: Get a few symbols that need AI processing
        print("📋 Step 1: Finding symbols to process...")
        symbols_ref = db.collection('picom_symbols')
        query = symbols_ref.where('processing_status', '==', 'processed_without_ai').limit(5)
        symbols = query.stream()
        
        symbols_to_process = []
        for doc in symbols:
            symbol_data = doc.to_dict()
            symbol_data['id'] = doc.id
            symbols_to_process.append(symbol_data)
        
        print(f"Found {len(symbols_to_process)} symbols to process")
        
        if not symbols_to_process:
            print("ℹ️ No symbols found that need AI processing")
            return
            
        # Step 2: Process each symbol with AI
        print("\n🤖 Step 2: Processing symbols with AI...")
        
        # Configure Gemini
        api_key = await get_gemini_api_key()
        genai.configure(api_key=api_key)
        
        processed_count = 0
        for symbol in symbols_to_process:
            try:
                print(f"Processing symbol: {symbol['name']}")
                
                # Generate AI tags for this symbol
                ai_tags = await generate_image_tags(
                    symbol['image_url'],
                    symbol.get('primary_category', 'other'),
                    symbol['name']
                )
                
                # Combine original tags with AI tags
                original_tags = symbol.get('tags', [])
                combined_tags = list(set(original_tags + ai_tags))
                
                # Update the symbol in Firestore
                doc_ref = db.collection('picom_symbols').document(symbol['id'])
                doc_ref.update({
                    'tags': combined_tags,
                    'processing_status': 'processed_with_ai',
                    'ai_tags': ai_tags,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                
                processed_count += 1
                print(f"✅ Updated {symbol['name']} with AI tags: {ai_tags}")
                
            except Exception as e:
                print(f"❌ Error processing {symbol['name']}: {str(e)}")
                continue
        
        print(f"\n🎉 AI processing completed! Processed {processed_count} symbols")
        print("Now test searching for 'pet', 'smile', etc. - they should find relevant symbols!")
        
    except Exception as e:
        print(f"❌ Error during AI processing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_ai_symbol_processing())