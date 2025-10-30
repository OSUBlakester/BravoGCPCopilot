#!/usr/bin/env python3
"""
Test the imagecreator search endpoint to verify tag position prioritization is working.
"""

from google.cloud import firestore

def test_imagecreator_logic():
    """Test the imagecreator search logic locally to verify the fix."""
    
    print("🎯 Testing imagecreator search logic fix")
    print("=" * 50)
    
    db = firestore.Client()
    
    # Simulate the imagecreator search for "home"
    search_term = "home"
    base_query = db.collection("aac_images").where("source", "==", "bravo_images")
    
    print(f"🔍 Searching for tag: '{search_term}'")
    
    # Search with array_contains like the endpoint does
    query = base_query.where("tags", "array_contains", search_term).limit(15)
    docs = list(query.stream())
    
    print(f"Found {len(docs)} documents")
    
    # Apply the new scoring logic
    scored_images = []
    
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        
        # Calculate tag position bonus
        match_score = 50  # Base score
        tags = data.get('tags', [])
        tag_position = -1
        
        for pos, tag_item in enumerate(tags):
            if tag_item.lower() == search_term.lower():
                tag_position = pos
                if pos == 0:
                    match_score += 20  # First tag gets big bonus
                elif pos == 1:
                    match_score += 10  # Second tag gets medium bonus
                elif pos <= 3:
                    match_score += 5   # Early tags get small bonus
                break
        
        data['match_score'] = match_score
        data['tag_position'] = tag_position
        scored_images.append(data)
    
    # Sort by match score (highest first)
    scored_images.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    
    print(f"\n📊 Results sorted by score:")
    print("-" * 50)
    
    for i, data in enumerate(scored_images[:5]):
        subconcept = data.get('subconcept', 'unknown')
        score = data.get('match_score', 0)
        position = data.get('tag_position', -1)
        first_tag = data.get('tags', ['no_tags'])[0]
        
        print(f"{i+1}. {subconcept}")
        print(f"   Score: {score} (position: {position}, first tag: '{first_tag}')")
        
        if 'places_home' in subconcept:
            print(f"   🎉 SUCCESS: places_home found at position {i+1}!")
        elif 'daily_living_tidy' in subconcept:
            print(f"   ⚠️  daily_living_tidy at position {i+1}")
        print()
    
    # Check if places_home is now ranked higher than daily_living_tidy
    places_home = next((data for data in scored_images if 'places_home' in data.get('subconcept', '')), None)
    tidy = next((data for data in scored_images if 'daily_living_tidy' in data.get('subconcept', '')), None)
    
    if places_home and tidy:
        places_idx = scored_images.index(places_home)
        tidy_idx = scored_images.index(tidy)
        
        print(f"🔍 Direct comparison:")
        print(f"   places_home: position {places_idx + 1}, score {places_home.get('match_score', 0)}")
        print(f"   daily_living_tidy: position {tidy_idx + 1}, score {tidy.get('match_score', 0)}")
        
        if places_idx < tidy_idx:
            print(f"   ✅ SUCCESS: places_home now ranks higher!")
        else:
            print(f"   ❌ ISSUE: daily_living_tidy still ranks higher")
    
    print("\n" + "=" * 50)
    print("🎊 Test complete!")

if __name__ == "__main__":
    test_imagecreator_logic()