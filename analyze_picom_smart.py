#!/usr/bin/env python3
"""
PiCom Image Analysis with Gemini Vision
Uses Google's Gemini to analyze PiCom images and generate comprehensive tags
"""

import os
import json
import base64
from collections import defaultdict, Counter
from pathlib import Path
import asyncio
import sys

def analyze_filename_metadata():
    """First, let's do the filename analysis to understand the structure"""
    picom_dir = Path("/Users/blakethomas/Documents/BravoGCPCopilot/PiComImages")
    
    # Get all PNG files
    png_files = list(picom_dir.glob("*.png"))
    print(f"📊 Found {len(png_files)} images to analyze")
    
    # Categories for analysis
    emotion_words = ['happy', 'sad', 'angry', 'afraid', 'excited', 'surprised', 'worried', 'tired', 'confused', 'bored', 'crying', 'laughing', 'smiling']
    action_words = ['run', 'walk', 'jump', 'eat', 'drink', 'play', 'sleep', 'sit', 'stand', 'dance', 'swimming', 'cooking', 'reading', 'writing', 'climbing', 'throwing']
    body_words = ['hand', 'foot', 'head', 'eye', 'eyes', 'mouth', 'nose', 'ear', 'arm', 'leg', 'face', 'hair', 'finger']
    color_words = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'black', 'white', 'pink', 'brown', 'grey', 'gray']
    people_words = ['man', 'woman', 'boy', 'girl', 'baby', 'child', 'person', 'people', 'mother', 'father', 'family', 'friend']
    animal_words = ['dog', 'cat', 'bird', 'fish', 'cow', 'horse', 'pig', 'sheep', 'rabbit', 'duck', 'chicken', 'elephant']
    food_words = ['apple', 'bread', 'cake', 'pizza', 'burger', 'food', 'eat', 'drink', 'milk', 'cheese', 'fruit', 'vegetable']
    place_words = ['home', 'school', 'hospital', 'shop', 'park', 'bedroom', 'kitchen', 'bathroom', 'garden', 'playground']
    
    categories = defaultdict(list)
    all_descriptions = []
    tag_frequency = Counter()
    
    results = []
    
    for image_path in png_files:
        filename = image_path.name
        
        # Parse filename
        base_name = filename.replace('.png', '')
        if '_' in base_name:
            description, image_id = base_name.rsplit('_', 1)
        else:
            description = base_name
            image_id = "unknown"
        
        # Clean and tokenize description
        desc_lower = description.lower().replace('_', ' ')
        all_descriptions.append(desc_lower)
        
        # Extract individual words as potential tags
        words = desc_lower.split()
        basic_tags = []
        
        # Categorize based on content
        found_categories = []
        
        if any(emotion in desc_lower for emotion in emotion_words):
            found_categories.append('emotions')
            basic_tags.extend([word for word in emotion_words if word in desc_lower])
            
        if any(action in desc_lower for action in action_words):
            found_categories.append('actions')
            basic_tags.extend([word for word in action_words if word in desc_lower])
            
        if any(body in desc_lower for body in body_words):
            found_categories.append('body_parts')
            basic_tags.extend([word for word in body_words if word in desc_lower])
            
        if any(color in desc_lower for color in color_words):
            found_categories.append('colors')
            basic_tags.extend([word for word in color_words if word in desc_lower])
            
        if any(person in desc_lower for person in people_words):
            found_categories.append('people')
            basic_tags.extend([word for word in people_words if word in desc_lower])
            
        if any(animal in desc_lower for animal in animal_words):
            found_categories.append('animals')
            basic_tags.extend([word for word in animal_words if word in desc_lower])
            
        if any(food in desc_lower for food in food_words):
            found_categories.append('food')
            basic_tags.extend([word for word in food_words if word in desc_lower])
            
        if any(place in desc_lower for place in place_words):
            found_categories.append('places')
            basic_tags.extend([word for word in place_words if word in desc_lower])
            
        if 'upper case' in desc_lower or 'lower case' in desc_lower:
            found_categories.append('letters')
            
        if any(num in desc_lower for num in ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'zero']) or any(char.isdigit() for char in desc_lower):
            found_categories.append('numbers')
        
        # Add all words as potential tags
        basic_tags.extend(words)
        basic_tags = list(set(basic_tags))  # Remove duplicates
        
        # Update frequency counter
        tag_frequency.update(basic_tags)
        
        # Determine difficulty based on description complexity
        difficulty = 'simple'
        if len(words) > 3 or any(complex_word in desc_lower for complex_word in ['communication', 'wheelchair', 'therapist', 'equipment']):
            difficulty = 'complex'
        elif len(words) > 2:
            difficulty = 'intermediate'
        
        # Determine age groups
        age_groups = ['all']
        if any(child_word in desc_lower for child_word in ['baby', 'child', 'toy', 'playground']):
            age_groups = ['child']
        elif any(adult_word in desc_lower for adult_word in ['work', 'job', 'office', 'driving']):
            age_groups = ['adult']
        
        # Create comprehensive metadata
        image_metadata = {
            'filename': filename,
            'image_id': image_id,
            'description': description.replace('_', ' '),
            'categories': found_categories if found_categories else ['other'],
            'tags': basic_tags,
            'difficulty': difficulty,
            'age_groups': age_groups,
            'word_count': len(words),
            'search_priority': len(basic_tags) * (2 if found_categories else 1)  # Higher priority for categorized items with more tags
        }
        
        results.append(image_metadata)
        
        # Add to categories
        for category in (found_categories if found_categories else ['other']):
            categories[category].append(filename)
    
    # Print analysis
    print("\n📋 Category Breakdown:")
    for category, files in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {category}: {len(files)} images")
    
    print(f"\n🏷️  Most Common Tags:")
    for tag, count in tag_frequency.most_common(20):
        if len(tag) > 2:  # Filter out very short words
            print(f"  {tag}: {count}")
    
    # Prepare Gemini Vision analysis structure
    gemini_analysis_template = {
        'prompt_template': """
        Analyze this AAC symbol image and provide additional tags that would help users find this image when communicating. 

        Current tags from filename: {current_tags}
        Current categories: {current_categories}

        Please add:
        1. EMOTIONS: Any emotions visible or that this image might convey
        2. ACTIONS: Any actions, activities, or verbs this represents  
        3. OBJECTS: All objects, items, or things visible
        4. CONCEPTS: Abstract ideas this could represent (feelings, relationships, time, etc.)
        5. USAGE_CONTEXT: When/how someone might use this in AAC communication
        6. SIMILAR_WORDS: Synonyms or related words that mean the same thing
        7. DIFFICULTY: simple/intermediate/complex based on concept abstractness
        
        Respond with just the new tags as a comma-separated list, focusing on words an AAC user might think of when looking for this concept.
        """,
        'batch_processing_plan': {
            'images_per_batch': 10,
            'estimated_api_calls': len(results),
            'estimated_cost': f"~${len(results) * 0.002:.2f} (at $0.002 per image)",
            'processing_time': f"~{len(results) * 2 // 60} minutes"
        }
    }
    
    # Save results
    output_data = {
        'analysis_date': '2025-09-17',
        'total_images': len(results),
        'category_stats': {k: len(v) for k, v in categories.items()},
        'top_tags': dict(tag_frequency.most_common(50)),
        'images': results,
        'gemini_analysis_ready': gemini_analysis_template
    }
    
    output_file = "/Users/blakethomas/Documents/BravoGCPCopilot/picom_ready_for_ai_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Analysis saved to: {output_file}")
    print(f"\n🤖 Ready for AI Enhancement:")
    print(f"   - {len(results)} images analyzed")
    print(f"   - {len(set(tag_frequency.keys()))} unique tags extracted")
    print(f"   - {len(categories)} categories identified")
    print(f"   - Estimated Gemini API cost: {gemini_analysis_template['batch_processing_plan']['estimated_cost']}")
    
    return output_data

