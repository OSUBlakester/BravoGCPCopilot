#!/usr/bin/env python3
"""
Test Production Search Prioritization

This script will test if the search prioritization fix is working in production
by checking the actual results from a live deployment.
"""

import requests
import json
import sys

def test_production_search(base_url="https://your-app-url.com"):
    """Test the production search API to see if prioritization is working."""
    
    print("🎯 Testing Production Search Prioritization")
    print("=" * 50)
    
    # Test the button search endpoint
    endpoint = f"{base_url}/api/symbols/button-search"
    
    test_cases = [
        {"query": "home", "expected_first": "home"},
        {"query": "tablet", "expected_first": "tablet"},
        {"query": "catch", "expected_first": "catch"}
    ]
    
    for test in test_cases:
        query = test["query"]
        expected = test["expected_first"]
        
        print(f"\n🔍 Testing query: '{query}'")
        print(f"   Expected first tag: '{expected}'")
        
        try:
            params = {"q": query, "limit": 5}
            response = requests.get(endpoint, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                symbols = data.get("symbols", [])
                
                if symbols:
                    first_symbol = symbols[0]
                    name = first_symbol.get("name", "unknown")
                    tags = first_symbol.get("tags", [])
                    first_tag = tags[0] if tags else "no_tags"
                    score = first_symbol.get("match_score", 0)
                    
                    print(f"   ✅ Found {len(symbols)} results")
                    print(f"   🥇 Top result: {name}")
                    print(f"   🏷️  First tag: '{first_tag}'")
                    print(f"   📊 Score: {score}")
                    
                    if first_tag.lower() == expected.lower():
                        print(f"   🎉 SUCCESS: Prioritization working correctly!")
                    else:
                        print(f"   ❌ ISSUE: Expected '{expected}' but got '{first_tag}'")
                        
                        # Show more results for debugging
                        print(f"   📋 All results:")
                        for i, symbol in enumerate(symbols[:3]):
                            s_name = symbol.get("name", "unknown")
                            s_tags = symbol.get("tags", [])
                            s_first_tag = s_tags[0] if s_tags else "no_tags"
                            s_score = symbol.get("match_score", 0)
                            print(f"      {i+1}. {s_name} (first tag: '{s_first_tag}', score: {s_score})")
                else:
                    print(f"   ⚠️  No results found")
                    
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎊 Production search test complete!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        print("Please provide your production URL:")
        print("python3 test_production_search.py https://your-app-url.com")
        sys.exit(1)
    
    test_production_search(base_url)