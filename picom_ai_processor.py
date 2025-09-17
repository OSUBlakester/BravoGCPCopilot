"""
PiCom Symbol AI Enhancement System
Adds Gemini Vision API endpoints to analyze PiCom images and generate additional tags
"""

import asyncio
import base64
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import google.generativeai as genai
from fastapi import HTTPException
from google.cloud import firestore, storage
from PIL import Image
import io

# Add these endpoints to your existing server.py file

# Configure Gemini (you'll need to set this up in your server.py)
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class PiComSymbolProcessor:
    def __init__(self):
        self.firestore_db = firestore.Client()
        self.storage_client = storage.Client()
        self.symbols_collection = "aac_symbols"
        self.bucket_name = "bravo-aac-symbols"  # You'll need to create this bucket
        
    def prepare_image_for_gemini(self, image_path: Path) -> str:
        """Convert image to base64 for Gemini API"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (optimize for Gemini)
                max_size = 1024
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to bytes
                buffer = io.BytesIO()
                img.save(buffer, format='PNG', optimize=True, quality=85)
                image_bytes = buffer.getvalue()
                
                return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            logging.error(f"Error preparing image {image_path}: {e}")
            return None

    async def analyze_image_with_gemini(self, image_data: str, current_tags: List[str], current_categories: List[str]) -> Dict:
        """Use Gemini Vision to enhance image metadata"""
        try:
            # Create analysis prompt
            prompt = f"""
            Analyze this AAC (Augmentative and Alternative Communication) symbol image.

            Current information extracted from filename:
            - Tags: {', '.join(current_tags)}
            - Categories: {', '.join(current_categories)}

            Please provide additional information to help AAC users find this symbol:

            1. EMOTIONS: What emotions are visible or could this image convey? (happy, sad, excited, etc.)
            2. ACTIONS: What actions, activities, or verbs does this show? (running, eating, playing, etc.)  
            3. OBJECTS: What objects, items, or things are visible? (ball, cup, book, etc.)
            4. PEOPLE: What types of people are shown? (child, adult, family, etc.)
            5. CONCEPTS: What abstract concepts could this represent? (love, time, help, etc.)
            6. USAGE: When might someone use this symbol in communication?
            7. SIMILAR_WORDS: What other words mean the same or similar thing?
            8. DIFFICULTY: Is this concept simple, intermediate, or complex for AAC users?
            9. AGE_SUITABILITY: Which age groups would find this most useful? (child, teen, adult, all)

            Respond in this exact JSON format:
            {{
                "emotions": ["emotion1", "emotion2"],
                "actions": ["action1", "action2"], 
                "objects": ["object1", "object2"],
                "people": ["person_type1", "person_type2"],
                "concepts": ["concept1", "concept2"],
                "usage_context": "When someone wants to communicate...",
                "similar_words": ["word1", "word2"],
                "difficulty": "simple",
                "age_groups": ["all"]
            }}

            Only include words that would genuinely help an AAC user find this symbol. Keep it focused and practical.
            """

            # Use Gemini Vision API
            model = genai.GenerativeModel('gemini-pro-vision')
            response = model.generate_content([
                prompt,
                {
                    'mime_type': 'image/png',
                    'data': image_data
                }
            ])

            # Parse JSON response
            try:
                ai_analysis = json.loads(response.text)
                return ai_analysis
            except json.JSONDecodeError:
                logging.error(f"Could not parse Gemini response as JSON: {response.text}")
                return self._create_fallback_analysis()

        except Exception as e:
            logging.error(f"Error in Gemini analysis: {e}")
            return self._create_fallback_analysis()

    def _create_fallback_analysis(self) -> Dict:
        """Fallback analysis if Gemini fails"""
        return {
            "emotions": [],
            "actions": [],
            "objects": [],
            "people": [],
            "concepts": [],
            "usage_context": "General communication",
            "similar_words": [],
            "difficulty": "simple",
            "age_groups": ["all"]
        }

    def combine_metadata(self, filename_data: Dict, ai_data: Dict) -> Dict:
        """Combine filename analysis with AI analysis"""
        # Merge all tags
        all_tags = set(filename_data.get('tags', []))
        
        # Add AI tags
        for category in ['emotions', 'actions', 'objects', 'people', 'concepts', 'similar_words']:
            if ai_data.get(category):
                all_tags.update(ai_data[category])

        # Enhanced categories
        enhanced_categories = filename_data.get('categories', []).copy()
        
        if ai_data.get('emotions'):
            enhanced_categories.append('emotions')
        if ai_data.get('actions'):
            enhanced_categories.append('actions')
        if ai_data.get('people'):
            enhanced_categories.append('people')
        if ai_data.get('objects'):
            enhanced_categories.append('objects')

        # Remove duplicates
        enhanced_categories = list(set(enhanced_categories))
        
        # Create symbol document
        symbol_doc = {
            'symbol_id': str(uuid.uuid4()),
            'filename': filename_data['filename'],
            'image_url': '',  # Will be set after upload
            'thumbnail_url': '',  # Will be generated
            
            # Core metadata
            'name': filename_data['description'],
            'description': filename_data['description'],
            'alt_text': f"AAC symbol showing {filename_data['description']}",
            
            # Categorization  
            'primary_category': enhanced_categories[0] if enhanced_categories else 'other',
            'categories': enhanced_categories,
            'tags': list(all_tags),
            'ai_tags': ai_data.get('emotions', []) + ai_data.get('actions', []) + ai_data.get('objects', []),
            'filename_tags': filename_data.get('tags', []),
            
            # Usage context
            'difficulty_level': ai_data.get('difficulty', 'simple'),
            'age_groups': ai_data.get('age_groups', ['all']),
            'usage_contexts': [ai_data.get('usage_context', 'General communication')],
            'related_concepts': ai_data.get('similar_words', []),
            
            # Search optimization
            'search_weight': len(all_tags) * (2 if ai_data.get('emotions') or ai_data.get('actions') else 1),
            'usage_frequency': 0,
            'last_used': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            
            # Source tracking
            'source': 'picom_cartoon',  # or 'picom_action' based on your collection
            'source_id': filename_data.get('image_id', ''),
            'processing_status': 'analyzed',
            
            # Keep AI analysis for reference
            'ai_analysis': ai_data,
            'filename_analysis': filename_data
        }
        
        return symbol_doc

    async def upload_image_to_storage(self, image_path: Path, symbol_id: str) -> tuple[str, str]:
        """Upload image to Cloud Storage and return URLs"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            
            # Original image
            image_blob_name = f"symbols/originals/{symbol_id}.png"
            image_blob = bucket.blob(image_blob_name)
            
            with open(image_path, 'rb') as image_file:
                image_blob.upload_from_file(image_file, content_type='image/png')
            
            image_url = f"gs://{self.bucket_name}/{image_blob_name}"
            
            # Create thumbnail (smaller version for UI)
            with Image.open(image_path) as img:
                img.thumbnail((128, 128), Image.Resampling.LANCZOS)
                
                thumbnail_buffer = io.BytesIO()
                img.save(thumbnail_buffer, format='PNG', optimize=True)
                thumbnail_buffer.seek(0)
                
                thumbnail_blob_name = f"symbols/thumbnails/{symbol_id}.png"
                thumbnail_blob = bucket.blob(thumbnail_blob_name)
                thumbnail_blob.upload_from_file(thumbnail_buffer, content_type='image/png')
                
                thumbnail_url = f"gs://{self.bucket_name}/{thumbnail_blob_name}"
            
            return image_url, thumbnail_url
            
        except Exception as e:
            logging.error(f"Error uploading image {image_path}: {e}")
            return "", ""

    async def save_symbol_to_firestore(self, symbol_doc: Dict) -> bool:
        """Save processed symbol to Firestore"""
        try:
            doc_ref = self.firestore_db.collection(self.symbols_collection).document(symbol_doc['symbol_id'])
            doc_ref.set(symbol_doc)
            return True
        except Exception as e:
            logging.error(f"Error saving symbol to Firestore: {e}")
            return False

