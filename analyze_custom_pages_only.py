import json

# Load the JSON
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/all_pages_FINAL.json', 'r') as f:
    all_data = json.load(f)

pages = all_data.get('pages', {})

# Analyze missing speech for ACTIONABLE buttons on CUSTOM pages only
# Exclude: ZZ pages, VS pages
total_custom_pages = 0
total_actionable_custom = 0
actionable_missing_speech = 0
excluded_zz = 0
excluded_vs = 0
examples = []

for page_id, page_data in pages.items():
    page_name = page_data.get('inferred_name', '')
    
    # Skip ZZ pages
    if 'ZZ' in page_name:
        excluded_zz += len(page_data.get('buttons', []))
        continue
    
    # Skip VS pages
    if page_name.startswith('VS'):
        excluded_vs += len(page_data.get('buttons', []))
        continue
    
    # This is a custom page
    total_custom_pages += 1
    
    for button in page_data.get('buttons', []):
        # Check if button is actionable (has navigation OR functions)
        has_nav = bool(button.get('navigation_type'))
        has_func = bool(button.get('functions'))
        
        if has_nav or has_func:
            total_actionable_custom += 1
            
            # Check if missing speech
            if not button.get('speech'):
                actionable_missing_speech += 1
                
                # Collect examples
                if len(examples) < 20:
                    nav_target = button.get('navigation_target', '') or ''
                    functions = button.get('functions', []) or []
                    
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

print("=" * 80)
print("ACTIONABLE BUTTONS ON CUSTOM PAGES (EXCLUDING ZZ and VS)")
print("=" * 80)
print()
print(f"Custom pages analyzed: {total_custom_pages}")
print(f"Buttons excluded (ZZ pages): {excluded_zz}")
print(f"Buttons excluded (VS pages): {excluded_vs}")
print()
print(f"Total actionable buttons (nav or functions) on custom pages: {total_actionable_custom}")
print(f"Missing speech: {actionable_missing_speech}")
print(f"With speech: {total_actionable_custom - actionable_missing_speech}")
if total_actionable_custom > 0:
    print(f"Percentage missing: {100*actionable_missing_speech/total_actionable_custom:.1f}%")
print()

if actionable_missing_speech > 0:
    print(f"Examples of actionable buttons on custom pages missing speech:\n")
    for i, ex in enumerate(examples[:15], 1):
        print(f"{i}. {ex['page']}/{ex['seq']}: {ex['name']}")
        print(f"   Page: {ex['page_name']}")
        if ex['icon']:
            print(f"   Icon: {ex['icon']}")
        if ex['nav_type']:
            print(f"   Navigation: {ex['nav_type']} → {ex['nav_target']}")
        if ex['functions']:
            print(f"   Functions: {ex['functions']}")
        print()
else:
    print("✓ No missing speech on custom pages!")
