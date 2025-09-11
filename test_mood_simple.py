#!/usr/bin/env python3
"""
Simple test script to check if mood context shows up in LLM responses
This only tests the LLM endpoint without authentication
"""

import requests
import json

def test_mood_simple():
    """Test if mood context appears in LLM responses"""
    
    # Test URL - Updated to match new deployment
    base_url = "https://test.talkwithbravo.com"
    
    # Test LLM endpoint with a simple prompt that should show mood influence
    test_prompt = "Generate 3 greeting options for me. Make them appropriate for my current mood."
    
    print(f"Testing LLM with prompt: '{test_prompt}'")
    print(f"URL: {base_url}/llm")
    
    try:
        llm_response = requests.post(
            f"{base_url}/llm",
            headers={"Content-Type": "application/json"},
            json={"prompt": test_prompt},
            timeout=30
        )
        
        print(f"LLM Response Status: {llm_response.status_code}")
        
        if llm_response.status_code == 200:
            try:
                response_data = llm_response.json()
                print("\nLLM Response:")
                print("=" * 60)
                print(response_data.get("response", "No response field"))
                print("=" * 60)
                
                # Check if response mentions mood or seems personalized
                response_text = response_data.get("response", "").lower()
                if any(word in response_text for word in ["mood", "feeling", "happy", "sad", "excited", "calm"]):
                    print("✅ Response mentions mood-related terms")
                else:
                    print("⚠️  Response doesn't clearly mention mood")
                    
            except json.JSONDecodeError:
                print(f"Non-JSON response: {llm_response.text}")
        else:
            print(f"Error: {llm_response.status_code}")
            print(f"Response: {llm_response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_mood_simple()
