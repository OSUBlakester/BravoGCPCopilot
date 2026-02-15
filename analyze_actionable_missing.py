import json

# Load the JSON
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/all_pages_FINAL.json', 'r') as f:
    all_data = json.load(f)

pages = all_data.get('pages', {})

# Analyze missing speech for ACTIONABLE buttons (have nav OR functions)
total_actionable = 0
actionable_missing_speech = 0
examples = []

for page_id, page_data in pages.items():
    page_name = page_data.get('inferred_name', '')
    
    # Skip entire page if it has ZZ
    if 'ZZ' in page_name:
        continue
    
    for button in page_data.get('buttons', []):
        # Check if button is actionable (has navigation OR functions)
        has_nav = bool(button.get('navigation_type'))
        has_func = bool(button.get('functions'))
        
        if has_nav or has_func:
            total_actionable += 1
            
            # Check if missing speech
            if not button.get('speech'):
                actionable_missing_speech += 1
                
                # Collect examples
                if len(examples) < 15:
                    nav_target = button.get('navigation_target', '') or ''
                    functions = button.get('functions', []) or []
                    has_zz = 'ZZ' in nav_target or 'ZZ' in ' '.join(functions)
                    
                    examples.append({
                        'page': page_id,
                        'page_name': page_name,
                        'seq': button['sequence'],
                        'name': button['name'] or '(no name)',
                        'icon': button['icon'],
                        'nav_type': button.get('navigation_type'),
                        'nav_target': nav_target,
                        'functions': functions,
                        'has_zz': has_zz
                    })

print("=== ACTIONABLE BUTTONS ANALYSIS (EXCLUDING ALL ZZ PAGES) ===\n")
print(f"Total actionable buttons (nav or functions): {total_actionable}")
print(f"Missing speech: {actionable_missing_speech}")
print(f"With speech: {total_actionable - actionable_missing_speech}")
print(f"Percentage missing: {100*actionable_missing_speech/total_actionable:.1f}%")
print()

if actionable_missing_speech > 0:
    print(f"Examples of actionable buttons missing speech:\n")
    for i, ex in enumerate(examples[:10], 1):
        zz_note = " [HAS ZZ]" if ex['has_zz'] else ""
        print(f"{i}. {ex['page']}/{ex['seq']}: {ex['name']}{zz_note}")
        print(f"   Page: {ex['page_name']}")
        if ex['icon']:
            print(f"   Icon: {ex['icon']}")
        if ex['nav_type']:
            print(f"   Navigation: {ex['nav_type']} → {ex['nav_target']}")
        if ex['functions']:
            print(f"   Functions: {ex['functions']}")
        print()
