import zlib
import json

# Load the compressed MTI file
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/max user 1 2026 feb.mti', 'rb') as f:
    # Skip the header line: "v500 1 NUVOICE\r\n"
    f.readline()
    
    # Skip 4 mystery bytes and CRLF
    f.read(4)
    f.read(2)
    
    # Rest is zlib compressed data
    compressed_data = f.read()
    decompressed = zlib.decompress(compressed_data)

# Find records for page 0007
page_id = '0007'
page_records = []
offset = 0

while offset < len(decompressed):
    if offset + 3 > len(decompressed):
        break
    
    # Check for record start (0xFF 0x90)
    if decompressed[offset:offset+2] == b'\xff\x90':
        # Found a record - check if it's page 0007
        record_start = offset
        offset += 2  # Skip 0xFF 0x90
        
        # Read page ID (2 bytes, big-endian)
        if offset + 2 > len(decompressed):
            break
        page_hex = decompressed[offset:offset+2].hex().upper()
        page_id_str = f"{page_hex[0:2]}{page_hex[2:4]}".lower()
        
        if page_id_str == '0007':
            # Find the next record to determine length
            next_record = decompressed.find(b'\xff\x90', offset + 2)
            if next_record == -1:
                record_data = decompressed[record_start:]
            else:
                record_data = decompressed[record_start:next_record]
            
            page_records.append({
                'offset': record_start,
                'length': len(record_data),
                'data': record_data[:500]  # First 500 bytes
            })
            
            offset += 2
            continue
        else:
            offset += 2
            continue
    else:
        offset += 1

print(f"Found {len(page_records)} records for page 0007")
print("\nRecord Info:")
for i, rec in enumerate(page_records[:1]):  # Just look at first record
    print(f"\nRecord {i}: offset={rec['offset']}, length={rec['length']}")
    print(f"First 500 bytes (hex):")
    print(rec['data'].hex())
    print(f"\nFirst 500 bytes (repr):")
    print(repr(rec['data']))

# Now let's specifically look for button data in 0007
# Button format: FF 9x [data]
print("\n\n=== Looking for buttons in page 0007 ===")
if len(page_records) > 0:
    record_data = page_records[0]['data']
    offset = 0
    button_count = 0
    
    # Look for button markers (FF 9x)
    while offset < len(record_data) - 10:
        if record_data[offset:offset+1] == b'\xff':
            marker = record_data[offset+1:offset+2]
            if marker[0] >= 0x90 and marker[0] <= 0x9f:  # Button marker range
                button_num = marker[0] - 0x90
                print(f"\nButton {button_num} at offset {offset}:")
                print(f"  Next 50 bytes (hex): {record_data[offset:offset+50].hex()}")
                button_count += 1
                if button_count >= 5:
                    break
        offset += 1
