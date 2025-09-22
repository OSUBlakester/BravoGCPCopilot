#!/usr/bin/env python3
"""
PiCom Image Analysis Script
Analyzes the structure and categorization of PiCom images to understand patterns
"""

import os
import re
from collections import defaultdict, Counter
import json

def analyze_picom_images():
    picom_dir = "/Users/blakethomas/Documents/BravoGCPCopilot/PiComImages"
    
    # Get all PNG files
    png_files = [f for f in os.listdir(picom_dir) if f.endswith('.png')]
    
    print(f"📊 Total images found: {len(png_files)}")
    
    # Parse naming patterns
    categories = defaultdict(list)
    emotion_words = []
    action_words = []
    object_words = []
    body_parts = []
    colors = []
    numbers = []
    letters = []
    
    # Common AAC categories to look for
    emotion_keywords = ['happy', 'sad', 'angry', 'afraid', 'excited', 'surprised', 'worried', 'tired', 'confused']
    action_keywords = ['run', 'walk', 'jump', 'eat', 'drink', 'play', 'sleep', 'sit', 'stand', 'dance']
    body_keywords = ['hand', 'foot', 'head', 'eye', 'mouth', 'nose', 'ear', 'arm', 'leg']
    color_keywords = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'black', 'white', 'pink']
    
    # Analyze each filename
    for filename in png_files:
        # Extract description (everything before the last underscore and ID)
        if '_' in filename:
            parts = filename.rsplit('_', 1)
            if len(parts) == 2:
                description = parts[0].lower()
                id_part = parts[1].replace('.png', '')
                
                # Categorize by content
                if any(emotion in description for emotion in emotion_keywords):
                    categories['emotions'].append(filename)
                elif any(action in description for action in action_keywords):
                    categories['actions'].append(filename)
                elif any(body in description for body in body_keywords):
                    categories['body_parts'].append(filename)
                elif any(color in description for color in color_keywords):
                    categories['colors'].append(filename)
                elif 'upper case' in description or 'lower case' in description:
                    categories['letters'].append(filename)
                elif description.isdigit() or any(num in description for num in ['one', 'two', 'three', 'four', 'five']):
                    categories['numbers'].append(filename)
                elif any(food in description for food in ['apple', 'bread', 'cake', 'pizza', 'burger']):
                    categories['food'].append(filename)
                elif any(animal in description for animal in ['dog', 'cat', 'bird', 'fish', 'cow', 'horse']):
                    categories['animals'].append(filename)
                elif any(person in description for person in ['man', 'woman', 'boy', 'girl', 'baby', 'child']):
                    categories['people'].append(filename)
                elif any(place in description for place in ['home', 'school', 'hospital', 'shop', 'park']):
                    categories['places'].append(filename)
                else:
                    categories['other'].append(filename)
    
    # Print category analysis
    print("\n📋 Category Breakdown:")
    for category, files in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {category}: {len(files)} images")
    
    # Find some example descriptions for each category
    print("\n🔍 Example descriptions by category:")
    for category, files in categories.items():
        if files:
            examples = [f.rsplit('_', 1)[0] for f in files[:3]]
            print(f"  {category}: {examples}")
    
    # Look for ID patterns
    ids = []
    for filename in png_files:
        if '_' in filename:
            parts = filename.rsplit('_', 1)
            if len(parts) == 2:
                id_part = parts[1].replace('.png', '')
                try:
                    ids.append(int(id_part))
                except ValueError:
                    pass
    
    if ids:
        print(f"\n🔢 ID Range: {min(ids)} to {max(ids)}")
        print(f"   Average ID: {sum(ids) // len(ids)}")
    
    # Save categorization to JSON
    output_file = "/Users/blakethomas/Documents/BravoGCPCopilot/picom_analysis.json"
    analysis_data = {
        'total_images': len(png_files),
        'categories': {k: len(v) for k, v in categories.items()},
        'category_examples': {k: [f.rsplit('_', 1)[0] for f in v[:5]] for k, v in categories.items()},
        'id_range': {'min': min(ids) if ids else 0, 'max': max(ids) if ids else 0}
    }
    
    with open(output_file, 'w') as f:
        json.dump(analysis_data, f, indent=2)
    
    print(f"\n💾 Analysis saved to: {output_file}")
    return analysis_data

if __name__ == "__main__":
    analyze_picom_images()