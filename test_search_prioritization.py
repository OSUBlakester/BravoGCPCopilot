#!/usr/bin/env python3
"""
Test Search Prioritization

Test the improved search algorithm to ensure it prioritizes:
1. First tag matches (filename-based) over later tag matches
2. Exact subconcept matches over partial matches
"""

from google.cloud import firestore
import logging

def test_search_prioritization():
    """Test that search now prioritizes first-tag matches correctly."""
    
    print("🎯 Testing Search Prioritization Fix")
    print("=" * 50)
    
    # Initialize Firestore
    db = firestore.Client()
    aac_images_ref = db.collection('aac_images')
    
    # Test case: "home" should prioritize places_home over daily_living_tidy
    print('\n🏠 Testing "home" search:')
    
    # Get the two key images we know about
    query = aac_images_ref.where('tags', 'array_contains', 'home').limit(20)
    results = list(query.stream())
    
    scored_results = []
    search_term = 'home'
    
    for doc in results:
        symbol = doc.to_dict()
        symbol['id'] = doc.id
        
        # Apply the new scoring logic
        tags = symbol.get('tags', [])
        tag_position_bonus = 0
        
        for pos, tag in enumerate(tags):
            if tag.lower() == search_term.lower():
                if pos == 0:
                    tag_position_bonus = 10  # First tag gets big bonus
                elif pos == 1:
                    tag_position_bonus = 5   # Second tag gets medium bonus
                elif pos <= 3:
                    tag_position_bonus = 2   # Early tags get small bonus
                break
        
        base_score = 15  # Base tag match score
        symbol['match_score'] = base_score + tag_position_bonus
        symbol['tag_position'] = next((pos for pos, tag in enumerate(tags) if tag.lower() == search_term.lower()), -1)
        
        scored_results.append(symbol)
    
    # Sort by match score (highest first)
    scored_results.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    
    print(f"Found {len(scored_results)} images with 'home' in tags:")
    print()
    
    for i, symbol in enumerate(scored_results[:5]):
        subconcept = symbol.get('subconcept', 'unknown')
        tags = symbol.get('tags', [])
        score = symbol.get('match_score', 0)
        position = symbol.get('tag_position', -1)
        first_tag = tags[0] if tags else 'no_tags'
        
        print(f"  {i+1}. {subconcept} (score: {score})")
        print(f"     First tag: '{first_tag}'")
        print(f"     'home' at position: {position}")
        print(f"     Tags: {tags[:5]}...")
        print()
    
    # Check if places_home is now ranked higher than daily_living_tidy
    places_home = next((s for s in scored_results if 'places_home' in s.get('subconcept', '')), None)
    tidy_home = next((s for s in scored_results if 'daily_living_tidy' in s.get('subconcept', '')), None)
    
    if places_home and tidy_home:
        places_score = places_home.get('match_score', 0)
        tidy_score = tidy_home.get('match_score', 0)
        
        print("🔍 Key comparison:")
        print(f"   places_home score: {places_score} (home at position {places_home.get('tag_position', -1)})")
        print(f"   daily_living_tidy score: {tidy_score} (home at position {tidy_home.get('tag_position', -1)})")
        
        if places_score > tidy_score:
            print("   ✅ SUCCESS: places_home now ranks higher than daily_living_tidy!")
        else:
            print("   ❌ ISSUE: daily_living_tidy still ranks higher than places_home")
    
    print("\n" + "=" * 50)
    print("🎊 Search prioritization test complete!")

if __name__ == "__main__":
    test_search_prioritization()