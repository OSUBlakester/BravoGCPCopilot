#!/usr/bin/env python3

"""
Analyze the exact cache content issue for Brady's profile
"""

def analyze_brady_data():
    """Analyze Brady's data structure and token estimation"""
    
    # Brady's actual user info as you provided
    brady_user_info = """Default user info.The user is Brady Thomas.  
Brady's name is pronounced "BRAY-DEE"
Brady was born on May 13, 1999, man who lives in Highlands Ranch, Colorado with his mother, Anne and Father, Blake.
Brady was born with a genetic condition called KCNQ2.  Brady has severe developmental disabilities.  Brady is non-verbal and uses AAC to communicate.  Brady uses a manual wheelchair. Brady is entirely tube-fed with Kate Farms formula.  
Brady loves the Denver Broncos and Oklahoma State Cowboys sports teams.  He also enjoys the other Denver-area professional sports teams and the Colorado State University Rams sports teams."""
    
    # Simulate what would be in cache context
    combined_content = """You are Bravo, an AI communication assistant designed for AAC (Augmentative and Alternative Communication) users. You help users communicate by providing relevant response options based on their context, relationships, location, activities, and conversation history.

Your role is to:
- Generate 3-7 contextually appropriate response options
- Consider the user's current mood, location, people present, and recent activities
- Take into account relationships with friends and family
- Be aware of upcoming events, birthdays, and holidays
- Reference recent conversations and diary entries when relevant
- Format responses as a JSON array with "option" and "summary" keys

Context Information:

## User Profile
"""
    combined_content += brady_user_info
    combined_content += """

## Friends Family
Brady's family includes his mother Anne and father Blake. [Additional family/friends data would be here]

## User Settings
[Settings data would be here]

## Holidays Birthdays
[Birthday/holiday data would be here]
"""
    
    print("🔍 Brady Data Analysis")
    print("=" * 60)
    
    print(f"📋 Brady's user info content:")
    print(f"Length: {len(brady_user_info)} characters")
    print(f"Preview: {brady_user_info[:100]}...")
    
    print(f"\n📊 Combined cache content analysis:")
    print(f"Total length: {len(combined_content)} characters") 
    
    # Token estimation (same logic as server)
    estimated_tokens = len(combined_content) // 4
    print(f"Estimated tokens: {estimated_tokens}")
    print(f"Meets 512 token threshold: {'✅ YES' if estimated_tokens >= 512 else '❌ NO'}")
    
    print(f"\n🔍 Potential Issues:")
    print(f"1. Data parsing: Brady's info starts with 'Default user info.' - is this handled correctly?")
    print(f"2. Cache creation: With {estimated_tokens} tokens, cache should definitely be created")
    print(f"3. Cache retrieval: Is the cached content being used during LLM calls?")
    print(f"4. Context assembly: Is Brady's detailed info making it to the LLM prompt?")
    
    print(f"\n💡 Debugging Steps:")
    print(f"1. Check if cache is actually being created (not just attempted)")
    print(f"2. Verify cache content includes Brady's specific details")
    print(f"3. Confirm LLM receives Brady's info in prompt context")
    print(f"4. Test if issue is in cache creation vs cache utilization")

if __name__ == "__main__":
    analyze_brady_data()
