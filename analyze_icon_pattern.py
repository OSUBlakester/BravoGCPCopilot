import json

# Load the already-extracted JSON
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/all_pages_FINAL.json', 'r') as f:
    all_data = json.load(f)

# Get page 0007 (pages keyed by page_id)
pages = all_data.get('pages', {})
page_0007 = pages.get('0007')

if not page_0007:
    print("Page 0007 not found!")
    exit(1)

# Find buttons with icons but no speech
icon_no_speech = []
for button in page_0007.get('buttons', []):
    if button.get('icon') and not button.get('speech'):
        icon_no_speech.append(button)

print(f"Found {len(icon_no_speech)} buttons with icons but no speech in page 0007\n")

# Show details of first few
for i, btn in enumerate(icon_no_speech[:5]):
    print(f"{i+1}. Seq {btn['sequence']}: {btn['name']}")
    print(f"   Icon: {btn['icon']}")
    print(f"   Speech: {btn['speech']}")
    print(f"   Functions: {btn.get('functions', [])}")
    print(f"   Full: {json.dumps(btn, indent=6)}")
    print()

# Analyze what these buttons have in common
print("=== PATTERN ANALYSIS ===")
print(f"Total with icons but no speech: {len(icon_no_speech)}")

# Check functions
has_functions = [b for b in icon_no_speech if b.get('functions')]
no_functions = [b for b in icon_no_speech if not b.get('functions')]

print(f"  - With functions: {len(has_functions)}")
print(f"  - Without functions: {len(no_functions)}")

# Check navigation
has_nav = [b for b in icon_no_speech if b.get('navigation_type')]
print(f"  - With navigation: {len(has_nav)}")

# Check if all are non-navigation
if len(has_nav) == 0:
    print("  → ALL icon buttons with no speech have NO navigation or functions")
    print("  → These might be DISPLAY-ONLY buttons (icons with no action)")
