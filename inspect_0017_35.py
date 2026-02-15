import zlib
import struct

# Load the MTI file
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/max user 1 2026 feb.mti', 'rb') as f:
    f.readline()  # Skip header
    f.read(4)     # Skip 4 bytes
    f.read(2)     # Skip CRLF
    compressed_data = f.read()

data = zlib.decompress(compressed_data)

# Find button 0017/35
page_id = 0x0017
sequence = 35
page_id_bytes = struct.pack('<H', page_id)
target_marker = b'm\x00\x04\xfd' + page_id_bytes + bytes([sequence])

pos = data.find(target_marker)

if pos != -1:
    print(f"Button 0017/35 found at offset {pos}")
    print()
    
    # Get 250 bytes
    button_data = data[pos:pos+250]
    
    print("Hex dump:")
    for i in range(0, min(len(button_data), 150), 32):
        chunk = button_data[i:i+32]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"{i:3d}: {hex_str:<96} | {ascii_str}")
    
    print()
    print("Details:")
    byte_9 = data[pos+9] if pos+9 < len(data) else 0
    print(f"byte_9 (format): 0x{byte_9:02x} ({byte_9})")
    
    # Show name area (bytes 10-40)
    print()
    print(f"Name area (bytes 10-40):")
    name_area = data[pos+10:pos+40]
    print(f"  Hex: {name_area.hex()}")
    print(f"  Repr: {repr(name_area)}")
    
    # Look for markers
    search_region = data[pos+10:pos+150]
    
    print()
    print("Markers:")
    if b'\xa4' in search_region:
        idx = search_region.find(b'\xa4')
        print(f"  ✓ 0xA4 marker at offset +{10+idx}")
    if b'\xff\x80\x8c' in search_region:
        idx = search_region.find(b'\xff\x80\x8c')
        print(f"  ✓ SET-PAGE PERM at offset +{10+idx}")
    if b'\xff\x80\x8d' in search_region:
        idx = search_region.find(b'\xff\x80\x8d')
        print(f"  ✓ SET-PAGE TEMP at offset +{10+idx}")
    if b'\r\n' in search_region:
        idx = search_region.find(b'\r\n')
        print(f"  ✓ CRLF at offset +{10+idx}")
    
    # Check what's between name and CRLF
    print()
    crlf_pos = search_region.find(b'\r\n')
    if crlf_pos > 0:
        content = search_region[:crlf_pos]
        print(f"Content from start to CRLF ({len(content)} bytes):")
        print(f"  Hex: {content.hex()}")
        print(f"  Repr: {repr(content)}")

else:
    print("Button 0017/35 NOT FOUND")
