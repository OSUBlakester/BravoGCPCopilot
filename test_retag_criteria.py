#!/usr/bin/env python3
"""
Test script to check how many images actually need re-tagging with corrected criteria
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from retag_bravo_images import BravoImageRetagger

async def test_retag_criteria():
    """Test the corrected re-tagging criteria"""
    retagger = BravoImageRetagger()
    
    print("🔍 Testing corrected re-tagging criteria...")
    
    images_to_retag = await retagger.find_images_needing_retag()
    
    print(f"📊 Found {len(images_to_retag)} images that actually need re-tagging")
    
    if len(images_to_retag) > 0:
        print("\n🔍 First 5 examples of images that need re-tagging:")
        for i, image in enumerate(images_to_retag[:5]):
            print(f"  {i+1}. {image['concept']}/{image['subconcept']}")
            print(f"     Current tags: {image['current_tags']}")
            print()
    else:
        print("🎉 All images have good tags with correct priority!")

if __name__ == "__main__":
    asyncio.run(test_retag_criteria())