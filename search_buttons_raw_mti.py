import zlib
import struct
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

# Test buttons from page 0017
test_buttons = [
    (0x0017, 7, "Conversation page", True),   # HAS speech
    (0x0017, 0, "Home", False),                # NO speech
    (0x0017, 1, "go back", False),             # NO speech
    (0x0017, 35, "ski", False),                # NO speech
    (0x0017, 76, "It will be", False),         # NO speech
]

def search_button(page_id, sequence):
    """Search for button in decompressed MTI data"""
    page_id_bytes = struct.pack('<H', page_id)
    marker = b'm\x00\x04\xfd' + page_id_bytes + bytes([sequence])
    return data.find(marker)

print("=" * 100)
print("SEARCHING RAW MTI DATA FOR BUTTONS FROM PAGE 0017")
print("=" * 100)

for page_id, seq, name, has_speech in test_buttons:
    pos = search_button(page_id, seq)
    
    print(f"\nButton {page_id:04x}/{seq:2d}: {name:20s} (extracted: {has_speech})")
    
    if pos != -1:
        print(f"  Found at MTI offset {pos}")
        
        # Show the button data
        button_data = data[pos:pos+200]
        print(f"  Raw data (first 100 bytes): {repr(button_data[:100])}")
        
        # Look for CRLF
        crlf_pos = button_data.find(b'\r\n')
        if crlf_pos > 0:
            content = button_data[:crlf_pos]
            # Count non-marker bytes
            content_clean = content.replace(b'\xff\x80\x8c', b'').replace(b'\xff\x80\x8d', b'').replace(b'\xa4', b'')
            print(f"  Content until CRLF ({crlf_pos} bytes): {repr(content)}")
    else:
        print(f"  NOT FOUND in raw MTI")
