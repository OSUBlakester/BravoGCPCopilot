#!/usr/bin/env python3
import json

with open('AccentToBravo/all_pages_FINAL.json', 'r') as f:
    data = json.load(f)
    pages = data.get('pages', {})
    if '3f16' in pages:
        buttons = pages['3f16'].get('buttons', [])
        print(f"Page 3f16 has {len(buttons)} buttons")
        for i, btn in enumerate(buttons[:10]):
            print(f"  [{i}] name={btn.get('name')}, speech={btn.get('speech')}")
    else:
        print("Page 3f16 not found")
        # List first few pages
        print(f"First pages: {list(pages.keys())[:10]}")


