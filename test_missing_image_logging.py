#!/usr/bin/env python3
"""
Test script to verify missing image logging functionality.
This will make some searches for terms that likely don't have images,
triggering the missing image logging system.
"""

import asyncio
import aiohttp
import json

# Test search terms that likely won't have images
TEST_TERMS = [
    "xylophone_purple_zebra",
    "quantum_unicorn_dance", 
    "invisible_elephant_shoes",
    "digital_rainbow_sandwich",
    "cosmic_potato_symphony",
    "mythical_coffee_dragon",
    "enchanted_keyboard_forest",
    "flying_pizza_orchestra",
    "magical_stapler_kingdom",
    "interdimensional_banana_portal"
]

BASE_URL = "https://bravo-dev-465400.uc.r.appspot.com"

async def test_missing_image_logging():
    """Test the missing image logging system"""
    print("🧪 Testing Missing Image Logging System")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        for term in TEST_TERMS:
            try:
                print(f"🔍 Searching for: {term}")
                
                # Make a search request that should return no results
                url = f"{BASE_URL}/api/imagecreator/search"
                params = {"tag": term, "limit": 5}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        image_count = data.get("total_found", 0)
                        
                        if image_count == 0:
                            print(f"  ✅ No images found - should be logged as missing")
                        else:
                            print(f"  ⚠️ Found {image_count} images - won't be logged")
                    else:
                        print(f"  ❌ Search failed: {response.status}")
                        
            except Exception as e:
                print(f"  ❌ Error searching for {term}: {e}")
            
            # Small delay between requests
            await asyncio.sleep(0.5)
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")
    print("\n📋 Next steps:")
    print("1. Wait a few seconds for logging to complete")
    print("2. Visit https://bravo-dev-465400.uc.r.appspot.com/missing_images.html")
    print("3. Check if the test terms appear in the missing images log")
    print("4. Verify the search counts and timestamps")

if __name__ == "__main__":
    asyncio.run(test_missing_image_logging())