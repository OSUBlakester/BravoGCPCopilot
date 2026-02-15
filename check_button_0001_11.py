import json

# Load the JSON
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/all_pages_FINAL.json', 'r') as f:
    all_data = json.load(f)

pages = all_data.get('pages', {})

# Get the first example: 0001/11 "GO BACK"
page_data = pages.get('0001', {})
for button in page_data.get('buttons', []):
    if button['sequence'] == 11:
        print("Button 0001/11 - GO BACK:")
        print(json.dumps(button, indent=2))
        
        # This button HAS:
        # - icon: REWIND
        # - navigation: PERMANENT to 1c17
        # - functions: SET-PAGE
        # But NO speech!
        
        print("\n=== Analysis ===")
        print("Expected to have speech because:")
        print("  ✓ Has icon (REWIND)")
        print("  ✓ Has functions (SET-PAGE)")
        print("  ✓ Is actionable (navigation)")
        print("\nBut speech is: null")
        print("\nPossible causes:")
        print("  1. Speech data exists in MTI but parsing failed")
        print("  2. Speech extraction code doesn't handle this specific format")
        print("  3. The button truly has no speech in MTI")
        
        break
