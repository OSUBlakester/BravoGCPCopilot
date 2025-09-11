#!/usr/bin/env python3
"""
Quick test script to debug mood context in LLM responses
"""

import requests
import json
import sys

def test_mood_context(mood_value=None):
    """Test if mood context is being included in LLM responses"""
    
    # Test URL - adjust for your deployment
    base_url = "https://test-bravo-copilot-792020467983.us-central1.run.app"
    
    # First, set a mood if provided
    if mood_value:
        print(f"Setting mood to: {mood_value}")
        user_info_response = requests.post(
            f"{base_url}/api/user-info",
            headers={"Content-Type": "application/json"},
            json={
                "userInfo": "Test user for mood debugging",
                "currentMood": mood_value
            }
        )
        print(f"Set mood response: {user_info_response.status_code}")
        if user_info_response.status_code != 200:
            print(f"Failed to set mood: {user_info_response.text}")
            return
    
    # Test LLM endpoint with a simple prompt
    test_prompt = "Generate a brief greeting message for me. Include 3 simple options."
    
    print(f"\nTesting LLM with prompt: '{test_prompt}'")
    
    llm_response = requests.post(
        f"{base_url}/llm",
        headers={"Content-Type": "application/json"},
        json={"prompt": test_prompt}
    )
    
    print(f"LLM Response Status: {llm_response.status_code}")
    
    if llm_response.status_code == 200:
        try:
            response_data = llm_response.json()
            print("\nLLM Response:")
            print("=" * 50)
            print(response_data.get("response", "No response field"))
            print("=" * 50)
            
            # Check if the response seems mood-appropriate
            response_text = response_data.get("response", "").lower()
            if mood_value:
                mood_lower = mood_value.lower()
                print(f"\nAnalyzing response for mood '{mood_value}':")
                if mood_lower == "happy" and any(word in response_text for word in ["wonderful", "great", "amazing", "fantastic", "cheerful"]):
                    print("✅ Response seems happy-appropriate")
                elif mood_lower == "sad" and any(word in response_text for word in ["sorry", "understand", "here for you", "comfort"]):
                    print("✅ Response seems sad-appropriate")
                else:
                    print("⚠️  Response doesn't clearly reflect the mood")
            
        except json.JSONDecodeError:
            print(f"Non-JSON response: {llm_response.text}")
    else:
        print(f"Error: {llm_response.text}")

if __name__ == "__main__":
    mood = sys.argv[1] if len(sys.argv) > 1 else "Happy"
    test_mood_context(mood)
