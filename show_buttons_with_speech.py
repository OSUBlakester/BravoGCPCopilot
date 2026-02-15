import json

# Load the JSON
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/all_pages_FINAL.json', 'r') as f:
    all_data = json.load(f)

pages = all_data['pages']

# Find some buttons WITH speech that have icons and navigation
buttons_with_speech = []

for page_id, page_data in pages.items():
    for button in page_data['buttons']:
        if (button.get('icon') and 
            button.get('speech') and 
            (button.get('navigation_type') or button.get('functions')) and
            'ZZ' not in str(button.get('navigation_target', '')) and
            'ZZ' not in str(button.get('functions', ''))):
            
            buttons_with_speech.append({
                'page': page_id,
                'seq': button['sequence'],
                'name': button['name'],
                'icon': button['icon'],
                'speech': button['speech'],
                'nav': button['navigation_type'],
                'nav_target': button['navigation_target'],
                'functions': button['functions']
            })
            
            if len(buttons_with_speech) >= 10:
                break
    if len(buttons_with_speech) >= 10:
        break

print("=" * 80)
print("EXAMPLE BUTTONS WITH SPEECH, ICON, AND NAVIGATION (NO ZZ)")
print("=" * 80)

for b in buttons_with_speech:
    print(f"\n{b['page']}/{b['seq']}: {repr(b['name'])}")
    print(f"  Icon: {b['icon']}")
    print(f"  Speech: {repr(b['speech'])}")
    print(f"  Navigation: {b['nav']} → {b['nav_target']}")
    if b['functions']:
        print(f"  Functions: {b['functions']}")
