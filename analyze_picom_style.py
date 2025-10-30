#!/usr/bin/env python3
"""
Script to analyze PiComImages style using Gemini Vision
"""

import os
import random
import google.generativeai as genai
from pathlib import Path
import base64

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash-exp')

def analyze_picom_images(num_samples=5):
    """Analyze sample images from PiComImages folder to understand the style"""
    picom_folder = Path("/Users/blakethomas/Documents/BravoGCPCopilot/PiComImages")
    
    # Get all PNG files
    image_files = list(picom_folder.glob("*.png"))
    if not image_files:
        print("No PNG files found in PiComImages folder")
        return
    
    # Select random samples
    sample_files = random.sample(image_files, min(num_samples, len(image_files)))
    
    print(f"Analyzing {len(sample_files)} sample images from PiComImages...")
    
    for i, image_file in enumerate(sample_files, 1):
        print(f"\n--- Analyzing Image {i}: {image_file.name} ---")
        
        try:
            # Read and encode image
            with open(image_file, "rb") as f:
                image_data = f.read()
            
            # Upload image to Gemini
            uploaded_image = genai.upload_file(image_file, mime_type="image/png")
            
            prompt = """
            Analyze this AAC (Augmentative and Alternative Communication) symbol image in detail. Describe:
            
            1. VISUAL STYLE:
               - Art style (cartoon, realistic, minimalist, etc.)
               - Line thickness and quality
               - Color palette and saturation
               - Shading/lighting approach
               - Level of detail
            
            2. COMPOSITION:
               - Background (transparent, solid color, simple pattern)
               - Subject positioning and framing
               - Use of negative space
            
            3. DESIGN CHARACTERISTICS:
               - How simplified or detailed are objects?
               - Are outlines prominent or subtle?
               - What's the overall aesthetic approach?
               - How would you describe the "feel" of the image?
            
            4. AAC-SPECIFIC FEATURES:
               - How clear and recognizable is the concept?
               - What makes this effective for communication?
            
            Please be very specific about visual characteristics that would help recreate this style.
            """
            
            response = model.generate_content([prompt, uploaded_image])
            print(response.text)
            
            # Clean up uploaded file
            genai.delete_file(uploaded_image.name)
            
        except Exception as e:
            print(f"Error analyzing {image_file.name}: {e}")
    
    # Generate style summary
    print(f"\n{'='*50}")
    print("STYLE SUMMARY ANALYSIS")
    print(f"{'='*50}")
    
    summary_prompt = f"""
    Based on analyzing {len(sample_files)} AAC symbol images, provide a comprehensive style guide that could be used to generate similar images. Focus on:
    
    1. A detailed visual style description
    2. Specific technical characteristics (colors, lines, composition)
    3. A concise prompt description that could be used with AI image generators
    
    Make this practical for creating consistent AAC symbols.
    """
    
    try:
        summary_response = model.generate_content(summary_prompt)
        print(summary_response.text)
    except Exception as e:
        print(f"Error generating summary: {e}")

if __name__ == "__main__":
    analyze_picom_images(5)