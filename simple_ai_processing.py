#!/usr/bin/env python3
"""
Simplified AI tagging script for PiCom symbols
"""

import os
import asyncio
import logging
from typing import List

# Setup environment - use application default credentials
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/blakethomas/Documents/BravoGCPCopilot/bravo-dev-465400-acd39b344c01.json'
os.environ['GCP_PROJECT_ID'] = 'bravo-dev-465400'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'bravo-dev-465400'

# Setup logging
logging.basicConfig(level=logging.INFO)

async def get_gemini_api_key():
    """Get Gemini API key from Secret Manager"""
    try:
        from google.cloud import secretmanager
        
        client = secretmanager.SecretManagerServiceClient()
        project_id = "bravo-dev-465400"
        secret_id = "GEMINI_API_KEY"
        
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error getting API key: {e}")
        return None

async def generate_ai_tags(image_url: str, concept: str, subconcept: str) -> List[str]:
    """Generate AI tags for a symbol using Gemini"""
    try:
        import google.generativeai as genai
        from PIL import Image
        import requests
        from io import BytesIO
        
        api_key = await get_gemini_api_key()
        if not api_key:
            return []
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Download and prepare image
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        
        prompt = f"""
        Analyze this image that represents the concept "{subconcept}" from the category "{concept}".
        
        Generate 8-12 relevant tags for AAC (Augmentative and Alternative Communication) purposes.
        
        Requirements:
        - Include the main concept and subconcept
        - Add descriptive words about appearance, function, context
        - Use simple, common words that AAC users might search for
        - Include both specific and general terms
        - Focus on communication-relevant aspects
        - For animals, include words like "pet", "animal" if applicable
        - For emotions, include synonyms like "happy", "joy", "cheerful" for smile
        
        Return only the tags, separated by commas, no other text.
        
        Example for a dog image: dog, pet, animal, canine, puppy, companion, furry, four-legged
        Example for a smile: smile, happy, joy, cheerful, grin, pleased, content, emotion
        """
        
        result = model.generate_content([prompt, img])
        tags_text = result.text.strip()
        
        # Clean and parse tags
        tags = [tag.strip().lower() for tag in tags_text.split(',')]
        tags = [tag for tag in tags if tag and len(tag) > 1]  # Filter out empty or single char tags
        
        return tags[:12]  # Limit to 12 tags
        
    except Exception as e:
        print(f"Error generating AI tags: {e}")
        return []

async def process_symbols():
    """Process symbols with AI tagging"""
    try:
        from google.cloud import firestore
        
        print("🚀 Starting AI Symbol Processing")
        print("=" * 40)
        
        # Initialize Firestore
        db = firestore.Client()
        
        # Get symbols to process
        print("📋 Finding symbols to process...")
        symbols_ref = db.collection('picom_symbols')
        query = symbols_ref.where('processing_status', '==', 'processed_without_ai').limit(10)
        docs = query.stream()
        
        symbols_to_process = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            symbols_to_process.append(data)
        
        print(f"Found {len(symbols_to_process)} symbols to process")
        
        if not symbols_to_process:
            print("ℹ️ No symbols found that need AI processing")
            # Let's check a few symbols manually
            all_docs = symbols_ref.limit(5).stream()
            for doc in all_docs:
                data = doc.to_dict()
                print(f"Sample symbol: {data.get('name')} - status: {data.get('processing_status')}")
            return
            
        # Process symbols
        processed = 0
        for symbol in symbols_to_process:
            try:
                name = symbol.get('name', 'unknown')
                category = symbol.get('primary_category', 'other') 
                image_url = symbol.get('image_url', '')
                
                print(f"🤖 Processing: {name} ({category})")
                
                # Generate AI tags
                ai_tags = await generate_ai_tags(image_url, category, name)
                
                if ai_tags:
                    # Combine with existing tags
                    original_tags = symbol.get('tags', [])
                    combined_tags = list(set(original_tags + ai_tags))
                    
                    # Update in Firestore
                    doc_ref = db.collection('picom_symbols').document(symbol['id'])
                    doc_ref.update({
                        'tags': combined_tags,
                        'ai_tags': ai_tags,
                        'processing_status': 'processed_with_ai',
                        'updated_at': firestore.SERVER_TIMESTAMP
                    })
                    
                    print(f"✅ Added AI tags: {', '.join(ai_tags)}")
                    processed += 1
                else:
                    print(f"⚠️ No AI tags generated for {name}")
                    
            except Exception as e:
                print(f"❌ Error processing {name}: {e}")
                continue
                
        print(f"\n🎉 Processing complete! Updated {processed} symbols with AI tags")
        print("Test searches for 'pet', 'smile', etc. should now work!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(process_symbols())