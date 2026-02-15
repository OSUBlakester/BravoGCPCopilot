import json

# Load the JSON to see what names were extracted
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/all_pages_FINAL.json', 'r') as f:
    all_data = json.load(f)

# Check our 5 test buttons
test_buttons = [
    ('0001', 17),  # unnamed POSS_M1
    ('0001', 20),  # unnamed DET_M1
    ('0009', 11),  # GO BACK
    ('000b', 0),   # Go to Kurzweil
    ('000b', 5),   # Spell
]

print("=" * 80)
print("EXTRACTED DATA FOR 5 TEST BUTTONS")
print("=" * 80)

for page_id, seq in test_buttons:
    page_data = all_data['pages'].get(page_id)
    if page_data:
        buttons = [b for b in page_data['buttons'] if b['sequence'] == seq]
        if buttons:
            b = buttons[0]
            print(f"\n{page_id}/{seq}:")
            print(f"  Name: {repr(b['name'])}")
            print(f"  Icon: {b['icon']}")
            print(f"  Speech: {repr(b['speech'])}")
            print(f"  Navigation: {b['navigation_type']} → {b['navigation_target']}")
            print(f"  Functions: {b['functions']}")
        else:
            print(f"\n{page_id}/{seq}: NOT FOUND in page")
    else:
        print(f"\n{page_id}/{seq}: Page not found")
