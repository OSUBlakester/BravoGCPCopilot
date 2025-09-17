#!/usr/bin/env python3
"""
Test script for PiCom Symbol Processing API endpoints
Tests the new AAC symbol functionality added to server.py
"""

import asyncio
import json
import requests
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:3000"  # Adjust if your server runs on different port
TEST_USER_TOKEN = None  # You'll need to get an auth token from Firebase

async def test_symbol_endpoints():
    """Test all the new symbol processing endpoints"""
    
    print("🧪 Testing PiCom Symbol Processing Endpoints")
    print("=" * 50)
    
    # Test 1: Check analysis file exists
    print("\n1. Checking if analysis is ready...")
    analysis_file = Path("picom_ready_for_ai_analysis.json")
    if analysis_file.exists():
        print("✅ Analysis file exists")
        with open(analysis_file) as f:
            data = json.load(f)
        print(f"   📊 {data['statistics']['total_images']} images analyzed")
        print(f"   📂 {len(data['statistics']['categories'])} categories found")
    else:
        print("❌ Analysis file not found - need to run analysis first")
        return
    
    # Test 2: Get symbol statistics (no auth needed)
    print("\n2. Testing /api/symbols/stats...")
    try:
        response = requests.get(f"{BASE_URL}/api/symbols/stats")
        if response.status_code == 200:
            stats = response.json()
            print("✅ Stats endpoint working")
            print(f"   📊 Statistics source: {stats['source']}")
            if 'statistics' in stats:
                print(f"   🔢 Total symbols: {stats['statistics'].get('total_symbols', 'N/A')}")
        else:
            print(f"❌ Stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Stats error: {e}")
    
    # Test 3: Get categories (no auth needed)
    print("\n3. Testing /api/symbols/categories...")
    try:
        response = requests.get(f"{BASE_URL}/api/symbols/categories")
        if response.status_code == 200:
            categories = response.json()
            print("✅ Categories endpoint working")
            print(f"   📂 Found {len(categories['categories'])} categories:")
            for cat in categories['categories'][:5]:  # Show first 5
                print(f"      - {cat['name']}: {cat['count']} symbols")
        else:
            print(f"❌ Categories failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Categories error: {e}")
    
    # Test 4: Search symbols (no auth needed)
    print("\n4. Testing /api/symbols/search...")
    try:
        # Test search with query
        response = requests.get(f"{BASE_URL}/api/symbols/search", params={
            'query': 'happy',
            'limit': 5
        })
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Search endpoint working")
            print(f"   🔍 Found {results['total_found']} symbols matching 'happy'")
            if results['symbols']:
                print("   📋 Sample results:")
                for symbol in results['symbols'][:3]:
                    print(f"      - {symbol['name']} (categories: {', '.join(symbol['categories'])})")
        else:
            print(f"❌ Search failed: {response.status_code}")
            
        # Test category filter
        response = requests.get(f"{BASE_URL}/api/symbols/search", params={
            'category': 'emotions',
            'limit': 3
        })
        if response.status_code == 200:
            results = response.json()
            print(f"   🎭 Found {results['total_found']} emotion symbols")
    except Exception as e:
        print(f"❌ Search error: {e}")
    
    # Tests requiring authentication (admin endpoints)
    print("\n" + "=" * 50)
    print("🔐 Admin-only endpoints (require authentication)")
    print("   ℹ️  These require admin@talkwithbravo.com token")
    
    if TEST_USER_TOKEN:
        headers = {"Authorization": f"Bearer {TEST_USER_TOKEN}"}
        
        # Test analyze endpoint
        print("\n5. Testing /api/symbols/analyze-picom...")
        try:
            response = requests.post(f"{BASE_URL}/api/symbols/analyze-picom", headers=headers)
            if response.status_code == 200:
                result = response.json()
                print("✅ Analysis endpoint working")
                print(f"   📊 Ready for AI: {result.get('ready_for_ai', False)}")
            else:
                print(f"❌ Analysis failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Analysis error: {e}")
        
        # Test batch processing
        print("\n6. Testing /api/symbols/process-batch...")
        try:
            response = requests.post(f"{BASE_URL}/api/symbols/process-batch", 
                headers=headers,
                json={
                    'batch_size': 5,
                    'start_index': 0,
                    'category': 'emotions'
                }
            )
            if response.status_code == 200:
                result = response.json()
                print("✅ Batch processing working")
                print(f"   ✨ Processed {result['processed_count']} symbols")
                print(f"   📊 {result['error_count']} errors")
                print(f"   ➡️  Next batch starts at index {result['next_start_index']}")
            else:
                print(f"❌ Batch processing failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Batch processing error: {e}")
    else:
        print("   ⚠️  Skipping admin tests - no auth token provided")
        print("   💡 To test admin endpoints:")
        print("      1. Start the server")
        print("      2. Login as admin@talkwithbravo.com")
        print("      3. Get the JWT token from browser dev tools")
        print("      4. Set TEST_USER_TOKEN variable in this script")
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary")
    print("✅ Ready to implement PiCom symbol database!")
    print("📝 Next steps:")
    print("   1. Start server: python3 server.py")
    print("   2. Test endpoints manually or with Postman")
    print("   3. Process symbols in batches for better performance")
    print("   4. Add to your AAC interface for symbol search")

def main():
    """Run the tests"""
    print("Starting PiCom Symbol API Tests...")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Server is running at {BASE_URL}")
        else:
            print(f"⚠️  Server responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Server not running at {BASE_URL}")
        print("   💡 Start server first: python3 server.py")
        return
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return
    
    # Run async tests
    asyncio.run(test_symbol_endpoints())

if __name__ == "__main__":
    main()