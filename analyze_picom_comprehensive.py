#!/usr/bin/env python3
"""
Enhanced PiCom Image Analysis with AI Vision
Combines filename parsing with AI image analysis to generate comprehensive tags
"""

import os
import json
import base64
from collections import defaultdict
import asyncio
import aiohttp
from pathlib import Path

# You'll need to install: pip install google-cloud-aiplatform pillow
try:
    import google.generativeai as genai
    from google.cloud import aiplatform
    from PIL import Image
    import io
except ImportError:
    print("Please install required packages:")
    print("pip install google-generativeai google-cloud-aiplatform pillow")
    exit(1)

class PiComImageAnalyzer:
    def __init__(self, images_dir, output_file):
        self.images_dir = Path(images_dir)
        self.output_file = output_file
        self.analysis_results = []
        
        # Initialize Gemini Vision API
        # You'll need to set your API key
        # genai.configure(api_key="YOUR_GEMINI_API_KEY")
        
    def extract_filename_metadata(self, filename):
        """Extract basic metadata from filename"""
        # Remove .png extension and split on underscore
        base_name = filename.replace('.png', '')
        if '_' in base_name:
            description, image_id = base_name.rsplit('_', 1)
        else:
            description, image_id = base_name, "unknown"
            
        # Basic categorization from filename
        desc_lower = description.lower()
        
        categories = []
        basic_tags = description.replace('_', ' ').split()
        
        # Determine primary categories
        if any(emotion in desc_lower for emotion in ['happy', 'sad', 'angry', 'afraid', 'excited', 'surprised', 'worried', 'tired']):
            categories.append('emotions')
        if any(action in desc_lower for action in ['run', 'walk', 'jump', 'eat', 'drink', 'play', 'sleep', 'sit', 'stand']):
            categories.append('actions')
        if any(body in desc_lower for body in ['hand', 'foot', 'head', 'eye', 'mouth', 'nose', 'ear']):
            categories.append('body_parts')
        if any(color in desc_lower for color in ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'black', 'white']):
            categories.append('colors')
        if 'upper case' in desc_lower or 'lower case' in desc_lower:
            categories.append('letters')
        if any(food in desc_lower for food in ['apple', 'bread', 'cake', 'pizza', 'burger', 'food']):
            categories.append('food')
        if any(animal in desc_lower for animal in ['dog', 'cat', 'bird', 'fish', 'cow', 'horse', 'animal']):
            categories.append('animals')
        if any(person in desc_lower for person in ['man', 'woman', 'boy', 'girl', 'baby', 'child', 'person']):
            categories.append('people')
        if any(place in desc_lower for place in ['home', 'school', 'hospital', 'shop', 'park']):
            categories.append('places')
            
        return {
            'filename': filename,
            'image_id': image_id,
            'description': description,
            'basic_categories': categories,
            'basic_tags': basic_tags
        }
    
    async def analyze_image_with_ai(self, image_path):
        """Use Gemini Vision to analyze image and generate additional tags"""
        try:
            # Load and prepare image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (Gemini has size limits)
                max_size = 1024
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                image_data = base64.b64encode(buffer.getvalue()).decode()
            
            # Create analysis prompt
            prompt = """
            Analyze this AAC (Augmentative and Alternative Communication) symbol image and provide:
            
            1. MAIN_SUBJECT: What is the primary subject/focus of the image?
            2. EMOTIONS: Any emotions displayed or conveyed (if applicable)
            3. ACTIONS: Any actions, movements, or activities shown
            4. OBJECTS: All visible objects, items, or things
            5. PEOPLE: Types of people shown (age, gender, relationships if clear)
            6. SETTINGS: Location, environment, or context
            7. CONCEPTS: Abstract concepts this image could represent
            8. AAC_USAGE: How this symbol might be used in AAC communication
            9. DIFFICULTY: Simple, Intermediate, or Complex (based on concept complexity)
            10. AGE_GROUPS: Which age groups would find this most useful (child, teen, adult, all)
            
            Respond in JSON format with these exact keys. Be concise but thorough.
            Consider that this is for AAC users who may have communication challenges.
            """
            
            # Note: This is pseudocode for Gemini Vision API
            # You'll need to implement the actual API call based on current Gemini documentation
            """
            model = genai.GenerativeModel('gemini-pro-vision')
            response = model.generate_content([prompt, {'mime_type': 'image/png', 'data': image_data}])
            
            # Parse JSON response
            ai_analysis = json.loads(response.text)
            """
            
            # For now, return mock data structure
            ai_analysis = {
                'main_subject': 'placeholder',
                'emotions': [],
                'actions': [],
                'objects': [],
                'people': [],
                'settings': [],
                'concepts': [],
                'aac_usage': 'placeholder',
                'difficulty': 'simple',
                'age_groups': ['all']
            }
            
            return ai_analysis
            
        except Exception as e:
            print(f"Error analyzing {image_path}: {e}")
            return None
    
    def calculate_search_metadata(self, filename_data, ai_data):
        """Combine filename and AI data to create comprehensive search metadata"""
        if not ai_data:
            return filename_data
        
        # Combine all tags
        all_tags = set(filename_data['basic_tags'])
        
        # Add AI-generated tags
        for category in ['emotions', 'actions', 'objects', 'people', 'settings', 'concepts']:
            if category in ai_data and ai_data[category]:
                all_tags.update(ai_data[category])
        
        # Enhanced categorization
        enhanced_categories = filename_data['basic_categories'].copy()
        
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
        
        return {
            **filename_data,
            'ai_analysis': ai_data,
            'enhanced_categories': enhanced_categories,
            'all_tags': list(all_tags),
            'difficulty_level': ai_data.get('difficulty', 'simple'),
            'age_groups': ai_data.get('age_groups', ['all']),
            'aac_usage_context': ai_data.get('aac_usage', ''),
            'search_weight': len(all_tags)  # More tags = higher search relevance
        }
    
    async def analyze_batch(self, image_files, batch_size=10):
        """Process images in batches to avoid API rate limits"""
        results = []
        
        for i in range(0, len(image_files), batch_size):
            batch = image_files[i:i + batch_size]
            batch_tasks = []
            
            for filename in batch:
                image_path = self.images_dir / filename
                if image_path.exists():
                    batch_tasks.append(self.process_single_image(image_path))
            
            # Process batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Filter out exceptions
            valid_results = [r for r in batch_results if not isinstance(r, Exception)]
            results.extend(valid_results)
            
            print(f"Processed batch {i//batch_size + 1}: {len(valid_results)} images")
            
            # Small delay to be respectful to API limits
            await asyncio.sleep(1)
        
        return results
    
    async def process_single_image(self, image_path):
        """Process a single image with both filename and AI analysis"""
        filename = image_path.name
        
        # Extract filename metadata
        filename_data = self.extract_filename_metadata(filename)
        
        # AI analysis
        ai_data = await self.analyze_image_with_ai(image_path)
        
        # Combine into comprehensive metadata
        full_metadata = self.calculate_search_metadata(filename_data, ai_data)
        
        return full_metadata
    
    async def run_full_analysis(self):
        """Run complete analysis on all images"""
        print(f"🔍 Starting comprehensive analysis of PiCom images...")
        
        # Get all PNG files
        png_files = [f.name for f in self.images_dir.glob("*.png")]
        print(f"📊 Found {len(png_files)} images to analyze")
        
        # Process in batches
        results = await self.analyze_batch(png_files)
        
        # Create summary statistics
        summary = {
            'total_images_analyzed': len(results),
            'categories_distribution': defaultdict(int),
            'difficulty_distribution': defaultdict(int),
            'age_group_distribution': defaultdict(int),
            'top_tags': defaultdict(int)
        }
        
        for result in results:
            for category in result.get('enhanced_categories', []):
                summary['categories_distribution'][category] += 1
            
            difficulty = result.get('difficulty_level', 'simple')
            summary['difficulty_distribution'][difficulty] += 1
            
            for age_group in result.get('age_groups', ['all']):
                summary['age_group_distribution'][age_group] += 1
            
            for tag in result.get('all_tags', []):
                summary['top_tags'][tag] += 1
        
        # Convert defaultdicts to regular dicts for JSON serialization
        summary = {k: dict(v) if isinstance(v, defaultdict) else v for k, v in summary.items()}
        
        # Save comprehensive results
        output_data = {
            'analysis_date': '2025-09-17',
            'summary': summary,
            'images': results
        }
        
        with open(self.output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"💾 Comprehensive analysis saved to: {self.output_file}")
        print(f"📈 Summary:")
        print(f"   - Categories found: {len(summary['categories_distribution'])}")
        print(f"   - Unique tags: {len(summary['top_tags'])}")
        print(f"   - Most common tags: {list(sorted(summary['top_tags'].items(), key=lambda x: x[1], reverse=True)[:10])}")
        
        return output_data

async def main():
    images_dir = "/Users/blakethomas/Documents/BravoGCPCopilot/PiComImages"
    output_file = "/Users/blakethomas/Documents/BravoGCPCopilot/picom_comprehensive_analysis.json"
    
    analyzer = PiComImageAnalyzer(images_dir, output_file)
    
    # For now, just do filename analysis as a starting point
    print("🚀 Starting comprehensive PiCom image analysis...")
    print("📝 Note: AI vision analysis is prepared but requires API key setup")
    
    # Run analysis
    results = await analyzer.run_full_analysis()
    
    print("✅ Analysis complete!")

if __name__ == "__main__":
    asyncio.run(main())