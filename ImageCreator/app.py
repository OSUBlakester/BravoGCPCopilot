
from flask import Flask, request, jsonify
from flask_cors import CORS
import random

# GCP imports
import os
import requests
import base64
from google.cloud import firestore, storage, secretmanager, aiplatform

# Set up GCP credentials and clients
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), "bravo-dev-465400-0950ffdbe03f.json")
FIRESTORE_PROJECT_ID = "bravo-dev-465400"
BUCKET_NAME = "brimages"
GEMINI_TEXT_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

# Initialize AI Platform
aiplatform.init(project=FIRESTORE_PROJECT_ID, location="us-central1")

db = firestore.Client(project=FIRESTORE_PROJECT_ID)
storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)
secret_client = secretmanager.SecretManagerServiceClient()

# Get Gemini API key from Secret Manager (for text model)
def get_gemini_api_key():
    try:
        secret_name = f"projects/{FIRESTORE_PROJECT_ID}/secrets/bravo-google-api-key/versions/latest"
        response = secret_client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Warning: Could not access Secret Manager: {e}")
        # Fallback: Check environment variable
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key:
            return api_key
        else:
            print("Warning: No Gemini API key found. Image tagging will be disabled.")
            return None

GEMINI_API_KEY = get_gemini_api_key()

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains on all routes

