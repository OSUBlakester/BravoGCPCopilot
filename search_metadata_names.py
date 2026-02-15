import zlib
import json

# Load the MTI file
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/max user 1 2026 feb.mti', 'rb') as f:
    f.readline()  # Skip header
    f.read(4)
    f.read(2)
    compressed_data = f.read()

data = zlib.decompress(compressed_data)

# Load JSON to compare
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/all_pages_FINAL.json', 'r') as f:
    all_data = json.load(f)

# Get all button names from page 0017 that should have speech according to JSON
page_0017 = all_data['pages']['0017']
buttons_with_speech = [b for b in page_0017['buttons'] if b.get('speech')]
buttons_no_speech = [b for b in page_0017['buttons'] if not b.get('speech')]

print("Page 0017 Summary:")
print(f"  Buttons WITH speech: {len(buttons_with_speech)}")
print(f"  Buttons WITHOUT speech: {len(buttons_no_speech)}")
print()

print("Buttons WITHOUT speech in extracted JSON:")
for b in buttons_no_speech[:10]:
    print(f"  {b['sequence']:3d}: {b['name']:30s}")
print()

# Now search metadata for these button names
print("Searching for button names in metadata section (around offset 900000+)...")
print()

metadata_start = 900000
metadata_end = 1000000

# Search for specific button names
test_names = ["Conversation page", "ski", "go back", "Home", "It will be"]

for name in test_names:
    search_bytes = name.encode('ascii', errors='ignore')
    
    # Search in metadata region
    pos = data.find(search_bytes, metadata_start, metadata_end)
    
    if pos != -1:
        print(f"Found '{name}' at offset {pos}")
        # Show context
        context = data[max(0, pos-50):pos+100]
        print(f"  Context: {repr(context)}")
        print()
    else:
        print(f"'{name}' NOT found in metadata region")
