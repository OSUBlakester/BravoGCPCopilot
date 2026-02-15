#!/usr/bin/env python3
"""
Analyze why page 2516 is missing the GOTO-HOME button at sequence 1
"""
import json
import zlib
import struct

print("=" * 80)
print("Analysis: Missing GOTO-HOME Button in Page 2516")
print("=" * 80)

# Load the extracted JSON to see what we DO have
with open('all_pages_FINAL.json') as f:
    data = json.load(f)

page = data['pages']['2516']
print(f"\n1. EXTRACTED DATA FOR PAGE 2516")
print(f"   Page Name: {page['inferred_name']}")
print(f"   Total Buttons: {page['button_count']}")
print(f"\n   Sequences found: {sorted([b['sequence'] for b in page['buttons']])}")
print(f"   Missing sequences: {[i for i in range(max([b['sequence'] for b in page['buttons']])) if i not in [b['sequence'] for b in page['buttons']]][:10]}")

# Show first few buttons
print(f"\n   First 5 buttons:")
for i, btn in enumerate(page['buttons'][:5]):
    print(f"     [{i}] seq={btn['sequence']:2d} row={btn['row']} col={btn['col']}: '{btn['name']}' | functions={btn.get('functions')}")

# Now let's look at the RAW MTI file to see what's actually there
print(f"\n2. RAW MTI FILE ANALYSIS")
with open('AccentToBravo/max user 1 2026 feb.mti', 'rb') as f:
    # Skip the header like extract_mti_to_json.py does
    f.readline()  # Skip "v500 1 NUVOICE\r\n" line
    f.read(4)     # Skip 4 mystery bytes
    f.read(2)     # Skip CRLF
    # Rest is zlib compressed data
    compressed_data = f.read()

data_bytes = zlib.decompress(compressed_data)

print(f"   Decompressed size: {len(data_bytes)} bytes")

# Search for page 2516 button records
# MTI format: m\x00\x04\xfd[page_high][page_low][sequence][...]
page_marker = b'm\x00\x04\xfd\x25\x16'  # m\x00\x04\xfd + 0x25 0x16 (page 2516)

matches = []
pos = 0
while True:
    pos = data_bytes.find(page_marker, pos)
    if pos == -1:
        break
    
    # Get sequence number (byte at offset 6 from marker start)
    if pos + 7 < len(data_bytes):
        sequence = data_bytes[pos + 6]
        matches.append((pos, sequence))
    pos += 1

print(f"\n   Found {len(matches)} button records for page 2516:")
for pos, seq in matches[:10]:
    # Show the button data
    end_pos = min(pos + 80, len(data_bytes))
    button_data = data_bytes[pos:end_pos]
    
    # Extract key bytes
    byte_9 = data_bytes[pos + 9] if pos + 9 < len(data_bytes) else 0
    
    print(f"\n     Sequence {seq:2d} at position {pos}:")
    print(f"       byte_9 (format indicator) = 0x{byte_9:02x} ({byte_9})")
    print(f"       First 60 bytes: {button_data[:60]}")
    
    # Try to identify the format
    if byte_9 == 0:
        print(f"       → Format 2: Null-terminated (name_len = 0)")
    elif byte_9 > 100:
        print(f"       → Format 3: Offset name (name_len = {byte_9} > 100)")
    elif byte_9 in [0xCC, 0xFF, 0x87, 0xAF]:
        print(f"       → Format 5: Function-based (special marker 0x{byte_9:02x})")
    else:
        print(f"       → Format 1/4: Standard (name_len = {byte_9})")
    
    # Check for navigation markers
    if b'\xff\x80\x85\xfe' in button_data:
        print(f"       ✅ Contains GOTO-HOME marker (FF 80 85 FE)")
    if b'\xff\x809' in button_data:
        print(f"       ⚠️  Contains navigation marker FF 80 39")

print(f"\n3. DIAGNOSIS")
print(f"   The button at sequence 1 was found in the raw MTI file:")

# Find sequence 1
seq_1_data = None
for pos, seq in matches:
    if seq == 1:
        seq_1_data = (pos, data_bytes[pos:min(pos+120, len(data_bytes))])
        break

if seq_1_data:
    pos, raw_bytes = seq_1_data
    byte_9 = raw_bytes[9]
    
    print(f"\n   Position in file: {pos}")
    print(f"   byte_9 = 0x{byte_9:02x} ({byte_9})")
    print(f"   Raw bytes (first 80): {raw_bytes[:80]}")
    
    # Look for the issue
    print(f"\n   ISSUE IDENTIFIED:")
    
    # Check if byte_9 interpretation is causing the problem
    if byte_9 == 0x3f:  # 63
        print(f"   • byte_9 = 0x3f (63) suggests Format 1 with name_len=63")
        print(f"   • But the button data shows navigation markers very early:")
        
        # Find navigation marker
        nav_pos = raw_bytes.find(b'\xff\x80')
        if nav_pos != -1:
            print(f"     - Navigation marker (FF 80) found at offset {nav_pos}")
            print(f"     - This is BEFORE where a 63-byte name would end (offset 10+63=73)")
            print(f"   • This indicates the button is NOT Format 1")
            print(f"   • It's likely a Format 5 (function-based) button being misdetected")
        
        print(f"\n   ROOT CAUSE:")
        print(f"   The parser is treating this as Format 1 (standard) because byte_9 = 0x3f")
        print(f"   It tries to read 63 bytes for the button name starting at offset 10")
        print(f"   But the actual button has navigation markers much earlier (around offset 12)")
        print(f"   This causes the parser to read past the button boundary into the NEXT button")
        print(f"   When it finds 'm\\x00\\x04\\xfd' (next button marker) in the name data,")
        print(f"   it gets confused and skips/fails to create the button properly")
        
        print(f"\n   WHY IT'S SKIPPED:")
        # Look at what happens after trying to read 63 bytes
        name_region = raw_bytes[10:10+63]
        if b'm\x00\x04\xfd' in name_region:
            next_button_offset = name_region.find(b'm\x00\x04\xfd')
            print(f"   • The parser finds the NEXT button marker at offset {10 + next_button_offset}")
            print(f"   • This is inside where it expects the name to be (offsets 10-73)")
            print(f"   • The extraction code likely hits an error or continue statement")
            print(f"   • The button object is never created and added to the page")
    
    # Check what the button actually contains
    if b'\xff\x809\xfe' in raw_bytes:
        print(f"\n   BUTTON CONTENTS:")
        print(f"   • Contains navigation marker FF 80 39 FE")
        print(f"     (This is not GOTO-HOME which would be FF 80 85 FE)")
        print(f"     (This appears to be a different navigation function)")
else:
    print(f"   ❌ Sequence 1 was NOT found in the raw MTI file!")
    print(f"   This would indicate the user's expectation is incorrect")

print(f"\n4. SOLUTION OPTIONS")
print(f"   A. Fix the binary parser to correctly detect Format 5 buttons")
print(f"      when byte_9 doesn't match expected markers")
print(f"   B. Add special handling for ambiguous byte_9 values like 0x3f")
print(f"   C. Add post-processing to detect missing home buttons based on")
print(f"      grid position (row=0, col=0 often has home button)")
print(f"   D. Let the Bravo UI add a home button to pages during import")
print(f"      if one is missing")

print("\n" + "=" * 80)
