#!/usr/bin/env python3
"""
Simplified test for Gemini Context Caching functionality
Tests the caching API integration directly
"""

import asyncio
import json
import os
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import google.generativeai as genai
    from google.generativeai import caching
except ImportError:
    print("❌ google-generativeai not installed. Run: pip install google-generativeai")
    exit(1)

async def test_gemini_caching_api():
    """Test the Gemini Context Caching API directly"""
    
    print("🧪 Testing Gemini Context Caching API Integration")
    print("=" * 60)
    
    # Load config to get API key
    try:
        import config
        api_key = config.GEMINI_API_KEY
        if not api_key or api_key.startswith('your_'):
            print("❌ No valid Gemini API key found in config")
            return False
    except ImportError:
        print("❌ Could not import config. Ensure config.py exists with GEMINI_API_KEY")
        return False
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    print(f"✅ Configured Gemini API")
    
    # Test context data
    test_context = {
        "user_profile": {
            "name": "Test User",
            "age": 25,
            "communication_style": "casual and friendly",
            "interests": ["technology", "music", "sports"]
        },
        "accessibility_needs": ["large buttons", "clear audio"],
        "vocabulary_level": "intermediate",
        "friends_family": [
            {"name": "Alice", "relationship": "friend"},
            {"name": "Bob", "relationship": "brother"}
        ]
    }
    
    try:
        # Test 1: Create cached content
        print("\n1️⃣ Testing Gemini cached content creation...")
        
        # Format content for Gemini cache
        context_text = f"""
User Profile and Context:
- Name: {test_context['user_profile']['name']}
- Age: {test_context['user_profile']['age']}
- Communication Style: {test_context['user_profile']['communication_style']}
- Interests: {', '.join(test_context['user_profile']['interests'])}
- Accessibility Needs: {', '.join(test_context['accessibility_needs'])}
- Vocabulary Level: {test_context['vocabulary_level']}
- Friends/Family: {', '.join([f"{p['name']} ({p['relationship']})" for p in test_context['friends_family']])}

This user prefers simple, clear communication options that are easy to understand and use.
"""
        
        # Create cached content object
        cached_content = caching.CachedContent.create(
            model='models/gemini-1.5-flash-8b',
            display_name='test_user_context_cache',
            contents=[{
                'role': 'user',
                'parts': [{'text': context_text}]
            }],
            ttl='300s'  # 5 minutes for testing
        )
        
        print(f"✅ Successfully created cached content: {cached_content.name}")
        print(f"   Cache Display Name: {cached_content.display_name}")
        print(f"   Model: {cached_content.model}")
        print(f"   TTL: {cached_content.ttl}")
        
        # Test 2: Use cached content to generate response
        print("\n2️⃣ Testing content generation with cached context...")
        
        model = genai.GenerativeModel(
            model_name='models/gemini-1.5-flash-8b',
            cached_content=cached_content
        )
        
        test_prompt = "Help me communicate that I'm feeling happy today. Suggest 3 simple communication options."
        
        response = model.generate_content(test_prompt)
        
        if response and response.text:
            print("✅ Successfully generated content with cached context")
            print(f"   Response length: {len(response.text)} characters")
            print(f"   Response preview: {response.text[:200]}...")
        else:
            print("❌ Failed to generate content with cached context")
            return False
        
        # Test 3: List cached content
        print("\n3️⃣ Testing cached content listing...")
        
        cached_contents = caching.CachedContent.list()
        print(f"✅ Found {len(cached_contents)} cached content objects")
        
        for content in cached_contents:
            if content.display_name == 'test_user_context_cache':
                print(f"   Found our test cache: {content.name}")
                break
        
        # Test 4: Delete cached content (cleanup)
        print("\n4️⃣ Testing cached content deletion...")
        
        cached_content.delete()
        print("✅ Successfully deleted cached content")
        
        print("\n🎉 Gemini Context Caching API tests completed successfully!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Gemini Context Caching API Test")
    success = asyncio.run(test_gemini_caching_api())
    
    if success:
        print("\n✅ All tests passed! Gemini Context Caching API is working correctly.")
        print("💡 The implementation in server.py should work with this API.")
        exit(0)
    else:
        print("\n❌ Some tests failed. Check the API configuration.")
        exit(1)