# Call Gemini AI Platform for image generation with retry logic
def generate_image_with_gemini(prompt, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            print(f"Attempting to generate image for prompt: {prompt} (attempt {attempt + 1}/{max_retries + 1})")
            
            # Get access token using service account
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
            import json
            
            # Load service account credentials
            credentials_path = os.path.join(os.path.dirname(__file__), "bravo-dev-465400-0950ffdbe03f.json")
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            
            # Refresh credentials to get access token
            credentials.refresh(Request())
            access_token = credentials.token
            print(f"Successfully obtained access token (attempt {attempt + 1})")
            
            # Use Vertex AI Imagen API
            endpoint = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{FIRESTORE_PROJECT_ID}/locations/us-central1/publishers/google/models/imagegeneration@006:predict"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            # Enhanced prompt for Apple Memoji style - very specific about the aesthetic
            enhanced_prompt = f"""Create an Apple Memoji-style illustration of {prompt}. 
            Style requirements:
            - Clean, minimalist 3D cartoon aesthetic exactly like Apple Memojis
            - Rounded, soft geometric shapes with gentle curves
            - Bright, vibrant colors with subtle gradients
            - Simple facial features: large expressive eyes, minimal nose, friendly smile
            - Smooth, matte finish appearance (no harsh shadows or reflections)
            - White or very light background
            - Characters should have the distinctive rounded, egg-shaped head proportions of Memojis
            - Simple, clean clothing with solid colors or basic patterns
            - Cheerful, friendly expression
            - High contrast between character and background for AAC clarity
            - Single character or simple family group composition
            - Square aspect ratio, centered composition
            
            Subject: {prompt}
            Make it look exactly like it could be an official Apple Memoji."""
            
            data = {
                "instances": [{
                    "prompt": enhanced_prompt
                }],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "1:1",
                    "safetyFilterLevel": "block_some",
                    "personGeneration": "allow_adult"
                }
            }
            
            response = requests.post(endpoint, headers=headers, json=data, timeout=120)
            print(f"Vertex AI response status: {response.status_code} (attempt {attempt + 1})")
            
            if response.status_code != 200:
                print(f"Error response (attempt {attempt + 1}): {response.text}")
                if attempt < max_retries:
                    print(f"Retrying in 2 seconds...")
                    import time
                    time.sleep(2)
                    continue
                return None
                
            result = response.json()
            print(f"API Response structure: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            # Extract image data from response
            if 'predictions' in result and len(result['predictions']) > 0:
                prediction = result['predictions'][0]
                print(f"Prediction keys: {list(prediction.keys()) if isinstance(prediction, dict) else 'Not a dict'}")
                
                # Check different possible response formats
                if 'bytesBase64Encoded' in prediction:
                    print(f"Found image in bytesBase64Encoded (attempt {attempt + 1})")
                    return prediction['bytesBase64Encoded']
                elif 'generated_image' in prediction:
                    print(f"Found image in generated_image (attempt {attempt + 1})")
                    return prediction['generated_image'].get('bytesBase64Encoded')
                elif 'image' in prediction:
                    print(f"Found image in image field (attempt {attempt + 1})")
                    return prediction['image']
                else:
                    print(f"Unexpected prediction format (attempt {attempt + 1}): {prediction}")
            else:
                print(f"Empty or no predictions in response (attempt {attempt + 1})")
            
            if attempt < max_retries:
                print(f"No valid image data found, retrying in 2 seconds...")
                import time
                time.sleep(2)
                continue
                
            print("No valid image data found in Vertex AI response after all retries")
            return None
            
        except Exception as e:
            print(f"Error generating image with Gemini (attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                print(f"Retrying in 3 seconds...")
                import time
                time.sleep(3)
                continue
            import traceback
            traceback.print_exc()
            return None
    
    return None

# AI-powered image analysis using Gemini Vision
def analyze_image_with_gemini(image_base64):
    if not GEMINI_API_KEY:
        return ["ai-generated", "memoji-style", "communication-aid"]
    
    try:
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Create a detailed prompt for image analysis
        analysis_prompt = """Analyze this image and generate 8-12 descriptive tags that would be useful for searching and categorizing AAC (Augmentative and Alternative Communication) images.

Focus on:
- What people/characters are shown (mother, father, child, etc.)
- Emotions or expressions (happy, smiling, calm, etc.)
- Actions or activities (hugging, playing, eating, etc.)  
- Objects or items visible (toys, food, furniture, etc.)
- Settings or locations (home, outdoors, kitchen, etc.)
- Colors (if distinctive)
- Style characteristics (cartoon, memoji, 3d, etc.)

Return only comma-separated tags, no explanations."""

        data = {
            "contents": [{
                "parts": [
                    {
                        "text": analysis_prompt
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_base64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 200,
            }
        }
        
        url = f"{GEMINI_TEXT_ENDPOINT}?key={GEMINI_API_KEY}"
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Parse the tags and break down compound tags
                tags = []
                for tag in generated_text.split(','):
                    tag = tag.strip().lower()
                    if tag and len(tag) > 1:
                        # Add the full tag
                        tags.append(tag)
                        
                        # Also add individual words from compound tags
                        # Skip common connecting words
                        skip_words = {'and', 'or', 'with', 'in', 'on', 'at', 'the', 'a', 'an', 'of'}
                        words = tag.split()
                        if len(words) > 1:  # Only break down multi-word tags
                            for word in words:
                                word = word.strip()
                                if word and len(word) > 2 and word not in skip_words:
                                    if word not in tags:  # Avoid duplicates
                                        tags.append(word)
                
                # Add some default AAC tags
                default_tags = ["aac", "communication", "memoji-style", "ai-generated"]
                for tag in default_tags:
                    if tag not in tags:
                        tags.append(tag)
                
                print(f"AI analyzed image and generated {len(tags)} tags: {tags}")
                return tags[:15]  # Limit to 15 tags max
            else:
                print("No valid response from Gemini Vision API")
                return ["aac", "communication", "ai-generated", "memoji-style"]
        else:
            print(f"Gemini Vision API error: {response.status_code} - {response.text}")
            return ["aac", "communication", "ai-generated", "memoji-style"]
            
    except Exception as e:
        print(f"Error analyzing image with Gemini Vision: {e}")
        return ["aac", "communication", "ai-generated", "memoji-style"]

# Save selected images to Cloud Storage and Firestore
@app.route('/save_images', methods=['POST'])
def api_save_images():
    try:
        data = request.json
        images_to_save = data.get('images', [])
        
        print(f"Received request to save {len(images_to_save)} images")
        
        saved_count = 0
        
        for i, image_data in enumerate(images_to_save):
            try:
                image_base64 = image_data.get('image', '')
                prompt = image_data.get('prompt', '')
                concept = image_data.get('concept', '')
                
                # Skip if it's a placeholder/fallback image
                if 'data:image/svg+xml' in image_base64 or 'Gemini Failed' in image_base64:
                    print(f"Skipping placeholder image {i+1}")
                    continue
                
                # Extract base64 data from data URL
                if 'data:image/png;base64,' in image_base64:
                    clean_base64 = image_base64.split('data:image/png;base64,')[1]
                else:
                    print(f"Invalid image format for image {i+1}")
                    continue
                
                # Analyze image with AI to get descriptive tags
                print(f"Analyzing image {i+1} with AI...")
                ai_tags = analyze_image_with_gemini(clean_base64)
                
                # Generate unique filename
                import uuid
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_id = str(uuid.uuid4())[:8]
                filename = f"aac_image_{timestamp}_{unique_id}.png"
                
                # Save to Cloud Storage
                print(f"Saving image {i+1} to Cloud Storage as {filename}...")
                blob = bucket.blob(f"images/{filename}")
                
                # Convert base64 to bytes
                import base64
                image_bytes = base64.b64decode(clean_base64)
                
                blob.upload_from_string(
                    image_bytes,
                    content_type='image/png'
                )
                
                # Get the public URL (bucket has uniform bucket-level access)
                image_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob.name}"
                
                # Save metadata to Firestore
                doc_data = {
                    'filename': filename,
                    'image_url': image_url,
                    'prompt': prompt,
                    'concept': concept,
                    'ai_tags': ai_tags,
                    'created_at': datetime.now(),
                    'file_size': len(image_bytes),
                    'mime_type': 'image/png'
                }
                
                doc_ref = db.collection('aac_images').document(unique_id)
                doc_ref.set(doc_data)
                
                print(f"Successfully saved image {i+1}: {filename} with {len(ai_tags)} AI tags")
                saved_count += 1
                
            except Exception as e:
                print(f"Error saving image {i+1}: {e}")
                continue
        
        return jsonify({
            'status': 'success',
            'saved_count': saved_count,
            'total_requested': len(images_to_save),
            'message': f'Successfully saved {saved_count} images to Cloud Storage with AI-generated tags'
        })
    
    except Exception as e:
        print(f"Error in api_save_images: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# AI-powered prompt generation using Gemini
def generate_prompts_with_gemini(concept, num_variations):
    if not GEMINI_API_KEY:
        print("No Gemini API key found, using fallback prompts")
        return generate_prompts_fallback(concept, num_variations)
    
    try:
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Enhanced prompt for generating AAC-suitable image prompts focused on subconcepts
        generation_prompt = f"""Generate {num_variations} simple subconcept prompts for AAC (Augmentative and Alternative Communication) based on the concept "{concept}".

IMPORTANT: Focus on SUBCONCEPTS and RELATED ITEMS, not actions or emotions.

For "{concept}", think of the main categories, people, or objects that belong to this concept:
- If "{concept}" is "family" → subconcepts: mother, father, sister, brother, grandmother, grandfather, baby, parents
- If "{concept}" is "food" → subconcepts: apple, bread, milk, sandwich, pizza, banana, water, juice
- If "{concept}" is "animals" → subconcepts: dog, cat, bird, fish, horse, cow, lion, elephant
- If "{concept}" is "home" → subconcepts: bed, chair, table, door, window, kitchen, bathroom, bedroom

Requirements:
- Generate simple, single-word or two-word subconcepts
- Focus on nouns (people, objects, places) rather than actions
- Make each subconcept clearly recognizable and different
- Suitable for Apple Memoji-style illustrations
- Keep it family-friendly and clear for communication

Format: Return exactly {num_variations} simple prompts, one per line, without numbers or bullets.

Examples for "family":
mother
father  
sister
brother
grandmother

Now generate {num_variations} subconcept prompts for "{concept}":]"""

        data = {
            "contents": [{
                "parts": [{
                    "text": generation_prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        url = f"{GEMINI_TEXT_ENDPOINT}?key={GEMINI_API_KEY}"
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Parse the generated prompts
                prompts = []
                for line in generated_text.strip().split('\n'):
                    line = line.strip()
                    if line and not line.startswith('*') and not line.startswith('-'):
                        # Clean up any numbering or formatting
                        cleaned_line = line
                        if '. ' in line and line[0].isdigit():
                            cleaned_line = '. '.join(line.split('. ')[1:])
                        prompts.append(cleaned_line)
                
                # Ensure we have the right number of prompts
                if len(prompts) >= num_variations:
                    print(f"Successfully generated {len(prompts[:num_variations])} AI prompts for '{concept}'")
                    return prompts[:num_variations]
                else:
                    print(f"Generated {len(prompts)} prompts, padding with fallbacks")
                    # Pad with fallback prompts if needed
                    fallback_prompts = generate_prompts_fallback(concept, num_variations - len(prompts))
                    return prompts + fallback_prompts
            else:
                print("No valid response from Gemini text API")
                return generate_prompts_fallback(concept, num_variations)
        else:
            print(f"Gemini text API error: {response.status_code} - {response.text}")
            return generate_prompts_fallback(concept, num_variations)
            
    except Exception as e:
        print(f"Error generating prompts with Gemini: {e}")
        return generate_prompts_fallback(concept, num_variations)

# Fallback prompt variations for a concept - focused on subconcepts
def generate_prompts_fallback(concept, num_variations):
    # Create subconcept-focused prompts based on the main concept
    base_variations = []
    
    # Add concept-specific subconcepts
    concept_lower = concept.lower()
    
    if concept_lower in ['family', 'home', 'love', 'people']:
        base_variations = [
            "mother", "father", "sister", "brother", "grandmother", 
            "grandfather", "baby", "parents", "children", "family"
        ]
    elif concept_lower in ['food', 'eat', 'hungry', 'kitchen', 'meal']:
        base_variations = [
            "apple", "bread", "milk", "water", "sandwich", 
            "pizza", "banana", "juice", "cookie", "pasta"
        ]
    elif concept_lower in ['animals', 'pets', 'zoo']:
        base_variations = [
            "dog", "cat", "bird", "fish", "horse", 
            "cow", "pig", "chicken", "rabbit", "bear"
        ]
    elif concept_lower in ['toys', 'play', 'games']:
        base_variations = [
            "ball", "doll", "car", "book", "blocks", 
            "puzzle", "bike", "swing", "slide", "teddy bear"
        ]
    elif concept_lower in ['clothes', 'clothing', 'wear']:
        base_variations = [
            "shirt", "pants", "shoes", "hat", "dress", 
            "socks", "coat", "glasses", "scarf", "mittens"
        ]
    elif concept_lower in ['school', 'learning', 'education']:
        base_variations = [
            "teacher", "student", "book", "pencil", "desk", 
            "computer", "backpack", "classroom", "bus", "lunch"
        ]
    elif concept_lower in ['body', 'person', 'me']:
        base_variations = [
            "head", "eyes", "nose", "mouth", "hands", 
            "feet", "hair", "ears", "smile", "face"
        ]
    elif concept_lower in ['emotions', 'feelings', 'mood']:
        base_variations = [
            "happy", "sad", "angry", "excited", "tired", 
            "scared", "surprised", "proud", "calm", "worried"
        ]
    elif concept_lower in ['colors', 'color']:
        base_variations = [
            "red", "blue", "green", "yellow", "orange", 
            "purple", "pink", "black", "white", "brown"
        ]
    elif concept_lower in ['numbers', 'counting', 'math']:
        base_variations = [
            "one", "two", "three", "four", "five", 
            "six", "seven", "eight", "nine", "ten"
        ]
    else:
        # Generic fallback - try to create simple variations of the concept
        base_variations = [
            concept, f"little {concept}", f"big {concept}", 
            f"{concept} toy", f"{concept} picture", f"my {concept}",
            f"new {concept}", f"old {concept}", f"good {concept}", 
            f"nice {concept}"
        ]
    
    # Shuffle and return the requested number
    import random
    random.shuffle(base_variations)
    return base_variations[:num_variations]

# Original simple prompt generation (now fallback)
def generate_prompts(concept, num_variations):
    return generate_prompts_fallback(concept, num_variations)

@app.route('/generate_prompts', methods=['POST'])
def api_generate_prompts():
    data = request.json
    concept = data.get('concept', '')
    num_variations = int(data.get('num_variations', 5))
    
    print(f"Generating {num_variations} prompts for concept: '{concept}'")
    
    # Use AI-powered prompt generation
    prompts = generate_prompts_with_gemini(concept, num_variations)
    
    print(f"Generated prompts: {prompts}")
    return jsonify({'prompts': prompts})

# Production image generation endpoint using Gemini
@app.route('/generate_images', methods=['POST'])
def api_generate_images():
    try:
        data = request.json
        prompts = data.get('prompts', [])
        concept = data.get('concept', 'concept')
        
        print(f"Received request for {len(prompts)} images with concept: {concept}")
        
        image_urls = []
        for i, prompt in enumerate(prompts):
            print(f"Processing prompt {i+1}: {prompt}")
            
            # Try to generate real image with Gemini
            image_data = generate_image_with_gemini(prompt)
            
            if image_data:
                # Successfully got image from Gemini
                image_url = f"data:image/png;base64,{image_data}"
                image_urls.append(image_url)
                print(f"Successfully generated image with Gemini for: {prompt}")
                
                # Generate and print tags for the image using AI analysis
                if image_data:
                    ai_tags = analyze_image_with_gemini(image_data)
                    print(f"Generated AI tags for '{prompt}': {ai_tags}")
                
            else:
                # Fallback to placeholder if Gemini fails
                print(f"Gemini failed for prompt: {prompt}, using fallback placeholder")
                colors = ["pink", "lightblue", "lightgreen", "plum", "khaki"]
                color_name = colors[i % len(colors)]
                
                svg_content = f'''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
                    <rect width="200" height="200" fill="{color_name}" />
                    <text x="100" y="90" text-anchor="middle" dy="0.3em" font-family="Arial" font-size="16" fill="black">
                        Gemini Failed
                    </text>
                    <text x="100" y="110" text-anchor="middle" dy="0.3em" font-family="Arial" font-size="14" fill="black">
                        Fallback {i+1}
                    </text>
                    <text x="100" y="130" text-anchor="middle" dy="0.3em" font-family="Arial" font-size="10" fill="darkgray">
                        {prompt[:20]}...
                    </text>
                </svg>'''
                
                import base64
                svg_base64 = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
                placeholder_url = f"data:image/svg+xml;base64,{svg_base64}"
                image_urls.append(placeholder_url)

        print(f"Returning {len(image_urls)} image URLs")
        return jsonify({
            'images': image_urls,
            'status': 'success',
            'message': f'Generated {len(image_urls)} images (mix of Gemini and fallbacks)'
        })
    
    except Exception as e:
        print(f"Error in api_generate_images: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Search images by tags
@app.route('/search_images', methods=['POST'])
def api_search_images():
    try:
        data = request.json
        search_tags = data.get('tags', [])
        limit = data.get('limit', 10)
        
        print(f"Searching for images with tags: {search_tags}")
        
        if not search_tags:
            return jsonify({'error': 'No search tags provided'}), 400
        
        # Query Firestore for images containing any of the search tags
        images_ref = db.collection('aac_images')
        
        results = []
        unique_ids = set()  # Track unique document IDs to avoid duplicates
        
        for tag in search_tags:
            search_tag = tag.lower().strip()
            
            # Method 1: Exact match (current approach)
            query = images_ref.where('ai_tags', 'array_contains', search_tag).limit(limit * 2)
            docs = query.stream()
            
            for doc in docs:
                if doc.id not in unique_ids:
                    doc_data = doc.to_dict()
                    doc_data['id'] = doc.id
                    results.append(doc_data)
                    unique_ids.add(doc.id)
            
            # Method 2: Get all documents and check for word-boundary matches
            # This is less efficient but more flexible for finding compound tags
            if len(results) < limit:  # Only do this if we need more results
                all_query = images_ref.limit(50)  # Get a reasonable sample
                all_docs = all_query.stream()
                
                for doc in all_docs:
                    if doc.id not in unique_ids:
                        doc_data = doc.to_dict()
                        ai_tags = doc_data.get('ai_tags', [])
                        
                        # Check if any tag contains our search term as a whole word
                        for ai_tag in ai_tags:
                            ai_tag_lower = ai_tag.lower()
                            # Use word boundaries to match whole words only
                            # Split the tag into words and check if our search term matches any word
                            tag_words = ai_tag_lower.replace('-', ' ').replace('_', ' ').split()
                            if search_tag in tag_words:
                                doc_data['id'] = doc.id
                                results.append(doc_data)
                                unique_ids.add(doc.id)
                                break  # Found a match, don't need to check more tags
        
        # Sort by created_at (most recent first)
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Limit final results
        results = results[:limit]
        
        print(f"Found {len(results)} images matching tags")
        
        return jsonify({
            'status': 'success',
            'count': len(results),
            'images': results,
            'search_tags': search_tags
        })
    
    except Exception as e:
        print(f"Error in api_search_images: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Get all saved images with optional filtering
@app.route('/list_images', methods=['GET'])
def api_list_images():
    try:
        limit = int(request.args.get('limit', 20))
        concept_filter = request.args.get('concept', '')
        
        print(f"Listing images (limit: {limit}, concept: {concept_filter or 'all'})")
        
        images_ref = db.collection('aac_images')
        
        if concept_filter:
            query = images_ref.where('concept', '==', concept_filter.lower()).limit(limit)
        else:
            query = images_ref.limit(limit)
        
        # Order by creation time (most recent first)
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
        
        docs = query.stream()
        
        results = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            # Convert Firestore timestamp to string for JSON serialization
            if 'created_at' in doc_data:
                doc_data['created_at'] = doc_data['created_at'].isoformat()
            results.append(doc_data)
        
        print(f"Found {len(results)} images")
        
        return jsonify({
            'status': 'success',
            'count': len(results),
            'images': results
        })
    
    except Exception as e:
        print(f"Error in api_list_images: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return 'Backend is running.'

if __name__ == '__main__':
    import sys
    import signal
    
    def signal_handler(sig, frame):
        print('\nGracefully shutting down server...')
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Starting Brimage AAC API server...")
    print("URL: http://127.0.0.1:5003")
    print("Press Ctrl+C to stop")
    
    # Run with more stable settings
    app.run(
        host='127.0.0.1',
        port=5003,
        debug=True,
        use_reloader=False,  # Disable auto-reloader to prevent port conflicts
        threaded=True        # Better for concurrent requests
    )
