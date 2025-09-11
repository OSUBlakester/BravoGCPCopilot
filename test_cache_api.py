#!/usr/bin/env python3

"""
Test script to verify cache functionality by making API calls to the deployed service
"""

import requests
import json
import time

# Test environment URL
BASE_URL = "https://bravo-aac-api-6spp73n6pa-uc.a.run.app"

def test_about_me_with_user_data():
    """Test if 'about me' responses contain user-specific data"""
    
    print("🧪 Testing 'About Me' functionality...")
    print("=" * 60)
    
    # Test account and user (using Blake/Blake which should have user data)
    account_id = "Blake"
    aac_user_id = "Blake"
    
    # Headers for the request
    headers = {
        "Content-Type": "application/json",
        "X-Account-ID": account_id,
        "X-AAC-User-ID": aac_user_id
    }
    
    # Test prompt for "About Me" - this should return personalized info if cache is working
    about_me_prompt = "Based on the details provided in the context, generate 5 different statements about the user. The statements should be in first person, as if the user was telling someone about the user. Statements can include information like age, family, disability and favorites. The statements should also be conversational, not just presenting a fact."
    
    payload = {
        "prompt": about_me_prompt
    }
    
    print(f"📡 Making request to: {BASE_URL}/llm")
    print(f"📋 Account ID: {account_id}")
    print(f"👤 AAC User ID: {aac_user_id}")
    print(f"💬 Prompt: {about_me_prompt[:100]}...")
    
    try:
        print(f"\n⏳ Sending request...")
        response = requests.post(f"{BASE_URL}/llm", headers=headers, json=payload, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Request successful!")
            
            try:
                response_data = response.json()
                print(f"\n📄 Response structure:")
                print(f"  Keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
                
                # Look for the actual response content
                if isinstance(response_data, dict):
                    if 'response' in response_data:
                        llm_response = response_data['response']
                        print(f"\n🤖 LLM Response:")
                        print(f"  Type: {type(llm_response)}")
                        
                        if isinstance(llm_response, list):
                            print(f"  Count: {len(llm_response)} items")
                            for i, item in enumerate(llm_response):
                                if isinstance(item, dict) and 'option' in item:
                                    option_text = item['option']
                                    print(f"    {i+1}. {option_text}")
                                    
                                    # Check for generic vs specific content
                                    generic_indicators = [
                                        "I am a person",
                                        "I like to",
                                        "I enjoy",
                                        "I am someone who",
                                        "My name is"
                                    ]
                                    
                                    specific_indicators = [
                                        "Blake",
                                        "family",
                                        "brother",
                                        "sister",
                                        "mom",
                                        "dad",
                                        "years old",
                                        "birthday"
                                    ]
                                    
                                    is_generic = any(indicator.lower() in option_text.lower() for indicator in generic_indicators)
                                    is_specific = any(indicator.lower() in option_text.lower() for indicator in specific_indicators)
                                    
                                    if is_specific:
                                        print(f"      ✅ Contains specific user data")
                                    elif is_generic:
                                        print(f"      ⚠️  Generic response - may lack user context")
                                    else:
                                        print(f"      ❓ Unclear specificity")
                        else:
                            print(f"  Content: {str(llm_response)[:500]}...")
                    else:
                        print(f"\n📄 Full response: {json.dumps(response_data, indent=2)[:1000]}...")
                else:
                    print(f"\n📄 Raw response: {response.text[:1000]}...")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"📄 Raw response: {response.text[:500]}...")
                
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"📄 Error response: {response.text[:500]}...")
            
    except requests.exceptions.Timeout:
        print(f"⏰ Request timed out after 30 seconds")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    
    return response.status_code == 200

def test_health_endpoint():
    """Test if the service is healthy"""
    print(f"\n🩺 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"📊 Health Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Service is healthy")
            return True
        else:
            print(f"❌ Service health check failed")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Cache Functionality in Deployed Environment")
    print("=" * 60)
    
    # First check if service is healthy
    if test_health_endpoint():
        # Test the main functionality
        success = test_about_me_with_user_data()
        
        if success:
            print(f"\n🎉 Test completed successfully!")
        else:
            print(f"\n❌ Test failed - check cache functionality")
    else:
        print(f"\n❌ Service is not healthy - cannot run tests")
