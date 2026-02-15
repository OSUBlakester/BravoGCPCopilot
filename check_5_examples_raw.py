import zlib
import struct
import json

# Load the MTI file
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/max user 1 2026 feb.mti', 'rb') as f:
    f.readline()  # Skip header
    f.read(4)     # Skip 4 bytes
    f.read(2)     # Skip CRLF
    compressed_data = f.read()

data = zlib.decompress(compressed_data)

# Test buttons to check
test_buttons = [
    ('0001', 17),  # unnamed POSS_M1
    ('0001', 20),  # unnamed DET_M1
    ('0009', 11),  # GO BACK
    ('000b', 0),   # Go to Kurzweil
    ('000b', 5),   # Spell
]

def find_button(page_id_str, sequence):
    """Find button in MTI data"""
    page_id = int(page_id_str, 16)
    page_id_bytes = struct.pack('<H', page_id)
    target_marker = b'm\x00\x04\xfd' + page_id_bytes + bytes([sequence])
    
    pos = data.find(target_marker)
    return pos

for page_id, seq in test_buttons:
    pos = find_button(page_id, seq)
    
    if pos != -1:
        print(f"\n{'='*70}")
        print(f"Button {page_id}/{seq} found at offset {pos}")
        print(f"{'='*70}")
        
        # Get 300 bytes
        button_data = data[pos:pos+300]
        
        # Show hex
        print("\nHex dump (first 300 bytes):")
        for i in range(0, min(len(button_data), 150), 32):
            chunk = button_data[i:i+32]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            print(f"{i:3d}: {hex_str:<96} | {ascii_str}")
        
        # Parse the button
        byte_9 = data[pos+9] if pos+9 < len(data) else 0
        print(f"\nFormat indicator (byte_9): 0x{byte_9:02x} ({byte_9})")
        
        # Check for markers
        search_region = data[pos+10:pos+150]
        
        markers = {
            'SET-PAGE PERM (FF 80 8C)': b'\xff\x80\x8c',
            'SET-PAGE TEMP (FF 80 8D)': b'\xff\x80\x8d',
            'CLEAR-DISPLAY (FF 80 3A FE)': b'\xff\x80\x3a\xfe',
            'PROMPT-MARKER (FF 80 7B FE)': b'\xff\x80{\xfe',
            '0xA4 markers': b'\xa4',
            'GO-BACK (FF 81 05 FE)': b'\xff\x81\x05\xfe',
        }
        
        print("\nMarkers found:")
        for name, marker in markers.items():
            if marker in search_region:
                idx = search_region.find(marker)
                print(f"  ✓ {name} at offset +{10+idx}")
            else:
                print(f"  ✗ {name}")
        
        # Try to extract button name
        print(f"\nButton data around name area:")
        # Show bytes 10-30 which usually contain name
        name_area = data[pos+10:pos+50]
        print(f"  Bytes 10-50: {repr(name_area)}")
        
    else:
        print(f"\nButton {page_id}/{seq}: NOT FOUND in MTI")