# Add these endpoints to your server.py:

# @app.post("/api/symbols/process-picom-batch")
# async def process_picom_symbols_batch():
#     """Process a batch of PiCom images with AI enhancement"""
#     processor = PiComSymbolProcessor()
#     
#     # Load the analysis data
#     analysis_file = Path("picom_ready_for_ai_analysis.json")
#     if not analysis_file.exists():
#         raise HTTPException(status_code=404, detail="Analysis file not found. Run analysis first.")
#     
#     with open(analysis_file) as f:
#         analysis_data = json.load(f)
#     
#     # Process first 50 images as a test batch
#     images_to_process = analysis_data['images'][:50]
#     picom_dir = Path("/Users/blakethomas/Documents/BravoGCPCopilot/PiComImages")
#     
#     processed_count = 0
#     errors = []
#     
#     for image_data in images_to_process:
#         try:
#             image_path = picom_dir / image_data['filename']
#             if not image_path.exists():
#                 errors.append(f"Image not found: {image_data['filename']}")
#                 continue
#             
#             # Prepare image for Gemini
#             image_b64 = processor.prepare_image_for_gemini(image_path)
#             if not image_b64:
#                 errors.append(f"Could not process image: {image_data['filename']}")
#                 continue
#             
#             # AI analysis
#             ai_analysis = await processor.analyze_image_with_gemini(
#                 image_b64, 
#                 image_data['tags'], 
#                 image_data['categories']
#             )
#             
#             # Combine metadata
#             symbol_doc = processor.combine_metadata(image_data, ai_analysis)
#             
#             # Upload to Cloud Storage
#             image_url, thumbnail_url = await processor.upload_image_to_storage(image_path, symbol_doc['symbol_id'])
#             symbol_doc['image_url'] = image_url
#             symbol_doc['thumbnail_url'] = thumbnail_url
#             
#             # Save to Firestore
#             success = await processor.save_symbol_to_firestore(symbol_doc)
#             
#             if success:
#                 processed_count += 1
#                 logging.info(f"Processed symbol: {image_data['filename']}")
#             else:
#                 errors.append(f"Failed to save: {image_data['filename']}")
#                 
#             # Small delay to avoid rate limits
#             await asyncio.sleep(0.1)
#             
#         except Exception as e:
#             errors.append(f"Error processing {image_data['filename']}: {str(e)}")
#     
#     return {
#         "processed_count": processed_count,
#         "total_requested": len(images_to_process),
#         "errors": errors[:10],  # Limit error list
#         "error_count": len(errors)
#     }

