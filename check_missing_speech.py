#!/usr/bin/env python3
import json

with open('all_pages_FINAL.json') as f:
    data = json.load(f)

pages = data['pages']
missing_speech = []
for page_id, page_data in list(pages.items())[:20]:  # Check first 20 pages
    buttons = page_data.get('buttons', [])
    for btn in buttons:
        if btn.get('name') and not btn.get('speech'):
            # Exclude ZZ/navigation buttons
            if btn['name'] not in ['ZZ', 'Home', 'GO-BACK-PAGE']:
                missing_speech.append(f"{page_id}/{btn['name']}")

print(f"Sample missing speech buttons (first 20 pages): {len(missing_speech)}")
for item in missing_speech[:20]:
    print(f"  {item}")
