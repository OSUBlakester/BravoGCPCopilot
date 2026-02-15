import json

# Load the JSON
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/all_pages_FINAL.json', 'r') as f:
    all_data = json.load(f)

pages = all_data.get('pages', {})

# Analyze missing speech, EXCLUDING buttons with "ZZ"
total_buttons = 0
total_with_icon_and_nav = 0
total_missing_speech = 0
actionable_missing_speech = 0
zz_buttons = 0

examples = []

for page_id, page_data in pages.items():
    for button in page_data.get('buttons', []):
        total_buttons += 1
        
        # Check if button has ZZ
        nav_target = button.get('navigation_target', '') or ''
        functions = button.get('functions', []) or []
        functions_str = ' '.join(functions) if functions else ''
        has_zz = 'ZZ' in nav_target or 'ZZ' in functions_str
        
        # Count buttons with icons and navigation
        if button.get('icon') and (button.get('navigation_type') or button.get('functions')):
            total_with_icon_and_nav += 1
        
        # Count missing speech
        if not button.get('speech'):
            total_missing_speech += 1
            
            # Count actionable missing speech (icon + nav/functions, NO ZZ)
            if button.get('icon') and (button.get('navigation_type') or button.get('functions')) and not has_zz:
                actionable_missing_speech += 1
                
                # Collect examples
                if len(examples) < 10:
                    examples.append({
                        'page': page_id,
                        'seq': button['sequence'],
                        'name': button['name'] or '(no name)',
                        'icon': button['icon'],
                        'nav_type': button.get('navigation_type'),
                        'nav_target': nav_target,
                        'functions': functions
                    })
            
            if has_zz:
                zz_buttons += 1

print("=== MISSING SPEECH ANALYSIS (EXCLUDING ZZ BUTTONS) ===\n")
print(f"Total buttons: {total_buttons}")
print(f"Buttons with icons + navigation: {total_with_icon_and_nav}")
print(f"Total missing speech: {total_missing_speech}")
print(f"  - With ZZ targets/functions: {zz_buttons}")
print(f"  - Actionable (NO ZZ): {actionable_missing_speech}")
print()

if actionable_missing_speech > 0:
    print(f"Examples of REAL missing speech (no ZZ):\n")
    for ex in examples:
        print(f"  {ex['page']}/{ex['seq']}: {ex['name']} (icon: {ex['icon']})")
        print(f"    Navigation: {ex['nav_type']} → {ex['nav_target']}")
        if ex['functions']:
            print(f"    Functions: {ex['functions']}")
        print()
else:
    print("No actionable missing speech buttons found (all are ZZ)!")