def create_database_schema():
    """Design the Firestore schema for storing symbol data"""
    
    schema = {
        "symbols": {
            "collection_name": "aac_symbols",
            "document_structure": {
                "symbol_id": "string (unique identifier)",
                "filename": "string (original filename)",
                "image_url": "string (Cloud Storage URL)",
                "thumbnail_url": "string (smaller version for lists)",
                
                # Core metadata
                "name": "string (primary name/description)",
                "description": "string (detailed description)",
                "alt_text": "string (accessibility description)",
                
                # Categorization
                "primary_category": "string (main category)",
                "categories": "array<string> (all applicable categories)",
                "tags": "array<string> (all searchable tags)",
                "ai_tags": "array<string> (AI-generated tags)",
                "filename_tags": "array<string> (extracted from filename)",
                
                # Usage context
                "difficulty_level": "string (simple|intermediate|complex)",
                "age_groups": "array<string> (child|teen|adult|elderly)",
                "usage_contexts": "array<string> (when/how to use)",
                "related_concepts": "array<string> (similar meanings)",
                
                # Search optimization
                "search_weight": "number (relevance scoring)",
                "usage_frequency": "number (how often selected)",
                "last_used": "timestamp",
                "created_at": "timestamp",
                "updated_at": "timestamp",
                
                # Source tracking
                "source": "string (picom_cartoon|picom_action|custom)",
                "source_id": "string (original ID from source)",
                "processing_status": "string (analyzed|needs_review|approved)"
            },
            
            "indexes_needed": [
                {"fields": ["primary_category", "difficulty_level"]},
                {"fields": ["tags", "search_weight"], "array_config": "contains"},
                {"fields": ["age_groups", "categories"], "array_config": "contains"},
                {"fields": ["usage_frequency", "created_at"]},
                {"fields": ["processing_status", "source"]}
            ]
        },
        
        "symbol_usage": {
            "collection_name": "symbol_usage_analytics",
            "document_structure": {
                "user_id": "string",
                "symbol_id": "string", 
                "used_at": "timestamp",
                "context": "string (search_query that found it)",
                "selected": "boolean (was it actually used?)",
                "session_id": "string"
            }
        }
    }
    
    print("🗄️  Database Schema Design:")
    print(json.dumps(schema, indent=2))
    
    # Save schema
    schema_file = "/Users/blakethomas/Documents/BravoGCPCopilot/picom_database_schema.json"
    with open(schema_file, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f"\n💾 Schema saved to: {schema_file}")
    return schema

if __name__ == "__main__":
    print("🚀 Starting PiCom Image Analysis...")
    
    # Step 1: Analyze filenames and prepare for AI enhancement
    analysis_data = analyze_filename_metadata()
    
    # Step 2: Create database schema
    schema = create_database_schema()
    
    print("\n✅ Analysis Complete!")
    print("\n📋 Next Steps:")
    print("1. 🤖 Set up Gemini Vision API for AI tag enhancement")
    print("2. ☁️  Create Cloud Storage bucket for images")  
    print("3. 🗄️  Implement Firestore collections with the designed schema")
    print("4. 📤 Build upload/processing pipeline")
    print("5. 🔍 Integrate intelligent search with AAC interface")