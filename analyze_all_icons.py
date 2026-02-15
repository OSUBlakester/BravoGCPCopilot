import json

# Load the JSON
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/all_pages_FINAL.json', 'r') as f:
    all_data = json.load(f)

pages = all_data.get('pages', {})

# Check all icon+no-speech buttons across ALL pages
total_icon_no_speech = 0
total_with_nav_or_func = 0
total_without_nav_or_func = 0

icon_examples = []

for page_id, page_data in pages.items():
    for button in page_data.get('buttons', []):
        if button.get('icon') and not button.get('speech'):
            total_icon_no_speech += 1
            
            has_nav = bool(button.get('navigation_type'))
            has_func = bool(button.get('functions'))
            
            if has_nav or has_func:
                total_with_nav_or_func += 1
                # Collect examples that DO have nav or func
                icon_examples.append({
                    'page': page_id,
                    'seq': button['sequence'],
                    'name': button['name'],
                    'icon': button['icon'],
                    'nav': button.get('navigation_type'),
                    'nav_target': button.get('navigation_target'),
                    'functions': button.get('functions')
                })
            else:
                total_without_nav_or_func += 1

print(f"=== ALL ICON BUTTONS WITH NO SPEECH ===")
print(f"Total: {total_icon_no_speech}")
print(f"  - With navigation or functions: {total_with_nav_or_func}")
print(f"  - Without navigation or functions: {total_without_nav_or_func}")
print()

if total_with_nav_or_func > 0:
    print(f"Found {len(icon_examples)} buttons with icons, no speech, BUT WITH nav/functions:")
    print("(These are actionable - might have speech that was missed)")
    print()
    for ex in icon_examples[:10]:
        print(f"  {ex['page']}/{ex['seq']}: {ex['name']} (icon: {ex['icon']})")
        print(f"    Nav: {ex['nav']} → {ex['nav_target']}")
        if ex['functions']:
            print(f"    Functions: {ex['functions']}")
    
    if len(icon_examples) > 10:
        print(f"  ... and {len(icon_examples)-10} more")
else:
    print("NO icon buttons with navigation or functions found!")
    print("→ All 4,467 icon buttons are display-only (no action, no speech)")
    print("→ These may INTENTIONALLY have no speech!")
