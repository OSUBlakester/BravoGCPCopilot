#!/usr/bin/env python3
"""
Direct LLM Testing Script
Tests Google Gemini API directly to isolate LLM issues from server code
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_environment():
    """Check if environment variables are set"""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY environment variable not set")
        return False
    
    print(f"✅ GOOGLE_API_KEY found (first 5 chars): {api_key[:5]}*****")
    return True

def test_basic_import():
    """Test if google.generativeai can be imported"""
    try:
        import google.generativeai as genai
        print("✅ google.generativeai imported successfully")
        return genai
    except ImportError as e:
        print(f"❌ Failed to import google.generativeai: {e}")
        return None

def test_api_configuration(genai):
    """Test API configuration"""
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        print("✅ Gemini API configured successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to configure Gemini API: {e}")
        return False

def test_model_initialization(genai):
    """Test different model initializations"""
    models_to_test = [
        'models/gemini-1.5-flash-latest',
        'models/gemini-pro',
        'models/gemini-2.5-flash-preview-05-20'
    ]
    
    successful_models = []
    
    for model_name in models_to_test:
        try:
            model = genai.GenerativeModel(model_name)
            print(f"✅ Model '{model_name}' initialized successfully")
            successful_models.append((model_name, model))
        except Exception as e:
            print(f"❌ Failed to initialize model '{model_name}': {e}")
    
    return successful_models

def test_simple_generation(model_name, model):
    """Test simple content generation"""
    try:
        test_prompt = "Say hello and confirm you're working properly."
        print(f"\n🔄 Testing generation with {model_name}...")
        print(f"Prompt: {test_prompt}")
        
        response = model.generate_content(test_prompt)
        response_text = response.text if hasattr(response, 'text') else str(response)
        
        print(f"✅ Response from {model_name}:")
        print(f"   {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
        return True
        
    except Exception as e:
        print(f"❌ Generation failed for {model_name}: {e}")
        return False

def test_json_generation(model_name, model):
    """Test JSON generation similar to your server"""
    try:
        test_prompt = "Generate a JSON array of 5 greeting phrases. Each phrase should be a simple string. Return only valid JSON."
        generation_config = {
            "response_mime_type": "application/json",
            "temperature": 0.7
        }
        
        print(f"\n🔄 Testing JSON generation with {model_name}...")
        print(f"Prompt: {test_prompt[:100]}...")
        
        response = model.generate_content(test_prompt, generation_config=generation_config)
        response_text = response.text if hasattr(response, 'text') else str(response)
        
        # Try to parse as JSON
        parsed_json = json.loads(response_text)
        print(f"✅ JSON generation successful for {model_name}")
        print(f"   Response type: {type(parsed_json)}")
        print(f"   Length: {len(parsed_json) if isinstance(parsed_json, (list, dict)) else 'N/A'}")
        print(f"   First item: {parsed_json[0] if isinstance(parsed_json, list) and parsed_json else parsed_json}")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed for {model_name}: {e}")
        print(f"   Raw response: {response_text[:200]}...")
        return False
    except Exception as e:
        print(f"❌ JSON generation failed for {model_name}: {e}")
        return False

def test_llm_options_replacement(model_name, model):
    """Test #LLMOptions replacement similar to your server"""
    try:
        test_prompt = "Generate #LLMOptions generic but expressive greetings. Each item should be a single sentence."
        llm_options_value = 10
        
        # Replace placeholder
        processed_prompt = test_prompt.replace("#LLMOptions", str(llm_options_value))
        
        generation_config = {
            "response_mime_type": "application/json",
            "temperature": 0.7
        }
        
        print(f"\n🔄 Testing #LLMOptions replacement with {model_name}...")
        print(f"Original prompt: {test_prompt}")
        print(f"Processed prompt: {processed_prompt}")
        
        response = model.generate_content(processed_prompt, generation_config=generation_config)
        response_text = response.text if hasattr(response, 'text') else str(response)
        
        # Try to parse as JSON
        parsed_json = json.loads(response_text)
        print(f"✅ #LLMOptions replacement test successful for {model_name}")
        print(f"   Response type: {type(parsed_json)}")
        print(f"   Length: {len(parsed_json) if isinstance(parsed_json, (list, dict)) else 'N/A'}")
        return True
        
    except Exception as e:
        print(f"❌ #LLMOptions replacement test failed for {model_name}: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("🧪 Starting LLM Direct Testing")
    print(f"🕐 Test time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Environment check
    if not check_environment():
        return False
    
    # Import test
    genai = test_basic_import()
    if not genai:
        return False
    
    # API configuration test
    if not test_api_configuration(genai):
        return False
    
    # Model initialization tests
    successful_models = test_model_initialization(genai)
    if not successful_models:
        print("❌ No models could be initialized")
        return False
    
    # Test each successful model
    all_tests_passed = True
    for model_name, model in successful_models:
        print(f"\n📋 Testing model: {model_name}")
        print("-" * 40)
        
        # Simple generation test
        if not test_simple_generation(model_name, model):
            all_tests_passed = False
        
        # JSON generation test
        if not test_json_generation(model_name, model):
            all_tests_passed = False
        
        # LLM options replacement test
        if not test_llm_options_replacement(model_name, model):
            all_tests_passed = False
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 All tests passed! LLM is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return all_tests_passed

if __name__ == "__main__":
    # Run the async test
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
