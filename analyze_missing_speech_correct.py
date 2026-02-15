import json

# Load the JSON
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/all_pages_FINAL.json', 'r') as f:
    all_data = json.load(f)

pages = all_data.get('pages', {})

# Analyze missing speech, EXCLUDING:
# 1. Buttons on pages with "ZZ" in the page name
# 2. Buttons with "ZZ" in their targets/functions
total_buttons = 0
total_missing_speech = 0
actionable_missing_speech = 0
zz_page_buttons = 0
zz_button_buttons = 0

examples = []

for page_id, page_data in pages.items():
    page_name = page_data.get('inferred_name', '')
    
    # Skip entire page if it has ZZ
    if 'ZZ' in page_name:
        zz_page_buttons += len(page_data.get('buttons', []))
        continue
    
    for button in page_data.get('buttons', []):
        total_buttons += 1
        
        # Check if button has ZZ in targets/functions
        nav_target = button.get('navigation_target', '') or ''
        functions = button.get('functions', []) or []
        functions_str = ' '.join(functions) if functions else ''
        has_zz = 'ZZ' in nav_target or 'ZZ' in functions_str
        
        # Count missing speech
        if not button.get('speech'):
            total_missing_speech += 1
            
            # Count actionable missing speech (NO ZZ anywhere)
            if not has_zz:
                actionable_missing_speech += 1
                
                # Collect examples
                if len(examples) < 15:
                    examples.append({
                        'page': page_id,
                        'page_name': page_name,
                        'seq': button['sequence'],
                        'name': button['name'] or '(no name)',
                        'icon': button['icon'],
                        'nav_type': button.get('navigation_type'),
                        'nav_target': nav_target,
                        'functions': functions
                    })
            else:
                zz_button_buttons += 1

print("=== MISSING SPEECH ANALYSIS (EXCLUDING ALL ZZ PAGES) ===\n")
print(f"Total buttons on non-ZZ pages: {total_buttons}")
print(f"Total missing speech: {total_missing_speech}")
print(f"  - With ZZ in targets/functions: {zz_button_buttons}")
print(f"  - Actionable (NO ZZ anywhere): {actionable_missing_speech}")
print(f"\nButtons on ZZ pages (excluded): {zz_page_buttons}")
print()

if actionable_missing_speech > 0:
    print(f"Examples of REAL missing speech:\n")
    for i, ex in enumerate(examples[:10], 1):
        print(f"{i}. {ex['page']}/{ex['seq']}: {ex['name']} (icon: {ex['icon']})")
        print(f"   Page: {ex['page_name']}")
        print(f"   Navigation: {ex['nav_type']} → {ex['nav_target']}")
        if ex['functions']:
            print(f"   Functions: {ex['functions']}")
        print()
else:
    print("No actionable missing speech buttons found (all are on ZZ pages or have ZZ targets)!")
