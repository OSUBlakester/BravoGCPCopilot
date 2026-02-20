#!/usr/bin/env python3
"""
Bulk import script for jokes database
Run this once to populate the jokes collection with initial data from icanhazdadjoke.com
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import the jokes_system module
sys.path.insert(0, str(Path(__file__).parent))

from jokes_system import bulk_import_icanhazdadjoke

async def main():
    print("🚀 Starting bulk import from icanhazdadjoke.com...")
    print("This will fetch jokes and auto-tag them with LLM")
    print("-" * 60)
    
    result = await bulk_import_icanhazdadjoke()
    
    print("-" * 60)
    if result['success']:
        print(f"✅ Successfully imported {result['imported_count']} jokes!")
        if result['errors']:
            print(f"⚠️  {len(result['errors'])} errors occurred:")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(result['errors']) > 5:
                print(f"   ... and {len(result['errors']) - 5} more")
    else:
        print(f"❌ Import failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
