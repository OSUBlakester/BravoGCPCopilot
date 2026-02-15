import zlib
import struct

# Load the MTI file
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/max user 1 2026 feb.mti', 'rb') as f:
    f.readline()  # Skip header
    f.read(4)     # Skip 4 bytes
    f.read(2)     # Skip CRLF
    compressed_data = f.read()

data = zlib.decompress(compressed_data)

# Find button 0001/11 (GO BACK)
# Search for: m\x00\x04\xfd followed by page ID
# Page ID 0001 in little-endian is 0x0100 = bytes [0x01, 0x01]
# But might be stored as 0x0100, so let's search more carefully

page_id_bytes = struct.pack('<H', 0x0100)  # 0001 in little-endian
target_marker = b'm\x00\x04\xfd' + page_id_bytes + b'\x0b'  # seq 11

pos = data.find(target_marker)
if pos != -1:
    print(f"Found button 0001/11 at offset {pos}")
    
    # Show the raw bytes
    button_data = data[pos:pos+200]
    print(f"\nFirst 200 bytes (hex):")
    for i in range(0, len(button_data), 32):
        chunk = button_data[i:i+32]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"{i:3d}: {hex_str:<96} | {ascii_str}")
    
    print(f"\n=== Analysis ===")
    print("Looking for markers:")
    
    # Check for various markers
    byte_9 = data[pos+9]
    print(f"byte_9 (format indicator): 0x{byte_9:02x} ({byte_9})")
    
    # Look for SET-PAGE markers (FF 80 8C or FF 80 8D)
    search_region = data[pos+10:pos+150]
    
    if b'\xff\x80\x8c' in search_region:
        set_page_pos = search_region.find(b'\xff\x80\x8c')
        print(f"  ✓ Found SET-PAGE PERMANENT at offset {pos+10+set_page_pos}")
        
        # Show what's before and after
        print(f"\n  Before SET-PAGE (25 bytes):")
        before_data = search_region[max(0, set_page_pos-25):set_page_pos]
        print(f"    {before_data.hex()}")
        print(f"    {repr(before_data)}")
        
        print(f"\n  After SET-PAGE (25 bytes):")
        after_data = search_region[set_page_pos+3:set_page_pos+28]
        print(f"    {after_data.hex()}")
        print(f"    {repr(after_data)}")
    
    if b'\xff\x80\x8d' in search_region:
        set_page_pos = search_region.find(b'\xff\x80\x8d')
        print(f"  ✓ Found SET-PAGE TEMPORARY at offset {pos+10+set_page_pos}")
    
    # Check for 0xA4 markers (used in the else branch)
    if b'\xa4' in search_region:
        a4_pos = search_region.find(b'\xa4')
        print(f"  ✓ Found 0xA4 marker at offset {pos+10+a4_pos}")
    else:
        print(f"  ✗ No 0xA4 markers found (this button uses FF 80 8C/8D, not 0xA4)")
    
    # Check for PROMPT-MARKER (FF 80 7B FE)
    if b'\xff\x80{\xfe' in search_region:
        pm_pos = search_region.find(b'\xff\x80{\xfe')
        print(f"  ✓ Found PROMPT-MARKER at offset {pos+10+pm_pos}")
    else:
        print(f"  ✗ No PROMPT-MARKER found")
    
    # Check for CLEAR-DISPLAY (FF 80 3A FE)
    if b'\xff\x80\x3a\xfe' in search_region:
        cd_pos = search_region.find(b'\xff\x80\x3a\xfe')
        print(f"  ✓ Found CLEAR-DISPLAY at offset {pos+10+cd_pos}")
    else:
        print(f"  ✗ No CLEAR-DISPLAY found")
    
else:
    print("Button not found! Trying alternative search...")
    
    # Try searching just for the marker and sequence
    pattern = b'm\x00\x04\xfd'
    pos = 0
    count = 0
    while True:
        pos = data.find(pattern, pos)
        if pos == -1:
            break
        
        # Check if this is page 0001, sequence 11
        if pos + 10 < len(data):
            page_bytes = data[pos+4:pos+6]
            seq = data[pos+6]
            
            if page_bytes == b'\x01\x01' and seq == 11:
                print(f"Found at {pos}: page={page_bytes.hex()}, seq={seq}")
                break
        
        pos += 1
        count += 1
        if count > 100000:
            print("Searched 100k records, not found")
            break
