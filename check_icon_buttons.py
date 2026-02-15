#!/usr/bin/env python3
import json

with open('all_pages_FINAL.json') as f:
    data = json.load(f)

pages = data['pages']

# Find buttons with icons but missing speech
examples = []
navigation_buttons = {'Home', 'GO-BACK-PAGE', 'ZZ', 'CLEAR', 'PREV PAGE', 'NEXT PAGE', 'PREVIOUS PAGE', 'NEXT PAGE'}

for page_id, page_data in pages.items():
    if len(examples) >= 5:
        break
    buttons = page_data.get('buttons', [])
    for btn in buttons:
        if len(examples) >= 5:
            break
        name = btn.get('name', '')
        speech = btn.get('speech')
        icon = btn.get('icon')
        functions = btn.get('functions') or []
        
        # Look for buttons with icon but no speech
        if icon and not speech and name and name not in navigation_buttons:
            # Skip if it's only navigation
            if functions and all(f.startswith(('SET-PAGE', 'GOTO-HOME', 'GO-BACK-PAGE', 'CLEAR')) for f in functions):
                continue
            
            examples.append({
                'page': page_id,
                'sequence': btn.get('sequence'),
                'name': name,
                'icon': icon,
                'speech': speech,
                'functions': functions,
                'full_button': btn
            })

print("5 Examples of buttons with icons but missing speech:\n")
for i, ex in enumerate(examples, 1):
    print(f"{i}. Page {ex['page']}, Seq {ex['sequence']}: '{ex['name']}'")
    print(f"   Icon: {ex['icon']}")
    print(f"   Speech: {ex['speech']}")
    print(f"   Functions: {ex['functions']}")
    print(f"   Full data: {json.dumps(ex['full_button'], indent=4)}")
    print()