# @app.get("/api/symbols/search")
# async def search_symbols(
#     query: str = "",
#     category: Optional[str] = None,
#     difficulty: Optional[str] = None,
#     age_group: Optional[str] = None,
#     limit: int = 20
# ):
#     """Search for AAC symbols"""
#     try:
#         symbols_ref = firestore_db.collection("aac_symbols")
#         
#         # Build query
#         if category:
#             symbols_ref = symbols_ref.where("categories", "array_contains", category)
#         if difficulty:
#             symbols_ref = symbols_ref.where("difficulty_level", "==", difficulty)
#         if age_group:
#             symbols_ref = symbols_ref.where("age_groups", "array_contains", age_group)
#             
#         # For text search, we'll need to implement a more sophisticated approach
#         # For now, let's get all matching symbols and filter client-side
#         symbols_ref = symbols_ref.order_by("search_weight", direction=firestore.Query.DESCENDING).limit(limit * 2)
#         
#         results = symbols_ref.stream()
#         symbols = []
#         
#         for doc in results:
#             symbol = doc.to_dict()
#             symbol['id'] = doc.id
#             
#             # Simple text matching
#             if query:
#                 query_lower = query.lower()
#                 match_score = 0
#                 
#                 # Check name/description
#                 if query_lower in symbol.get('name', '').lower():
#                     match_score += 10
#                 if query_lower in symbol.get('description', '').lower():
#                     match_score += 5
#                     
#                 # Check tags
#                 for tag in symbol.get('tags', []):
#                     if query_lower in tag.lower():
#                         match_score += 3
#                         
#                 if match_score > 0:
#                     symbol['match_score'] = match_score
#                     symbols.append(symbol)
#             else:
#                 symbols.append(symbol)
#                 
#         # Sort by match score if query provided
#         if query:
#             symbols.sort(key=lambda x: x.get('match_score', 0), reverse=True)
#             
#         return {
#             "symbols": symbols[:limit],
#             "total_found": len(symbols),
#             "query": query,
#             "filters": {
#                 "category": category,
#                 "difficulty": difficulty, 
#                 "age_group": age_group
#             }
#         }
#         
#     except Exception as e:
#         logging.error(f"Error searching symbols: {e}")
#         raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")