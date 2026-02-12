#!/usr/bin/env python3
"""
Accent MTI File Extractor
Extracts pages and buttons from Accent .mti files and exports to JSON

Usage:
    python3 extract_mti_to_json.py <mti_file_path>
    
Output:
    all_pages_FINAL.json - Complete extracted data
"""

import sys
import zlib
import struct
import json
import re
from datetime import datetime


def extract_mti_file(mti_file_path):
    """
    Extract all pages and buttons from an Accent MTI file
    
    Args:
        mti_file_path: Path to the .mti file
        
    Returns:
        Dictionary with pages, buttons, and metadata
    """
    
    print(f"Reading MTI file: {mti_file_path}")
    
    # Read and decompress the MTI file
    # MTI files have format: v500 header line, 4 mystery bytes, CRLF, then zlib compressed data
    with open(mti_file_path, 'rb') as f:
        # Skip the header
        f.readline()  # Skip "v500 1 NUVOICE\r\n" line
        f.read(4)     # Skip 4 mystery bytes
        f.read(2)     # Skip CRLF
        
        # Rest is zlib compressed data
        compressed_data = f.read()
    
    print(f"Compressed data size: {len(compressed_data)} bytes")
    
    # Decompress the data
    try:
        data = zlib.decompress(compressed_data)
        print(f"Decompressed {len(data)} bytes")
    except Exception as e:
        print(f"Error decompressing: {e}")
        print("Extraction failed!")
        return None
    
    # PHASE 1: Parse metadata overlay records (button property extensions)
    # These records provide navigation data for buttons defined elsewhere
    # Format: m\x00\x04\xfd\x25\x16[XX][XX][flags][0x01][name_len][name]...\xff\x80\x8c[nav_target]\xfe
    print("Phase 1: Parsing button metadata overlays...")
    metadata_map = {}
    
    pos = 900000  # Metadata section starts around here
    end_metadata_pos = min(1000000, len(data))
    
    while pos < end_metadata_pos:
        idx = data.find(b'm\x00\x04\xfd\x25\x16', pos)
        if idx == -1 or idx >= end_metadata_pos:
            break
        
        try:
            record = data[idx:idx+250]
            
            # Metadata record structure:
            # 0-3: marker m\x00\x04\xfd
            # 4-7: ref bytes (25 16 XX XX) - overlay reference
            # 8-11: flags
            # 12: type byte (must be 0x01)
            # 13: name length
            # 14+: button name
            # ... \xff\x80\x8c[navigation_target]\xfe
            
            if len(record) < 20 or record[12] != 0x01:
                pos = idx + 1
                continue
            
            name_len = record[13]
            if name_len > 100 or name_len == 0:
                pos = idx + 1
                continue
            
            button_name = record[14:14+name_len].decode('latin-1', errors='replace').strip()
            
            # Extract navigation target using delimiter \xff\x80\x8c ... \xfe
            nav_start = record.find(b'\xff\x80\x8c')
            if nav_start > 0:
                nav_end = record.find(b'\xfe', nav_start + 3)
                if nav_end > nav_start:
                    nav_bytes = record[nav_start+3:nav_end]
                    nav_target_raw = nav_bytes.decode('latin-1', errors='replace').strip()
                    
                    # Navigation targets start with "0 " prefix (means SET-PAGE)
                    if nav_target_raw.startswith('0 '):
                        page_name = nav_target_raw[2:].strip()
                        
                        if button_name:
                            # Store mapping: button name → navigation target
                            metadata_map[button_name.lower()] = {
                                'navigation_target_name': page_name,
                                'ref_bytes': record[4:8].hex()
                            }
        
        except Exception:
            pass
        
        pos = idx + 1
    
    print(f"  Found {len(metadata_map)} button overlays with navigation data")
    if len(metadata_map) > 0:
        sample_names = list(metadata_map.keys())[:5]
        print(f"  Sample: {', '.join(sample_names)}")
    # Parse all m-records (button definitions)
    pages = {}
    page_names = {}  # Store 40XX metadata for page naming
    
    pos = 0
    button_count = 0
    format_stats = {
        'Format 1 - Standard': 0,
        'Format 2 - Null-terminated': 0,
        'Format 3 - Offset name': 0,
        'Format 4 - Simple speech': 0,
        'Format 5 - Function-based': 0,
        'Complex format': 0
    }
    
    print("Phase 2: Parsing button records...")
    
    while pos < len(data) - 20:
        # Progress indicator every 1000 buttons
        if button_count % 1000 == 0:
            print(f"  Processed {button_count} buttons... (pos={pos}/{len(data)})", flush=True)
        
        # Look for m-record marker: m\x00\x04\xfd
        if data[pos:pos+4] != b'm\x00\x04\xfd':
            pos += 1
            continue
        
        try:
            # Extract page ID (2 bytes, little-endian) and SWAP BYTES
            # MTI stores as 0x0004 but we display as 0x0400
            page_id_bytes = data[pos+4:pos+6]
            page_id_raw = struct.unpack('<H', page_id_bytes)[0]
            
            # Byte-swap the page ID: swap high and low bytes
            page_id_swapped = ((page_id_raw & 0xFF) << 8) | ((page_id_raw >> 8) & 0xFF)
            page_id_str = f"{page_id_swapped:04x}"
            
            # Extract sequence (1 byte)
            sequence = data[pos+6]
            
            # Calculate grid position
            row = sequence // 16
            col = sequence % 16
            
            # Extract button name based on format
            byte_9 = data[pos+9]
            extra_buttons = []
            
            # DEBUG for page 0301 seq 0
            if page_id_str == '0301' and sequence == 0:
                print(f"\nDEBUG 0301/0: byte_9={byte_9} (0x{byte_9:02x})")
                print(f"  Button data: {data[pos:pos+60]}")
            
            # DEBUG for page 0400 seq 0
            if page_id_str == '0400' and sequence == 0:
                print(f"\nDEBUG 0400/0: byte_9={byte_9} (0x{byte_9:02x})")
                print(f"  Button data: {data[pos:pos+100]}")
            
            # DEBUG for page 0400 seq 0
            if page_id_str == '0500' and sequence == 0:
                print(f"\nDEBUG 0500/0: byte_9={byte_9} (0x{byte_9:02x})")
                print(f"  Button data: {data[pos:pos+80]}")

            # DEBUG for page 2516 seq 1
            if page_id_str == '2516' and sequence == 1:
                print(f"\nDEBUG 2516/1: byte_9={byte_9} (0x{byte_9:02x}), pos={pos}")
                print(f"  Button data: {data[pos:pos+80]}")
            
            button_name = ""
            icon_name = None
            speech = None
            navigation_type = None
            navigation_target = None
            functions = []
            has_goto_home = False  # Track if GOTO-HOME is present
            
            # Format 5: Function-based (0xCC, 0xFF, 0x87, or 0xAF markers)
            # These have variable-length data, parse carefully
            # 0x87 and 0xAF buttons also use byte 13 for name_len (not bytes 10-11)
            if byte_9 in [0x87, 0xaf, 0xcc, 0xff] and pos + 14 < len(data):
                # Format 5: All 0xCC and 0xFF records
                # Name length can be at different locations:
                # Try byte 13 first (1-byte length, most common)
                name_len_13 = data[pos+13] if pos+13 < len(data) else 0
                # Also check bytes 10-11 (2-byte length, for some buttons with embedded nulls)
                name_len_10 = struct.unpack('<H', data[pos+10:pos+12])[0] if pos+12 < len(data) else 0
                
                # Heuristic: if byte 13 points to valid length, try it first
                # But if the name contains embedded null byte, use the 2-byte length instead
                name_len = name_len_13
                if 0 < name_len_13 < 100 and pos + 14 + name_len_13 < len(data):
                    # Check if there's an embedded null in the name OR right after it
                    # (If truncating at null, the null won't be in test_name but will be right after)
                    test_name = data[pos+14:pos+14+name_len_13]
                    byte_after = data[pos+14+name_len_13] if pos+14+name_len_13 < len(data) else 0xff
                    if (b'\x00' in test_name or byte_after == 0x00) and 0 < name_len_10 < 500 and name_len_10 > name_len_13:
                        # If the next bytes after the null look like function markers, keep name_len_13
                        next_after_null = data[pos+14+name_len_13+1:pos+14+name_len_13+3]
                        looks_like_marker = byte_after == 0x00 and (
                            next_after_null.startswith(b'\xff') or next_after_null.startswith(b'\xa4') or next_after_null.startswith(b'\xa0')
                        )
                        # If the next bytes repeat the name (duplication), keep name_len_13
                        next_after_null_long = data[pos+14+name_len_13+1:pos+14+name_len_13+1+len(test_name)]
                        looks_like_duplicate = byte_after == 0x00 and test_name and next_after_null_long.lower().startswith(test_name.lower())
                        if not looks_like_marker and not looks_like_duplicate:
                            # Name has embedded null or ends at null, use 2-byte length which should span the full text
                            name_len = name_len_10
                
                if 0 < name_len < 500:
                    # Extract name using the length - don't stop at \r\n since it might be intentional line break
                    name_start = pos + 14
                    name_end = name_start + name_len
                    
                    # Get name bytes and remove embedded nulls
                    name_bytes = data[name_start:name_end]
                    name_bytes = name_bytes.replace(b'\x00', b'')
                    # Also remove any CRLF line breaks (they're display formatting, not part of the text)
                    name_bytes = name_bytes.replace(b'\r\n', b'')
                    
                    # Strip everything from first control character onwards (metadata)
                    for i, byte_val in enumerate(name_bytes):
                        if byte_val < 0x20:
                            name_bytes = name_bytes[:i]
                            break
                    
                    button_name = name_bytes.decode('ascii', errors='ignore').rstrip()
                    
                    pos_cursor = pos + 14 + name_len
                    
                    # Skip null terminator if present
                    if pos_cursor < len(data) and data[pos_cursor] == 0:
                        pos_cursor += 1
                    
                    # Check for GO-BACK-PAGE pattern: FF 81 05 FE (before icon/functions)
                    button_end = data.find(b'\r\n', pos_cursor)
                    if button_end == -1:
                        button_end = min(pos_cursor + 120, len(data))
                    else:
                        button_end = min(button_end, pos_cursor + 120)
                    
                    search_region = data[pos_cursor:button_end]
                    go_back_page_pos = search_region.find(b'\xff\x81\x05\xfe')
                    
                    # Check for FF 80 navigation patterns (SET-PAGE, CLEAR-DISPLAY, GOTO-HOME)
                    clear_display_pos = search_region.find(b'\xff\x80\x3a\xfe')
                    set_page_perm_pos = search_region.find(b'\xff\x80\x8c')
                    set_page_temp_pos = search_region.find(b'\xff\x80\x8d')
                    goto_home_pos = search_region.find(b'\xff\x80\x85\xfe')
                    
                    if go_back_page_pos != -1:
                        # GO-BACK-PAGE function detected
                        navigation_type = 'GO-BACK-PAGE'
                        navigation_target = None
                        functions.append('GO-BACK-PAGE')
                        speech = None  # Navigation buttons have no speech
                        # Skip the rest of Format 5 processing
                    elif goto_home_pos != -1:
                        # GOTO-HOME function detected
                        navigation_type = 'PERMANENT'
                        navigation_target = '0400'  # Home page
                        functions.append('GOTO-HOME')
                        speech = None  # Navigation buttons have no speech
                    elif clear_display_pos != -1 or set_page_perm_pos != -1 or set_page_temp_pos != -1:
                        # FF 80 navigation pattern detected - handle like Format 3
                        # Process CLEAR-DISPLAY
                        if clear_display_pos != -1:
                            functions.append('CLEAR-DISPLAY')
                        
                        # Process SET-PAGE (PERMANENT or TEMPORARY)
                        if set_page_perm_pos != -1:
                            # Extract target page name between FF 80 8C and FE
                            target_start = set_page_perm_pos + 3
                            target_end = search_region.find(b'\xfe', target_start)
                            if target_end != -1:
                                target_name = search_region[target_start:target_end].decode('ascii', errors='ignore')
                                navigation_type = 'PERMANENT'
                                navigation_target = target_name
                                functions.append(f'SET-PAGE({target_name})')
                        elif set_page_temp_pos != -1:
                            # Extract target page name between FF 80 8D and FE
                            target_start = set_page_temp_pos + 3
                            target_end = search_region.find(b'\xfe', target_start)
                            if target_end != -1:
                                target_name = search_region[target_start:target_end].decode('ascii', errors='ignore')
                                navigation_type = 'TEMPORARY'
                                navigation_target = target_name
                                functions.append(f'SET-PAGE({target_name})')

                        # Handle PROMPT-MARKER in the search region (speech before, name after)
                        prompt_marker_pos = search_region.find(b'\xff\x80{\xfe')
                        has_prompt_marker = prompt_marker_pos != -1
                        set_page_pos = set_page_perm_pos if set_page_perm_pos != -1 else set_page_temp_pos
                        if has_prompt_marker:
                            # Speech is before PROMPT-MARKER; if SET-PAGE appears earlier, stop there
                            speech_end = prompt_marker_pos
                            if set_page_pos != -1 and set_page_pos < prompt_marker_pos:
                                speech_end = set_page_pos
                            speech_bytes = search_region[:speech_end]
                            # Remove the SET-PAGE marker if it's at the end of speech_bytes
                            if set_page_perm_pos != -1 and b'\xff\x80\x8c' in speech_bytes:
                                marker_pos = speech_bytes.rfind(b'\xff\x80\x8c')
                                if marker_pos >= 0:
                                    speech_bytes = speech_bytes[:marker_pos]
                            elif set_page_temp_pos != -1 and b'\xff\x80\x8d' in speech_bytes:
                                marker_pos = speech_bytes.rfind(b'\xff\x80\x8d')
                                if marker_pos >= 0:
                                    speech_bytes = speech_bytes[:marker_pos]
                            speech_bytes = speech_bytes.replace(b'\x00', b'').strip()
                            if speech_bytes:
                                speech = speech_bytes.decode('ascii', errors='ignore').strip()

                            # Name is after PROMPT-MARKER; if SET-PAGE appears after it, stop there
                            name_bytes = search_region[prompt_marker_pos + 4:]
                            if set_page_pos != -1 and set_page_pos > prompt_marker_pos:
                                name_bytes = search_region[prompt_marker_pos + 4:set_page_pos]
                            # Remove null bytes and filter control characters (< 0x20, except space)
                            name_bytes = bytes(b for b in name_bytes if b >= 0x20 or b == 0x09)
                            name_bytes = name_bytes.strip()
                            if name_bytes:
                                name_text = name_bytes.decode('ascii', errors='ignore').strip()
                                if name_text:
                                    button_name = name_text
                        
                        # Extract speech if present (between CLEAR-DISPLAY and SET-PAGE or vice versa)
                        if not speech and clear_display_pos != -1 and (set_page_perm_pos != -1 or set_page_temp_pos != -1):
                            set_page_pos = set_page_perm_pos if set_page_perm_pos != -1 else set_page_temp_pos
                            if clear_display_pos < set_page_pos:
                                # Speech is between CLEAR-DISPLAY and SET-PAGE
                                speech_start = clear_display_pos + 4
                                speech_bytes = search_region[speech_start:set_page_pos]
                                speech_bytes = speech_bytes.replace(b'\x00', b'').strip()
                                if speech_bytes:
                                    speech = speech_bytes.decode('ascii', errors='ignore').strip()
                            else:
                                # SET-PAGE comes before CLEAR-DISPLAY, no speech
                                speech = None

                        # If no explicit speech extracted, fall back to button name
                        # BUT: if PROMPT-MARKER is present, do NOT force speech = button_name
                        if not speech and button_name and button_name not in ['CLEAR-DISPLAY', 'GO-BACK-PAGE', ''] and not has_prompt_marker:
                            speech = button_name
                        else:
                            # Only one pattern present (SET-PAGE without CLEAR-DISPLAY or vice versa)
                            # Use button_name as speech if it exists and is meaningful
                            if button_name and button_name not in ['CLEAR-DISPLAY', 'GO-BACK-PAGE', ''] and not has_prompt_marker:
                                speech = button_name
                            else:
                                speech = None
                    else:
                        # Normal Format 5 processing (icon + function markers)
                        # Reset pos_cursor to after name for icon extraction
                        pos_cursor = pos + 14 + name_len
                        
                        # Extract icon
                        if pos_cursor < len(data):
                            icon_len = data[pos_cursor]
                            pos_cursor += 1
                            if 0 < icon_len < 50:
                                icon_name = data[pos_cursor:pos_cursor+icon_len].decode('ascii', errors='ignore')
                                pos_cursor += icon_len
                        
                        # Process function markers (0xA4)
                        while pos_cursor < len(data) - 10 and data[pos_cursor] == 0xa4:
                            func_type = data[pos_cursor+1]
                            pos_cursor += 2
                            
                            if func_type == 0x3a:  # Speech
                                # Find end of speech (next 0xA4 or CRLF)
                                speech_end = pos_cursor
                                while speech_end < len(data) - 2:
                                    if data[speech_end] == 0xa4 or data[speech_end] == 0xa0 or data[speech_end:speech_end+2] == b'\r\n':
                                        break
                                    speech_end += 1
                                speech_bytes = data[pos_cursor:speech_end]
                                speech_bytes = speech_bytes.replace(b'\x00', b'')  # Remove embedded nulls
                                speech_text = speech_bytes.decode('ascii', errors='ignore').strip()
                                # Only set speech if there's actual text (empty speech marker means no speech)
                                if speech_text:
                                    speech = speech_text
                                pos_cursor = speech_end
                                
                            elif func_type == 0x06:  # RANDOM-CHOICE
                                # Extract page reference (in parentheses)
                                ref_start = pos_cursor
                                while ref_start < len(data) and data[ref_start] != 0x28:  # '('
                                    ref_start += 1
                                ref_end = ref_start + 1
                                while ref_end < len(data) and data[ref_end] != 0x29:  # ')'
                                    ref_end += 1
                                if ref_start < ref_end:
                                    ref_page = data[ref_start+1:ref_end].decode('ascii', errors='ignore')
                                    functions.append(f'RANDOM-CHOICE({ref_page})')
                                pos_cursor = ref_end + 1
                                
                            elif func_type == 0x85:  # GO-BACK-PAGE
                                # This function returns to the previous page
                                navigation_type = 'GO-BACK-PAGE'
                                navigation_target = None
                                functions.append('GO-BACK-PAGE')
                                # Skip any trailing data (CRLF usually follows)
                                
                            elif func_type == 0x8b:  # GOTO-HOME
                                # Extract target (should be "home" in parentheses)
                                target_start = pos_cursor
                                while target_start < len(data) and data[target_start] != 0x28:
                                    target_start += 1
                                target_end = target_start + 1
                                while target_end < len(data) and data[target_end] != 0x29:
                                    target_end += 1
                                if target_start < target_end:
                                    navigation_target = '0400'  # Home page ID
                                    navigation_type = 'PERMANENT'
                                    functions.append('GOTO-HOME')
                                    has_goto_home = True  # Mark that we've seen GOTO-HOME
                                    speech = None  # GOTO-HOME buttons have no speech
                                pos_cursor = target_end + 1
                                
                            elif func_type in [0x8c, 0x8d]:  # Navigation
                                # Only set navigation if we haven't seen GOTO-HOME
                                if not has_goto_home:
                                    nav_type = 'PERMANENT' if func_type == 0x8c else 'TEMPORARY'
                                    # Extract target (in parentheses)
                                    target_start = pos_cursor
                                    while target_start < len(data) and data[target_start] != 0x28:
                                        target_start += 1
                                    target_end = target_start + 1
                                    while target_end < len(data) and data[target_end] != 0x29:
                                        target_end += 1
                                    if target_start < target_end:
                                        navigation_target = data[target_start+1:target_end].decode('ascii', errors='ignore')
                                        navigation_type = nav_type
                                    pos_cursor = target_end + 1
                                else:
                                    # Skip past the navigation marker but don't process it
                                    target_start = pos_cursor
                                    while target_start < len(data) and data[target_start] != 0x28:
                                        target_start += 1
                                    target_end = target_start + 1
                                    while target_end < len(data) and data[target_end] != 0x29:
                                        target_end += 1
                                    pos_cursor = target_end + 1
                        
                        # Check for CLEAR-DISPLAY marker (0xA0) after all 0xA4 markers
                        if pos_cursor < len(data) and data[pos_cursor] == 0xa0:
                            functions.append('CLEAR-DISPLAY')
                            pos_cursor += 1
                        
                        # If no speech was found via markers, check for inline speech
                        if not speech and button_name and not has_goto_home:
                            # Debug for page 2516 seq 5
                            if page_id_str == '2516' and sequence == 5:
                                print(f"DEBUG Format 5 normal path seq 5: button_name={repr(button_name)}, speech={repr(speech)}, has_goto_home={has_goto_home}, pos_cursor={hex(pos_cursor)}")
                            # Check if there's text after the icon that could be speech
                            # Look for text up to the next CRLF or 0xA4
                            speech_end = pos_cursor
                            while speech_end < len(data) - 2:
                                if data[speech_end:speech_end+2] == b'\r\n' or data[speech_end] == 0xa4:
                                    break
                                speech_end += 1
                            
                            if speech_end > pos_cursor:
                                speech_bytes = data[pos_cursor:speech_end]
                                speech_bytes = speech_bytes.replace(b'\x00', b'')
                                
                                # Strip everything from first control character onwards (metadata)
                                for i, byte_val in enumerate(speech_bytes):
                                    if byte_val < 0x20:
                                        speech_bytes = speech_bytes[:i]
                                        break
                                
                                speech_candidate = speech_bytes.decode('ascii', errors='ignore').strip()
                                # Only use if it's different from name and non-empty
                                if speech_candidate and speech_candidate != button_name:
                                    speech = speech_candidate
                                else:
                                    speech = button_name
                            else:
                                speech = button_name
                    
                    format_stats['Format 5 - Function-based'] += 1
                else:
                    # Invalid name length, skip
                    format_stats['Complex format'] += 1
                    pos += 1
                    continue
                    
            # Format 2: Null-terminated (name_len = 0)
            elif byte_9 == 0:
                # Skip null padding
                pos_cursor = pos + 10
                while pos_cursor < len(data) and data[pos_cursor] == 0:
                    pos_cursor += 1
                
                # Read full text until CRLF
                text_start = pos_cursor
                while pos_cursor < len(data) - 2:
                    if data[pos_cursor:pos_cursor+2] == b'\r\n':
                        break
                    pos_cursor += 1
                
                # Get the text bytes and strip leading/trailing null bytes
                text_bytes = data[text_start:pos_cursor]
                text_bytes = text_bytes.lstrip(b'\x00')  # Remove leading null bytes
                
                # Remove icon prefix patterns and extract icon name:
                # Pattern 1: \x08[ICON_NAME]![text] or ^[text]
                # Pattern 2: \x04-\x08[ICON_NAME]![text] or ^[text]
                # Pattern 3: [ICON_NAME]![text] (no control char)
                # Pattern 4: [ICON_NAME][Same text with different case] (e.g., "FLAGFlag Day")
                # Pattern 5: \x05PLANE (length-prefixed icon without separator)
                # The icon name is usually uppercase letters/numbers, ends with ! or ^
                
                # First, check if there's a length-prefix control character at the start
                if text_bytes and text_bytes[0] < 0x20 and text_bytes[0] > 0:
                    # This byte tells us the icon length
                    icon_len = text_bytes[0]
                    if icon_len < 20 and len(text_bytes) > icon_len:
                        # Extract the icon name
                        potential_icon = text_bytes[1:1+icon_len]
                        # Check if it looks like an icon (uppercase ASCII)
                        is_icon_name = all(
                            (65 <= b <= 90) or  # A-Z
                            (48 <= b <= 57) or  # 0-9
                            b == 95 or          # underscore
                            b == 126            # tilde
                            for b in potential_icon
                        )
                        if is_icon_name:
                            icon_name = potential_icon.decode('ascii', errors='ignore')
                            # Skip the control byte and icon name
                            text_bytes = text_bytes[1+icon_len:]
                
                # If no icon found yet, strip any remaining leading control characters
                while text_bytes and text_bytes[0] < 0x20:
                    text_bytes = text_bytes[1:]
                
                # Now check for icon pattern: [UPPERCASE_NAME]! or [UPPERCASE_NAME]^
                # Icon names are typically 4-8 uppercase letters/numbers followed by ! or ^
                exc_pos = text_bytes.find(b'!')
                caret_pos = text_bytes.find(b'^')
                
                # Use whichever separator comes first (or only one exists)
                sep_pos = -1
                if exc_pos != -1 and caret_pos != -1:
                    sep_pos = min(exc_pos, caret_pos)
                elif exc_pos != -1:
                    sep_pos = exc_pos
                elif caret_pos != -1:
                    sep_pos = caret_pos
                
                # If separator found, check if everything before it looks like an icon name
                if sep_pos != -1 and 0 < sep_pos <= 20:
                    prefix = text_bytes[:sep_pos]
                    # Icon names are typically uppercase ASCII with underscores/numbers
                    # Check if prefix looks like an icon name (mostly uppercase/numbers)
                    is_icon_name = all(
                        (65 <= b <= 90) or  # A-Z
                        (48 <= b <= 57) or  # 0-9
                        b == 95 or          # underscore
                        b == 126            # tilde
                        for b in prefix
                    )
                    if is_icon_name and len(prefix) >= 3:
                        # Save the icon name
                        icon_name = prefix.decode('ascii', errors='ignore')
                        # Skip the icon prefix in the text
                        text_bytes = text_bytes[sep_pos+1:]
                else:
                    # Pattern 4: Check for repeated word (e.g., "FLAGFlag Day")
                    # The icon is all-uppercase, but gets merged with title-case repeat
                    decoded = text_bytes.decode('ascii', errors='ignore')
                    if len(decoded) > 3:
                        # Try different lengths for the all-uppercase prefix
                        for icon_len in range(3, min(11, len(decoded))):
                            if all(c.isupper() or c in '0123456789_~' for c in decoded[:icon_len]):
                                # Check if text after this matches (case-insensitive)
                                rest = decoded[icon_len:]
                                if (len(rest) >= icon_len and
                                    rest[:icon_len].upper() == decoded[:icon_len]):
                                    # Found a match!
                                    icon_name = decoded[:icon_len]
                                    text_bytes = rest.encode('ascii', errors='ignore')
                                    break
                
                # Remove embedded null bytes that can truncate text
                # Example: "Merry Christ-\x00mas" should become "Merry Christ-mas"
                text_bytes = text_bytes.replace(b'\x00', b'')
                
                # Check for PROMPT-MARKER (FF 80 7B FE) which separates speech from button name
                # Structure: [speech]«PROMPT-MARKER»[button_name]
                # Or with navigation: [speech]«SET-PAGE(target)»«PROMPT-MARKER»[button_name]
                prompt_marker = text_bytes.find(b'\xff\x80{\xfe')
                
                if prompt_marker != -1:
                    # PROMPT-MARKER found - extract name from AFTER marker, speech from BEFORE marker
                    # Debug for buttons with "today"
                    if b'today' in text_bytes or page_id_str == '0917':
                        print(f"DEBUG PROMPT-MARKER: page {page_id_str} seq {sequence}")
                        print(f"  Full text_bytes: {text_bytes.hex()}")
                        print(f"  prompt_marker pos: {prompt_marker}")
                    
                    # Button name is everything after PROMPT-MARKER (strip control chars and whitespace)
                    name_bytes = text_bytes[prompt_marker + 4:]  # Skip the 4-byte marker
                    # Remove control characters
                    name_clean = []
                    for byte_val in name_bytes:
                        if byte_val >= 0x20:
                            name_clean.append(byte_val)
                        else:
                            break  # Stop at first control char
                    button_name = bytes(name_clean).decode('ascii', errors='ignore').strip()
                    
                    # Check for navigation markers in the content before PROMPT-MARKER
                    speech_bytes = text_bytes[:prompt_marker]
                    # Extract navigation if present
                    set_page_perm_marker = speech_bytes.find(b'\xff\x80\x8c')
                    set_page_temp_marker = speech_bytes.find(b'\xff\x80\x8d')
                    nav_marker_pos = -1
                    if set_page_perm_marker != -1 and set_page_temp_marker != -1:
                        nav_marker_pos = min(set_page_perm_marker, set_page_temp_marker)
                        navigation_type = 'PERMANENT' if set_page_perm_marker < set_page_temp_marker else 'TEMPORARY'
                    elif set_page_perm_marker != -1:
                        nav_marker_pos = set_page_perm_marker
                        navigation_type = 'PERMANENT'
                    elif set_page_temp_marker != -1:
                        nav_marker_pos = set_page_temp_marker
                        navigation_type = 'TEMPORARY'
                    
                    if nav_marker_pos != -1:
                        # Extract navigation target between marker and FE terminator
                        target_start = nav_marker_pos + 3  # Skip FF 80 8C/8D
                        target_end = speech_bytes.find(b'\xfe', target_start)
                        if target_end != -1:
                            navigation_target = speech_bytes[target_start:target_end].decode('ascii', errors='ignore')
                        # Speech is everything before navigation marker
                        speech_bytes = speech_bytes[:nav_marker_pos]
                    
                    # Clean and decode speech
                    speech_text = speech_bytes.decode('ascii', errors='ignore').strip()
                    # Only set speech if there's actual text (not empty or just whitespace)
                    if speech_text:
                        speech = speech_text
                    else:
                        speech = None
                    
                    # Set text_bytes to just button_name for downstream processing
                    text_bytes = button_name.encode('ascii', errors='ignore')
                
                # Check for navigation function markers and truncate text before them
                # SET-PAGE markers: FF 80 8C (PERMANENT) or FF 80 8D (TEMPORARY)
                # These appear in Format 2 buttons with navigation
                set_page_perm_marker = text_bytes.find(b'\xff\x80\x8c')
                set_page_temp_marker = text_bytes.find(b'\xff\x80\x8d')
                set_page_marker = -1
                if set_page_perm_marker != -1 and set_page_temp_marker != -1:
                    set_page_marker = min(set_page_perm_marker, set_page_temp_marker)
                elif set_page_perm_marker != -1:
                    set_page_marker = set_page_perm_marker
                elif set_page_temp_marker != -1:
                    set_page_marker = set_page_temp_marker
                
                # If navigation marker found, keep only text before it (strip trailing space)
                # BUT: Only if PROMPT-MARKER doesn't come after it!
                # First check if PROMPT-MARKER exists in text_bytes (before any truncation)
                has_prompt_marker = b'\xff\x80{\xfe' in text_bytes
                
                if set_page_marker != -1 and not has_prompt_marker:
                    # Only truncate if there's no PROMPT-MARKER after the SET-PAGE
                    text_bytes = text_bytes[:set_page_marker].rstrip()
                
                # Handle PROMPT-MARKER pattern in Format 2 (similar to Formats 5 and 3)
                # PROMPT-MARKER: FF 80 7B FE - speech before, name after
                prompt_marker_pos = text_bytes.find(b'\xff\x80{\xfe')
                
                
                if prompt_marker_pos != -1:
                    # Speech is everything before PROMPT-MARKER (but after any SET-PAGE)
                    # First check if SET-PAGE appears before PROMPT-MARKER
                    set_page_in_speech_perm = text_bytes.find(b'\xff\x80\x8c')
                    set_page_in_speech_temp = text_bytes.find(b'\xff\x80\x8d')
                    set_page_in_speech = -1
                    if set_page_in_speech_perm != -1 and set_page_in_speech_temp != -1:
                        set_page_in_speech = min(set_page_in_speech_perm, set_page_in_speech_temp)
                    elif set_page_in_speech_perm != -1:
                        set_page_in_speech = set_page_in_speech_perm
                    elif set_page_in_speech_temp != -1:
                        set_page_in_speech = set_page_in_speech_temp
                    
                    # If SET-PAGE appears before PROMPT-MARKER, extract speech before SET-PAGE
                    if set_page_in_speech != -1 and set_page_in_speech < prompt_marker_pos:
                        speech_bytes = text_bytes[:set_page_in_speech].strip()
                    else:
                        # Otherwise, speech is everything before PROMPT-MARKER
                        speech_bytes = text_bytes[:prompt_marker_pos].strip()
                    
                    if speech_bytes:
                        speech = speech_bytes.decode('ascii', errors='ignore').strip()
                    
                    # Name is everything after PROMPT-MARKER, up to null terminator or control char
                    name_start = prompt_marker_pos + 4  # Skip the 4-byte PROMPT-MARKER
                    # Find end of name (null terminator or control char)
                    name_end = name_start
                    while name_end < len(text_bytes) and text_bytes[name_end] >= 0x20:
                        name_end += 1
                    name_bytes = text_bytes[name_start:name_end]
                    # Filter out control characters from name
                    name_bytes = bytes(b for b in name_bytes if b >= 0x20 or b == 0x09)
                    if name_bytes:
                        button_name = name_bytes.decode('ascii', errors='ignore').strip()
                        full_text = button_name
                    else:
                        # If no name after marker, use the speech as button name
                        full_text = button_name
                
                # Only do duplicate checking and further text cleaning if PROMPT-MARKER wasn't found
                # (since PROMPT-MARKER handling already set button_name and speech)
                if prompt_marker_pos == -1:
                    # Pattern 5: Check for exact word duplication AFTER navigation marker removal
                    # (e.g., "peoplepeople" after marker stripped)
                    if icon_name is None:  # Only if we haven't extracted an icon yet
                        decoded = text_bytes.decode('ascii', errors='ignore')
                        # Check if first half equals second half (exact duplication)
                        if len(decoded) % 2 == 0 and len(decoded) >= 6:
                            half_len = len(decoded) // 2
                            first_half = decoded[:half_len]
                            second_half = decoded[half_len:]
                            if first_half == second_half:
                                # Duplicated word found, keep only first half
                                text_bytes = first_half.encode('ascii', errors='ignore')
                    
                    # Decode and clean the text
                    full_text = text_bytes.decode('ascii', errors='ignore')
                    # Remove trailing control characters and high-ASCII
                    while full_text and (ord(full_text[-1]) < 32 or ord(full_text[-1]) >= 127):
                        full_text = full_text[:-1]
                    # Remove trailing whitespace
                    full_text = full_text.rstrip()
                    # Remove trailing special characters that appear to be garbage
                    # Pattern 1: Single non-alphanumeric char preceded by space (like " <")
                    while full_text and len(full_text) >= 2:
                        if full_text[-2] == ' ' and not full_text[-1].isalnum() and full_text[-1] not in ["'", "!", "?", ".", ","]:
                            full_text = full_text[:-1].rstrip()
                        else:
                            break
                    # Pattern 1b: Single lowercase letter preceded by space (like " r") - likely garbage
                    if full_text and len(full_text) >= 2:
                        if full_text[-2] == ' ' and len(full_text[-1]) == 1 and full_text[-1].islower():
                            full_text = full_text[:-1].rstrip()
                    # Pattern 1c: Single digit or single uppercase letter preceded by space - likely garbage
                    # This handles cases like "Monday 8" or "Thursday G"
                    if full_text and len(full_text) >= 2:
                        if full_text[-2] == ' ' and len(full_text[-1]) == 1 and (full_text[-1].isdigit() or full_text[-1].isupper()):
                            full_text = full_text[:-1].rstrip()
                    # Pattern 2: Trailing punctuation that looks like garbage (single char, not common punctuation)
                    # Remove characters like '}', '<', etc. that appear at the end
                    if full_text and not full_text[-1].isalnum() and full_text[-1] not in ["'", "!", "?", ".", ",", ")", '"']:
                        # Check if the char before the special char is alphanumeric (suggests it's garbage)
                        if len(full_text) >= 2 and full_text[-2].isalnum():
                            full_text = full_text[:-1]
                    
                    # Pattern 3: Remove embedded control characters and anything after them
                    # This handles cases like "Jokes \x05SUN1B" where icon marker appears mid-string
                    control_char_pos = -1
                    for i, ch in enumerate(full_text):
                        if ord(ch) < 0x20:
                            control_char_pos = i
                            break
                    if control_char_pos != -1:
                        # Found control character, truncate at that position and strip trailing space
                        full_text = full_text[:control_char_pos].rstrip()
                    
                    button_name = full_text
                    speech = full_text  # Button speaks its own name
                else:
                    # PROMPT-MARKER was found, so button_name and speech already set above
                    pass

                
                format_stats['Format 2 - Null-terminated'] += 1
                
            # Format 3: Offset name (name_len > 100 - invalid marker)
            # NOTE: Excludes 0x87 which uses byte 13 like Format 5
            elif byte_9 > 100 and byte_9 != 0x87:
                # Check if this is a metadata page (40XX)
                is_metadata_page = page_id_str.startswith('40')
                
                # For Format 3, try bytes 10-11 first, but if that gives unreliable value,
                # use byte 13 as fallback (some Format 3 buttons store length there)
                name_len_from_10_11 = struct.unpack('<H', data[pos+10:pos+12])[0] if pos+12 < len(data) else 0
                name_len_from_13 = data[pos+13] if pos+13 < len(data) else 0
                
                # For metadata pages, extract name differently - just read until CRLF or control char
                if is_metadata_page:
                    name_start = pos + 14
                    name_end = name_start
                    # Read until CRLF or control character (except space)
                    while name_end < len(data) and name_end < name_start + 100:
                        if data[name_end:name_end+2] == b'\r\n':
                            break
                        if data[name_end] < 0x20 and data[name_end] != 0x00:
                            break
                        name_end += 1
                    name_bytes = data[name_start:name_end]
                    # Remove any embedded nulls in metadata names
                    name_bytes = name_bytes.replace(b'\x00', b'')
                    button_name = name_bytes.decode('ascii', errors='ignore').strip()
                    icon_name = None
                    
                    # DEBUG for page 4002 seq 1
                    if page_id_str == '4002' and sequence == 1:
                        print(f"DEBUG 4002/1: name_bytes={name_bytes.hex()}, button_name='{button_name}'")
                    
                    # Set cursor position
                    pos_cursor = name_end
                else:
                    # Normal Format 3 processing for non-metadata pages
                    # If bytes 10-11 give unreasonably large value, use byte 13
                    if name_len_from_10_11 > 200:
                        name_len = name_len_from_13
                    else:
                        name_len = name_len_from_10_11
                    
                    # Extract name, but stop at \r\n terminator
                    name_start = pos + 14
                    name_end = name_start
                    while name_end < name_start + name_len and name_end < len(data):
                        if data[name_end:name_end+2] == b'\r\n':
                            break
                        name_end += 1
                    name_bytes = data[name_start:name_end]
                    
                    # Remove icon prefix patterns
                    # Format 1: Length-prefixed icon (control char specifying length)
                    if name_bytes and name_bytes[0] < 0x20 and name_bytes[0] > 0:
                        icon_len = name_bytes[0]
                        if icon_len < 20 and len(name_bytes) > icon_len:
                            # Check if the icon section contains valid icon name characters
                            icon_section = name_bytes[1:1+icon_len]
                            is_icon_name = all(
                                (65 <= b <= 90) or (48 <= b <= 57) or b == 95 or b == 126
                                for b in icon_section
                            )
                            if is_icon_name:
                                icon_name = icon_section.decode('ascii', errors='ignore')
                                name_bytes = name_bytes[1+icon_len:]
                    
                    # Format 2: Separator-based icon (icon name + ! or ^)
                    # First strip any remaining leading control chars
                    while name_bytes and name_bytes[0] < 0x20:
                        name_bytes = name_bytes[1:]
                    
                    exc_pos = name_bytes.find(b'!')
                    caret_pos = name_bytes.find(b'^')
                    sep_pos = -1
                    if exc_pos != -1 and caret_pos != -1:
                        sep_pos = min(exc_pos, caret_pos)
                    elif exc_pos != -1:
                        sep_pos = exc_pos
                    elif caret_pos != -1:
                        sep_pos = caret_pos
                    
                    if sep_pos != -1 and 0 < sep_pos <= 20:
                        prefix = name_bytes[:sep_pos]
                        is_icon_name = all(
                            (65 <= b <= 90) or (48 <= b <= 57) or b == 95 or b == 126
                            for b in prefix
                        )
                        if is_icon_name and len(prefix) >= 3:
                            icon_name = prefix.decode('ascii', errors='ignore')
                            name_bytes = name_bytes[sep_pos+1:]
                    
                    # Stop at first null byte (marks end of button name, rest is navigation code)
                    null_pos = name_bytes.find(b'\x00')
                    if null_pos != -1:
                        name_bytes = name_bytes[:null_pos]
                    
                    # Strip everything from first control character onwards (metadata)
                    for i, byte_val in enumerate(name_bytes):
                        if byte_val < 0x20:
                            name_bytes = name_bytes[:i]
                            break
                    
                    button_name = name_bytes.decode('ascii', errors='ignore')
                    button_name = button_name.rstrip()  # Strip trailing whitespace
                    
                    pos_cursor = pos + 14 + name_len
                
                # Skip null terminator if present
                if pos_cursor < len(data) and data[pos_cursor] == 0:
                    pos_cursor += 1
                
                # Find the end of this button (CRLF terminator) to limit search window
                button_end = data.find(b'\r\n', pos_cursor)
                if button_end == -1:
                    button_end = min(pos_cursor + 50, len(data))
                else:
                    button_end = min(button_end, pos_cursor + 50)
                
                # Check for GO-BACK-PAGE pattern: FF 81 05 FE (search only within this button)
                search_region = data[pos_cursor:button_end]
                go_back_page_pos = search_region.find(b'\xff\x81\x05\xfe')
                
                # Check for CLEAR DISPLAY pattern: FF 80 3A FE
                clear_display_pos = search_region.find(b'\xff\x80\x3a\xfe')
                
                # Check for SET-PAGE patterns: FF 80 8C (PERMANENT) or FF 80 8D (TEMPORARY)
                set_page_perm_pos = search_region.find(b'\xff\x80\x8c')
                set_page_temp_pos = search_region.find(b'\xff\x80\x8d')
                
                # Check for INSERT-DATE pattern: FF 80 67 FE
                insert_date_pos = search_region.find(b'\xff\x80\x67\xfe')
                
                # Check for SPEAK-DATE pattern: FF 80 63 FE
                speak_date_pos = search_region.find(b'\xff\x80\x63\xfe')
                
                # Check for INSERT-TIME pattern: FF 80 66 FE
                insert_time_pos = search_region.find(b'\xff\x80\x66\xfe')
                
                # Check for SPEAK-TIME pattern: FF 80 62 FE
                speak_time_pos = search_region.find(b'\xff\x80\x62\xfe')
                
                if go_back_page_pos != -1:
                    # Found GO-BACK-PAGE pattern
                    navigation_target = None
                    navigation_type = 'GO-BACK-PAGE'
                    functions.append('GO-BACK-PAGE')
                    # Skip to end of record (don't parse icon/speech)
                    if not button_name:
                        button_name = "GO-BACK-PAGE"
                    speech = None  # GO-BACK-PAGE buttons have no speech
                elif clear_display_pos != -1 or set_page_perm_pos != -1 or set_page_temp_pos != -1:
                    # Found CLEAR DISPLAY and/or SET-PAGE patterns
                    # These can appear in either order
                    
                    # Check for CLEAR DISPLAY
                    if clear_display_pos != -1:
                        functions.append('CLEAR-DISPLAY')
                        # Extract speech text that may exist between CLEAR DISPLAY and other markers
                        
                        # Determine if there's a SET-PAGE marker and its position relative to CLEAR DISPLAY
                        set_page_pos_for_speech = None
                        if set_page_perm_pos != -1:
                            set_page_pos_for_speech = set_page_perm_pos
                        if set_page_temp_pos != -1 and (set_page_pos_for_speech is None or set_page_temp_pos < set_page_pos_for_speech):
                            set_page_pos_for_speech = set_page_temp_pos
                        
                        # Only extract speech if CLEAR DISPLAY comes BEFORE SET-PAGE
                        if set_page_pos_for_speech is not None and clear_display_pos < set_page_pos_for_speech:
                            # Extract text between CLEAR DISPLAY and SET-PAGE
                            speech_start = clear_display_pos + 4
                            speech_end = set_page_pos_for_speech
                            
                            if speech_end > speech_start:
                                speech_bytes = search_region[speech_start:speech_end]
                                # Remove function markers
                                speech_bytes = speech_bytes.replace(b'\xff\x80\x67\xfe', b'')  # INSERT-DATE
                                speech_bytes = speech_bytes.replace(b'\xff\x80\x63\xfe', b'')  # SPEAK-DATE
                                speech_bytes = speech_bytes.replace(b'\xff\x80\x66\xfe', b'')  # INSERT-TIME
                                speech_bytes = speech_bytes.replace(b'\xff\x80\x62\xfe', b'')  # SPEAK-TIME
                                
                                # Remove embedded null bytes
                                speech_bytes = speech_bytes.replace(b'\x00', b'')
                                
                                speech = speech_bytes.decode('ascii', errors='ignore').strip()
                                if not speech:
                                    speech = None
                        else:
                            # CLEAR DISPLAY comes after SET-PAGE or no SET-PAGE found
                            # Any text after CLEAR DISPLAY is just padding, set speech to None
                            speech = None
                    
                    # Check for SET-PAGE (regardless of position relative to CLEAR DISPLAY)
                    if set_page_perm_pos != -1 or set_page_temp_pos != -1:
                        # Determine which SET-PAGE marker appears first
                        if set_page_perm_pos != -1 and (set_page_temp_pos == -1 or set_page_perm_pos < set_page_temp_pos):
                            navigation_type = 'PERMANENT'
                            set_page_pos = set_page_perm_pos
                        else:
                            navigation_type = 'TEMPORARY'
                            set_page_pos = set_page_temp_pos
                        
                        # Extract page name
                        page_start = set_page_pos + 3  # After FF 80 8C or FF 80 8D
                        page_end = page_start
                        while page_end < len(search_region) and search_region[page_end] != 0xfe:
                            page_end += 1
                        if page_end > page_start:
                            navigation_target = search_region[page_start:page_end].decode('ascii', errors='ignore')
                            functions.append(f'SET-PAGE({navigation_target})')

                    # Handle PROMPT-MARKER in search region (speech before, name after)
                    prompt_marker_pos = search_region.find(b'\xff\x80{\xfe')
                    if prompt_marker_pos != -1:
                        speech_bytes = search_region[:prompt_marker_pos]
                        # Remove SET-PAGE markers from speech if they appear before PROMPT-MARKER
                        if b'\xff\x80\x8c' in speech_bytes:
                            marker_pos = speech_bytes.rfind(b'\xff\x80\x8c')
                            if marker_pos >= 0:
                                speech_bytes = speech_bytes[:marker_pos]
                        elif b'\xff\x80\x8d' in speech_bytes:
                            marker_pos = speech_bytes.rfind(b'\xff\x80\x8d')
                            if marker_pos >= 0:
                                speech_bytes = speech_bytes[:marker_pos]
                        speech_bytes = speech_bytes.replace(b'\x00', b'').strip()
                        if speech_bytes:
                            speech = speech_bytes.decode('ascii', errors='ignore').strip()

                        name_bytes = search_region[prompt_marker_pos + 4:]
                        if 'set_page_pos' in locals() and set_page_pos != -1 and set_page_pos > prompt_marker_pos:
                            name_bytes = search_region[prompt_marker_pos + 4:set_page_pos]
                        # Remove null bytes and filter control characters (< 0x20, except space)
                        name_bytes = bytes(b for b in name_bytes if b >= 0x20 or b == 0x09)
                        name_bytes = name_bytes.strip()
                        if name_bytes:
                            name_text = name_bytes.decode('ascii', errors='ignore').strip()
                            if name_text:
                                button_name = name_text
                    
                    # Check for INSERT-DATE and SPEAK-DATE
                    if insert_date_pos != -1:
                        functions.append('INSERT-DATE')
                    if speak_date_pos != -1:
                        functions.append('SPEAK-DATE')
                    
                    # Check for INSERT-TIME and SPEAK-TIME
                    if insert_time_pos != -1:
                        functions.append('INSERT-TIME')
                    if speak_time_pos != -1:
                        functions.append('SPEAK-TIME')
                    
                    # Navigation-only buttons should only have speech if there was actual text outside function markers
                    if not speech:
                        has_prompt_marker = b'\xff\x80{\xfe' in search_region
                        if button_name and has_prompt_marker:
                            speech = button_name
                        elif button_name:
                            speech = button_name
                        else:
                            speech = None
                
                else:
                    # Normal Format 3 processing
                    # Check for 0xFF marker (indicates encoded icon/navigation data)
                    if pos_cursor < len(data) and data[pos_cursor] == 0xff:
                        # Check for GO-BACK-PAGE pattern: FF 81 05 FE
                        if pos_cursor + 3 < len(data) and data[pos_cursor:pos_cursor+4] == b'\xff\x81\x05\xfe':
                            navigation_type = 'GO-BACK-PAGE'
                            navigation_target = None
                            pos_cursor += 4
                        else:
                            # 0xFF marker - skip encoded icon/navigation bytes
                            pos_cursor += 1
                            # Skip until we hit 0xA4 or CRLF
                            while pos_cursor < len(data) and data[pos_cursor] not in [0xa4, 0x0d]:
                                pos_cursor += 1
                        
                        # No speech for these buttons
                        speech = button_name
                    else:
                        # Extract icon (standard Format 3)
                        if pos_cursor < len(data):
                            icon_len = data[pos_cursor]
                            if 0 < icon_len < 50:
                                icon_name = data[pos_cursor+1:pos_cursor+1+icon_len].decode('ascii', errors='ignore')
                                pos_cursor += 1 + icon_len
                    
                        # Extract speech (2-byte length)
                    if pos_cursor + 2 < len(data):
                        speech_len = struct.unpack('<H', data[pos_cursor:pos_cursor+2])[0]
                        pos_cursor += 2
                        if 0 < speech_len < 500:
                            speech_bytes = data[pos_cursor:pos_cursor+speech_len]
                            
                            # Remove icon prefix patterns and preserve icon if not already set
                            speech_bytes_orig = speech_bytes
                            while speech_bytes and speech_bytes[0] < 0x20:
                                speech_bytes = speech_bytes[1:]
                            
                            exc_pos = speech_bytes.find(b'!')
                            caret_pos = speech_bytes.find(b'^')
                            sep_pos = -1
                            if exc_pos != -1 and caret_pos != -1:
                                sep_pos = min(exc_pos, caret_pos)
                            elif exc_pos != -1:
                                sep_pos = exc_pos
                            elif caret_pos != -1:
                                sep_pos = caret_pos
                            
                            if sep_pos != -1 and 0 < sep_pos <= 20:
                                prefix = speech_bytes[:sep_pos]
                                is_icon_name = all(
                                    (65 <= b <= 90) or (48 <= b <= 57) or b == 95 or b == 126
                                    for b in prefix
                                )
                                if is_icon_name and len(prefix) >= 3:
                                    if not icon_name:
                                        icon_name = prefix.decode('ascii', errors='ignore')
                                    speech_bytes = speech_bytes[sep_pos+1:]
                            
                            # Remove embedded null bytes
                            speech_bytes = speech_bytes.replace(b'\x00', b'')
                            
                            # Strip everything from first control character onwards (metadata)
                            for i, byte_val in enumerate(speech_bytes):
                                if byte_val < 0x20:
                                    speech_bytes = speech_bytes[:i]
                                    break
                            
                            speech = speech_bytes.decode('ascii', errors='ignore')
                            pos_cursor += speech_len
                            
                            # Check if speech looks like icon/metadata junk
                            # This happens when the binary speech field contains icon names instead of actual speech
                            if speech:
                                # If original speech_bytes had control chars (before stripping), it's likely junk
                                had_control_chars = any(b < 0x20 for b in speech_bytes_orig)
                                # Also check if it's very short and looks like an icon name (mostly uppercase)
                                is_short_uppercase = len(speech) <= 15 and sum(1 for c in speech if c.isupper()) > len(speech) * 0.5
                                
                                if had_control_chars or is_short_uppercase:
                                    speech = None
                    
                    # Extract navigation
                    if pos_cursor < len(data):
                        nav_byte = data[pos_cursor]
                        if nav_byte == 0x85:  # GO-BACK-PAGE
                            navigation_type = 'GO-BACK-PAGE'
                            navigation_target = None
                            pos_cursor += 1
                        elif nav_byte in [0x8c, 0x8d]:
                            navigation_type = 'PERMANENT' if nav_byte == 0x8c else 'TEMPORARY'
                            pos_cursor += 1
                            # Find null terminator for target
                            target_start = pos_cursor
                            while pos_cursor < len(data) and data[pos_cursor] != 0:
                                pos_cursor += 1
                            navigation_target = data[target_start:pos_cursor].decode('ascii', errors='ignore')
                    
                    # Don't set speech to button_name for navigation-only buttons
                    # Speech should only contain text that was explicitly extracted
                    if not speech:
                        speech = None
                
                format_stats['Format 3 - Offset name'] += 1
                
            # Format 1: Standard (byte_9 1-49)
            # byte_9 can indicate name length, but not always reliable
            # Check both methods and use whichever produces valid ASCII
            elif 1 <= byte_9 <= 49:
                # Check if this is a metadata page (40XX)
                is_metadata_page = page_id_str.startswith('40')
                
                if is_metadata_page:
                    # Metadata pages: extract name until CRLF, skip icon processing
                    # For Format 1, byte_9 indicates the name is at pos+10 (old method)
                    # Try old method first (pos+10) since byte_9 1-49 means Format 1
                    name_start = pos + 10
                    name_end = data.find(b'\r\n', name_start)
                    if name_end == -1 or name_end > name_start + 100:
                        name_end = name_start + 50
                    
                    name_bytes = data[name_start:name_end]
                    # Remove embedded nulls
                    name_bytes = name_bytes.replace(b'\x00', b'')
                    # Stop at any control character except null
                    for i, byte_val in enumerate(name_bytes):
                        if byte_val < 0x20 and byte_val != 0:
                            name_bytes = name_bytes[:i]
                            break
                    
                    button_name = name_bytes.decode('ascii', errors='replace').strip()
                    
                    # Set pos_cursor after the name
                    name_len = len(button_name.encode('ascii', errors='replace'))
                    pos_cursor = pos + 10 + name_len
                    
                else:
                    
                    # Normal Format 1 processing with icon stripping
                    # Try new method first (name at pos+14, length at pos+13)
                    name_len_new = data[pos+13] if pos+13 < len(data) else 0
                    if 0 < name_len_new < 100 and pos+14+name_len_new < len(data):
                        # Extract name, but stop at \r\n terminator
                        name_start = pos + 14
                        name_end = name_start
                        while name_end < name_start + name_len_new and name_end < len(data):
                            if data[name_end:name_end+2] == b'\r\n':
                                break
                            name_end += 1
                        name_bytes_new = data[name_start:name_end]
                        
                        # Remove icon prefix patterns and preserve icon
                        icon_name_new = None
                        while name_bytes_new and name_bytes_new[0] < 0x20:
                            name_bytes_new = name_bytes_new[1:]
                        
                        exc_pos = name_bytes_new.find(b'!')
                        caret_pos = name_bytes_new.find(b'^')
                        sep_pos = -1
                        if exc_pos != -1 and caret_pos != -1:
                            sep_pos = min(exc_pos, caret_pos)
                        elif exc_pos != -1:
                            sep_pos = exc_pos
                        elif caret_pos != -1:
                            sep_pos = caret_pos
                        
                        if sep_pos != -1 and 0 < sep_pos <= 20:
                            prefix = name_bytes_new[:sep_pos]
                            is_icon_name = all(
                                (65 <= b <= 90) or (48 <= b <= 57) or b == 95 or b == 126
                                for b in prefix
                            )
                            if is_icon_name and len(prefix) >= 3:
                                icon_name_new = prefix.decode('ascii', errors='ignore')
                                name_bytes_new = name_bytes_new[sep_pos+1:]
                        
                        # Remove embedded null bytes
                        name_bytes_new = name_bytes_new.replace(b'\x00', b'')
                        
                        # Strip everything from first control character onwards (metadata)
                        for i, byte_val in enumerate(name_bytes_new):
                            if byte_val < 0x20:
                                name_bytes_new = name_bytes_new[:i]
                                break
                        
                        name_new = name_bytes_new.decode('ascii', errors='replace').rstrip()
                        is_valid_new = all(32 <= ord(c) < 127 or c == '\n' for c in name_new) if name_new else False
                    else:
                        is_valid_new = False
                    
                    # Try middle method (name at pos+10, length at pos+9)
                    # This handles buttons where byte_8=56-57 (Voice variant buttons)
                    name_len_middle = data[pos+9] if pos+9 < len(data) else 0
                    if 0 < name_len_middle < 100 and pos+10+name_len_middle < len(data):
                        # Extract name, but stop at \r\n terminator
                        name_start = pos + 10
                        name_end = name_start
                        while name_end < name_start + name_len_middle and name_end < len(data):
                            if data[name_end:name_end+2] == b'\r\n':
                                break
                            name_end += 1
                        name_bytes_middle = data[name_start:name_end]
                        
                        # Remove embedded null bytes
                        name_bytes_middle = name_bytes_middle.replace(b'\x00', b'')
                        
                        # Strip everything from first control character onwards
                        for i, byte_val in enumerate(name_bytes_middle):
                            if byte_val < 0x20:
                                name_bytes_middle = name_bytes_middle[:i]
                                break
                        
                        name_middle = name_bytes_middle.decode('ascii', errors='replace').rstrip()
                        is_valid_middle = all(32 <= ord(c) < 127 or c == '\n' for c in name_middle) if name_middle else False
                    else:
                        is_valid_middle = False
                    
                    # Try old method (name at pos+10, length=byte_9)
                    if pos+10+byte_9 < len(data):
                        # Extract name, but stop at \r\n terminator
                        name_start = pos + 10
                        name_end = name_start
                        while name_end < name_start + byte_9 and name_end < len(data):
                            if data[name_end:name_end+2] == b'\r\n':
                                break
                            name_end += 1
                        name_bytes_old = data[name_start:name_end]
                        
                        # Remove icon prefix patterns and preserve icon
                        icon_name_old = None
                        while name_bytes_old and name_bytes_old[0] < 0x20:
                            name_bytes_old = name_bytes_old[1:]
                        
                        exc_pos = name_bytes_old.find(b'!')
                        caret_pos = name_bytes_old.find(b'^')
                        sep_pos = -1
                        if exc_pos != -1 and caret_pos != -1:
                            sep_pos = min(exc_pos, caret_pos)
                        elif exc_pos != -1:
                            sep_pos = exc_pos
                        elif caret_pos != -1:
                            sep_pos = caret_pos
                        
                        if sep_pos != -1 and 0 < sep_pos <= 20:
                            prefix = name_bytes_old[:sep_pos]
                            is_icon_name = all(
                                (65 <= b <= 90) or (48 <= b <= 57) or b == 95 or b == 126
                                for b in prefix
                            )
                            if is_icon_name and len(prefix) >= 3:
                                icon_name_old = prefix.decode('ascii', errors='ignore')
                                name_bytes_old = name_bytes_old[sep_pos+1:]
                        
                        # Remove embedded null bytes
                        name_bytes_old = name_bytes_old.replace(b'\x00', b'')
                        
                        # Strip everything from first control character onwards (metadata)
                        for i, byte_val in enumerate(name_bytes_old):
                            if byte_val < 0x20:
                                name_bytes_old = name_bytes_old[:i]
                                break
                        
                        name_old = name_bytes_old.decode('ascii', errors='replace').rstrip()
                        is_valid_old = all(32 <= ord(c) < 127 or c == '\n' for c in name_old) if name_old else False
                    else:
                        is_valid_old = False
                    
                    # Choose the valid one - prefer MIDDLE method if valid (longer name)
                    # MIDDLE method handles voice variant buttons (byte_7=56-57)
                    if is_valid_middle:
                        # Use middle method (name_len at pos+9)
                        name_len = name_len_middle
                        button_name = name_middle
                        pos_cursor = pos + 10 + name_len
                        
                        # Extract icon for middle method
                        if pos_cursor < len(data):
                            # Check for 0x00 separator first
                            if data[pos_cursor] == 0:
                                pos_cursor += 1
                            
                            if pos_cursor < len(data):
                                potential_icon_len = data[pos_cursor]
                                
                                # Check if this looks like a length byte (1-30) or ASCII text (>= 32)
                                if 1 <= potential_icon_len <= 30:
                                    # Looks like a length byte
                                    icon_len = potential_icon_len
                                    pos_cursor += 1
                                    icon_name = data[pos_cursor:pos_cursor+icon_len].decode('ascii', errors='ignore')
                                    pos_cursor += icon_len
                                # If byte is >= 32 (printable ASCII), it's likely the start of speech, not icon
                                # In this case, don't extract icon here - use button name as fallback later
                    elif is_valid_old:
                        # Fallback to old method (name_len at byte_9)
                        name_len = byte_9
                        button_name = name_old
                        if icon_name_old:
                            icon_name = icon_name_old
                        pos_cursor = pos + 10 + name_len
                        
                        # Extract icon for old method (same as middle method)
                        # Even if we already have icon_name from the name field, we need to skip over the icon data
                        if pos_cursor < len(data):
                            # Check for 0x00 separator first
                            if data[pos_cursor] == 0:
                                pos_cursor += 1
                            
                            if pos_cursor < len(data):
                                potential_icon_len = data[pos_cursor]
                                
                                # Check if this looks like a length byte (1-30) or ASCII text (>= 32)
                                if 1 <= potential_icon_len <= 30:
                                    # Looks like a length byte
                                    icon_len = potential_icon_len
                                    pos_cursor += 1
                                    icon_data = data[pos_cursor:pos_cursor+icon_len].decode('ascii', errors='ignore')
                                    if not icon_name:
                                        icon_name = icon_data
                                    pos_cursor += icon_len
                                    
                                    # Check if next byte is a separator (! or ^) and skip it
                                    if pos_cursor < len(data) and data[pos_cursor] in [0x21, 0x5e]:  # ! or ^
                                        pos_cursor += 1
                                # If byte is >= 32 (printable ASCII), it's likely the start of speech, not icon
                                # In this case, don't extract icon here - keep existing icon_name or use button name later
                                        pos_cursor += 1
                    elif is_valid_new:
                        # DEBUG
                        if page_id_str == '0201' and sequence == 32:
                            print(f"DEBUG 0201/32: Using NEW method")
                            print(f"  name_new='{name_new}', name_len_new={name_len_new}")
                        
                        # Fallback to new method (name_len at pos+13)
                        name_len = name_len_new
                        button_name = name_new
                        if icon_name_new:
                            icon_name = icon_name_new
                        pos_cursor = pos + 14 + name_len
                        
                        # DEBUG
                        if page_id_str == '0201' and sequence == 32:
                            print(f"DEBUG 0201/32: After name extraction (NEW), pos_cursor={pos_cursor} (pos={pos}, name_len={name_len})")
                    else:
                        # None valid, skip
                        format_stats['Complex format'] += 1
                        pos += 1
                        continue
                
                # Skip 0x00 separator
                if pos_cursor < len(data) and data[pos_cursor] == 0:
                    pos_cursor += 1
                
                # Find the end of this button (CRLF terminator) to limit search window
                button_end = data.find(b'\r\n', pos_cursor)
                if button_end == -1:
                    button_end = min(pos_cursor + 120, len(data))  # Increased from 50 to 120 for PROMPT-MARKER support
                else:
                    button_end = min(button_end, pos_cursor + 120)  # Increased from 50 to 120
                
                # Check for GO-BACK-PAGE pattern: FF 81 05 FE (search only within this button)
                search_region = data[pos_cursor:button_end]
                
                # Check for VOICE-SET-TEMPORARY (FF 81 03 ... FE) and VOICE-CLEAR-TEMPORARY (FF 81 04 FE)
                # These should be stripped from search_region but tracked in functions
                voice_set_temp_pos = search_region.find(b'\xff\x81\x03')
                voice_clear_temp_pos = search_region.find(b'\xff\x81\x04\xfe')
                
                # Strip VOICE markers from search region before icon/speech extraction
                cleaned_search_region = search_region
                if voice_set_temp_pos != -1:
                    # Find the end of VOICE-SET-TEMPORARY parameter (FE marker)
                    param_end = search_region.find(b'\xfe', voice_set_temp_pos + 3)
                    if param_end != -1:
                        # Remove the entire VOICE-SET-TEMPORARY function (FF 81 03 ... FE)
                        cleaned_search_region = cleaned_search_region[:voice_set_temp_pos] + cleaned_search_region[param_end+1:]
                        functions.append('VOICE-SET-TEMPORARY')
                
                if voice_clear_temp_pos != -1:
                    # Remove VOICE-CLEAR-TEMPORARY marker (4 bytes: FF 81 04 FE)
                    voice_clear_in_cleaned = cleaned_search_region.find(b'\xff\x81\x04\xfe')
                    if voice_clear_in_cleaned != -1:
                        cleaned_search_region = cleaned_search_region[:voice_clear_in_cleaned] + cleaned_search_region[voice_clear_in_cleaned+4:]
                        functions.append('VOICE-CLEAR-TEMPORARY')
                
                # Use cleaned_search_region for all subsequent pattern matching
                search_region = cleaned_search_region
                
                go_back_page_pos = search_region.find(b'\xff\x81\x05\xfe')
                
                # Check for GOTO-HOME pattern: FF 80 85 FE
                goto_home_pos = search_region.find(b'\xff\x80\x85\xfe')
                
                # Check for CLEAR DISPLAY pattern: FF 80 3A FE
                clear_display_pos = search_region.find(b'\xff\x80\x3a\xfe')
                
                # Check for SET-PAGE patterns: FF 80 8C (PERMANENT) or FF 80 8D (TEMPORARY)
                set_page_perm_pos = search_region.find(b'\xff\x80\x8c')
                set_page_temp_pos = search_region.find(b'\xff\x80\x8d')
                
                # Check for INSERT-DATE pattern: FF 80 67 FE
                insert_date_pos = search_region.find(b'\xff\x80\x67\xfe')
                
                # Check for SPEAK-DATE pattern: FF 80 63 FE
                speak_date_pos = search_region.find(b'\xff\x80\x63\xfe')
                
                # Check for INSERT-TIME pattern: FF 80 66 FE
                insert_time_pos = search_region.find(b'\xff\x80\x66\xfe')
                
                # Check for SPEAK-TIME pattern: FF 80 62 FE
                speak_time_pos = search_region.find(b'\xff\x80\x62\xfe')
                
                if go_back_page_pos != -1:
                    # Found GO-BACK-PAGE pattern
                    navigation_target = None
                    navigation_type = 'GO-BACK-PAGE'
                    functions.append('GO-BACK-PAGE')
                    # Skip to end of record (don't parse icon/speech)
                    if not button_name:
                        button_name = "GO-BACK-PAGE"
                    speech = None  # GO-BACK-PAGE buttons have no speech
                elif goto_home_pos != -1:
                    # Found GOTO-HOME pattern
                    navigation_target = '0400'
                    navigation_type = 'PERMANENT'
                    functions.append('GOTO-HOME')
                    if not button_name:
                        button_name = "home"
                    speech = None  # GOTO-HOME buttons have no speech
                elif clear_display_pos != -1 or set_page_perm_pos != -1 or set_page_temp_pos != -1:
                    # Found CLEAR DISPLAY and/or SET-PAGE patterns
                    # These can appear in either order
                    
                    # Check for CLEAR DISPLAY
                    if clear_display_pos != -1:
                        functions.append('CLEAR-DISPLAY')
                        # Don't automatically set speech = None
                        # Extract speech text that may exist between markers
                        
                        # Find the earliest function marker position
                        earliest_marker = clear_display_pos
                        if set_page_perm_pos != -1 and set_page_perm_pos > clear_display_pos:
                            latest_marker = set_page_perm_pos
                        elif set_page_temp_pos != -1 and set_page_temp_pos > clear_display_pos:
                            latest_marker = set_page_temp_pos
                        else:
                            latest_marker = None
                        
                        # Extract text after CLEAR DISPLAY marker (4 bytes)
                        speech_start = clear_display_pos + 4
                        if latest_marker:
                            speech_end = latest_marker
                        else:
                            speech_end = len(search_region)
                        
                        if speech_end > speech_start:
                            speech_bytes = search_region[speech_start:speech_end]
                            # Remove function markers
                            speech_bytes = speech_bytes.replace(b'\xff\x80\x67\xfe', b'')  # INSERT-DATE
                            speech_bytes = speech_bytes.replace(b'\xff\x80\x63\xfe', b'')  # SPEAK-DATE
                            speech_bytes = speech_bytes.replace(b'\xff\x80\x66\xfe', b'')  # INSERT-TIME
                            speech_bytes = speech_bytes.replace(b'\xff\x80\x62\xfe', b'')  # SPEAK-TIME
                            
                            # Remove embedded null bytes
                            speech_bytes = speech_bytes.replace(b'\x00', b'')
                            
                            speech = speech_bytes.decode('ascii', errors='ignore').strip()
                            if not speech:
                                speech = None
                    
                    # Check for SET-PAGE (regardless of position relative to CLEAR DISPLAY)
                    if set_page_perm_pos != -1 or set_page_temp_pos != -1:
                        # Determine which SET-PAGE marker appears first
                        if set_page_perm_pos != -1 and (set_page_temp_pos == -1 or set_page_perm_pos < set_page_temp_pos):
                            navigation_type = 'PERMANENT'
                            set_page_pos = set_page_perm_pos
                        else:
                            navigation_type = 'TEMPORARY'
                            set_page_pos = set_page_temp_pos
                        
                        # Extract page name
                        page_start = set_page_pos + 3  # After FF 80 8C or FF 80 8D
                        page_end = page_start
                        while page_end < len(search_region) and search_region[page_end] != 0xfe:
                            page_end += 1
                        if page_end > page_start:
                            navigation_target = search_region[page_start:page_end].decode('ascii', errors='ignore')
                            functions.append(f'SET-PAGE({navigation_target})')
                    
                    # Check for INSERT-DATE and SPEAK-DATE
                    if insert_date_pos != -1:
                        functions.append('INSERT-DATE')
                    if speak_date_pos != -1:
                        functions.append('SPEAK-DATE')
                    
                    # Check for INSERT-TIME and SPEAK-TIME
                    if insert_time_pos != -1:
                        functions.append('INSERT-TIME')
                    if speak_time_pos != -1:
                        functions.append('SPEAK-TIME')
                    
                    # If no CLEAR DISPLAY, check for PROMPT-MARKER or use button name as speech
                    if clear_display_pos == -1 and not speech:
                        
                        # Check if there's a PROMPT-MARKER pattern (speech before, name after)
                        has_prompt_marker = b'\xff\x80{\xfe' in search_region
                        if has_prompt_marker:
                            prompt_pos = search_region.find(b'\xff\x80{\xfe')
                            original_button_name = button_name
                            # Speech is everything before PROMPT-MARKER, but stop at SET-PAGE if present
                            # First, skip the icon if present
                            speech_start = 0
                            if len(search_region) > 0 and search_region[0] < 0x20 and search_region[0] > 0:
                                # First byte might be icon length
                                icon_len = search_region[0]
                                if icon_len < 50 and len(search_region) > 1 + icon_len:
                                    # Skip the icon length byte and the icon name
                                    speech_start = 1 + icon_len
                            
                            set_page_pos = set_page_perm_pos if set_page_perm_pos != -1 else set_page_temp_pos
                            
                            if set_page_pos != -1 and set_page_pos < prompt_pos:
                                # SET-PAGE comes before PROMPT-MARKER
                                # Speech is everything from speech_start to SET-PAGE marker
                                speech_bytes = search_region[speech_start:set_page_pos]
                            else:
                                # PROMPT-MARKER comes first, extract everything from speech_start to it
                                speech_bytes = search_region[speech_start:prompt_pos]
                            
                            
                            # Clean up the speech bytes
                            speech_bytes = speech_bytes.replace(b'\x00', b'').strip()
                            
                            if speech_bytes:
                                speech_text = speech_bytes.decode('ascii', errors='ignore').strip()
                                if speech_text:
                                    speech = speech_text
                            
                            # Name is after PROMPT-MARKER; stop at first control char
                            name_start = prompt_pos + 4
                            name_end = name_start
                            while name_end < len(search_region) and search_region[name_end] >= 0x20:
                                name_end += 1
                            name_bytes = search_region[name_start:name_end]
                            name_bytes = bytes(b for b in name_bytes if b >= 0x20 or b == 0x09)
                            if name_bytes:
                                prompt_name = name_bytes.decode('ascii', errors='ignore').strip()
                                # Remove trailing single-letter junk
                                # Case 1: "word h" (space before letter)
                                if prompt_name and len(prompt_name) >= 2 and prompt_name[-2] == ' ':
                                    if prompt_name[-1].islower() or prompt_name[-1].isupper():
                                        prompt_name = prompt_name[:-2].rstrip()
                                # Case 2: "voiceA" (uppercase letter after lowercase word, no space)
                                elif prompt_name and len(prompt_name) >= 2 and prompt_name[-1].isupper() and prompt_name[-2].islower():
                                    prompt_name = prompt_name[:-1]
                                if prompt_name:
                                    button_name = prompt_name
                                    # If icon not set yet, treat original name as icon label
                                    if original_button_name and not icon_name:
                                        icon_name = original_button_name
                        
                        # If still no speech, fall back to button name
                        # BUT: if PROMPT-MARKER exists, do not force speech = button_name
                        if not speech and not has_prompt_marker:
                            speech = button_name

                
                elif b'\xff\x80{\xfe' in search_region and go_back_page_pos == -1 and clear_display_pos == -1 and set_page_perm_pos == -1 and set_page_temp_pos == -1:
                    # PROMPT-MARKER ONLY (no CLEAR-DISPLAY, SET-PAGE, or GO-BACK-PAGE)
                    # Extract name and speech from PROMPT-MARKER pattern
                    prompt_pos = search_region.find(b'\xff\x80{\xfe')
                    original_button_name = button_name
                    
                    # Speech is everything before PROMPT-MARKER
                    speech_bytes = search_region[:prompt_pos].replace(b'\x00', b'').strip()
                    if speech_bytes:
                        speech_text = speech_bytes.decode('ascii', errors='ignore').strip()
                        if speech_text:
                            speech = speech_text
                    
                    # Name is after PROMPT-MARKER; stop at first control char or 0x7F+
                    name_start = prompt_pos + 4
                    name_end = name_start
                    while name_end < len(search_region):
                        byte_val = search_region[name_end]
                        # Stop at control character (< 0x20) or extended ASCII (>= 0x7F)
                        if byte_val < 0x20 or byte_val >= 0x7F:
                            break
                        name_end += 1
                    
                    name_bytes = search_region[name_start:name_end]
                    if name_bytes:
                        prompt_name = name_bytes.decode('ascii', errors='ignore').strip()
                        # Remove trailing single-letter junk
                        # Case 1: "word h" (space before letter)
                        if prompt_name and len(prompt_name) >= 2 and prompt_name[-2] == ' ':
                            if prompt_name[-1].islower() or prompt_name[-1].isupper():
                                prompt_name = prompt_name[:-2].rstrip()
                        # Case 2: "voiceA" (uppercase letter after lowercase word, no space)
                        elif prompt_name and len(prompt_name) >= 2 and prompt_name[-1].isupper() and prompt_name[-2].islower():
                            prompt_name = prompt_name[:-1]
                        if prompt_name:
                            button_name = prompt_name
                            # If icon not set yet, treat original name as icon label
                            if original_button_name and not icon_name:
                                icon_name = original_button_name

                
                else:
                    # Extract icon (if present)
                    # If byte is 0 or >= 32 (printable ASCII), it's the start of speech
                    # Ensure search_region is defined if we haven't entered a CLEAR-DISPLAY/SET-PAGE block
                    if 'search_region' not in locals():
                        button_end = data.find(b'\r\n', pos_cursor)
                        if button_end == -1:
                            button_end = min(pos_cursor + 120, len(data))
                        else:
                            button_end = min(button_end, pos_cursor + 120)
                        search_region = data[pos_cursor:button_end]
                    
                    if pos_cursor < len(data):
                        potential_icon_len = data[pos_cursor]
                        if 1 <= potential_icon_len <= 30:
                            # This looks like an icon length
                            icon_len = potential_icon_len
                            pos_cursor += 1
                            if pos_cursor + icon_len < len(data):
                                icon_name = data[pos_cursor:pos_cursor+icon_len].decode('ascii', errors='ignore')
                                pos_cursor += icon_len
                    
                    # Check for 0xA4 function markers (same as Format 5)
                    marker_start = pos_cursor
                    while pos_cursor < len(data) - 10 and data[pos_cursor] == 0xa4:
                        func_type = data[pos_cursor+1]
                        pos_cursor += 2
                        
                        if func_type == 0x3a:  # Speech marker
                            # Find end of speech (next 0xA4 or 0xA0 or CRLF)
                            speech_end = pos_cursor
                            while speech_end < len(data) - 2:
                                if data[speech_end] == 0xa4 or data[speech_end] == 0xa0 or data[speech_end:speech_end+2] == b'\r\n':
                                    break
                                speech_end += 1
                            speech_bytes = data[pos_cursor:speech_end]
                            speech_bytes = speech_bytes.replace(b'\x00', b'')
                            speech_text = speech_bytes.decode('ascii', errors='ignore').strip()
                            # Only set speech if there's actual text
                            if speech_text:
                                speech = speech_text
                            pos_cursor = speech_end
                        
                        elif func_type == 0x06:  # RANDOM-CHOICE
                            # Extract page reference (in parentheses)
                            ref_start = pos_cursor
                            while ref_start < len(data) and data[ref_start] != 0x28:  # '('
                                ref_start += 1
                            ref_end = ref_start + 1
                            while ref_end < len(data) and data[ref_end] != 0x29:  # ')'
                                ref_end += 1
                            if ref_start < ref_end:
                                ref_page = data[ref_start+1:ref_end].decode('ascii', errors='ignore')
                                functions.append(f'RANDOM-CHOICE({ref_page})')
                            pos_cursor = ref_end + 1
                        
                        elif func_type in [0x8c, 0x8d]:  # SET-PAGE
                            nav_type = 'PERMANENT' if func_type == 0x8c else 'TEMPORARY'
                            # Extract target (in parentheses)
                            target_start = pos_cursor
                            while target_start < len(data) and data[target_start] != 0x28:
                                target_start += 1
                            target_end = target_start + 1
                            while target_end < len(data) and data[target_end] != 0x29:
                                target_end += 1
                            if target_start < target_end:
                                navigation_target = data[target_start+1:target_end].decode('ascii', errors='ignore')
                                navigation_type = nav_type
                                functions.append(f'SET-PAGE({navigation_target})')
                            pos_cursor = target_end + 1
                    
                    # Check for CLEAR-DISPLAY marker (0xA0) after all 0xA4 markers
                    if pos_cursor < len(data) and data[pos_cursor] == 0xa0:
                        functions.append('CLEAR-DISPLAY')
                        pos_cursor += 1
                    
                    # Check for A4 7B speech marker within this button (used by control buttons)
                    if not speech:
                        a4_speech_pos = search_region.find(b'\xa4\x7b')
                        if a4_speech_pos != -1:
                            speech_start = a4_speech_pos + 2
                            speech_end = speech_start
                            while speech_end < len(search_region):
                                byte_val = search_region[speech_end]
                                if byte_val < 0x20 or byte_val >= 0x80:
                                    break
                                speech_end += 1
                            speech_bytes = search_region[speech_start:speech_end]
                            speech_text = speech_bytes.decode('ascii', errors='ignore').strip()
                            if speech_text.endswith('}'):
                                speech_text = speech_text[:-1].rstrip()
                            if speech_text:
                                speech = speech_text
                    
                    
                    # Always check for PROMPT-MARKER pattern, whether we found 0xA4 markers or not
                    # This handles buttons with PROMPT-MARKER but no 0xA4 function markers
                    if not speech:
                        # Check if there's a PROMPT-MARKER pattern in the search region
                        search_start = marker_start if pos_cursor <= marker_start else marker_start
                        # Look ahead from current position to find PROMPT-MARKER
                        search_end = min(pos_cursor + 100, len(data))
                        search_region_data = data[search_start:search_end]
                        
                        
                        if b'\xff\x80{\xfe' in search_region_data:
                            # PROMPT-MARKER found - try to extract speech before it
                            prompt_pos = search_region_data.find(b'\xff\x80{\xfe')
                            speech_bytes = search_region_data[:prompt_pos]
                            
                            # Remove SET-PAGE markers from speech if present
                            if b'\xff\x80\x8c' in speech_bytes:
                                marker_pos = speech_bytes.rfind(b'\xff\x80\x8c')
                                if marker_pos >= 0:
                                    speech_bytes = speech_bytes[:marker_pos]
                            elif b'\xff\x80\x8d' in speech_bytes:
                                marker_pos = speech_bytes.rfind(b'\xff\x80\x8d')
                                if marker_pos >= 0:
                                    speech_bytes = speech_bytes[:marker_pos]
                            
                            # Extract button name from after PROMPT-MARKER
                            name_bytes = search_region_data[prompt_pos + 4:]
                            # Find end of name (null byte or control char)
                            name_end = 0
                            for b in name_bytes:
                                if b < 0x20:
                                    break
                                name_end += 1
                            name_bytes = name_bytes[:name_end]
                            
                            speech_bytes = speech_bytes.replace(b'\x00', b'').strip()
                            if speech_bytes:
                                speech = speech_bytes.decode('ascii', errors='ignore').strip()

                            
                            if name_bytes:
                                button_name = name_bytes.decode('ascii', errors='ignore').strip()
                    elif pos_cursor == marker_start and not speech:
                        # No function markers, do normal speech extraction
                        # Extract speech - direct ASCII text until CRLF (0x0d 0x0a)
                        a4_speech_pos = search_region.find(b'\xa4\x7b')
                        if a4_speech_pos != -1:
                            speech_start = a4_speech_pos + 2
                            speech_end = speech_start
                            while speech_end < len(search_region):
                                byte_val = search_region[speech_end]
                                if byte_val < 0x20 or byte_val >= 0x80:
                                    break
                                speech_end += 1
                            speech_bytes = search_region[speech_start:speech_end]
                            speech_text = speech_bytes.decode('ascii', errors='ignore').strip()
                            if speech_text.endswith('}'):
                                speech_text = speech_text[:-1].rstrip()
                            if speech_text:
                                speech = speech_text
                        if not speech and pos_cursor < len(data):
                            speech_start = pos_cursor
                            while pos_cursor < len(data) - 2:
                                if data[pos_cursor:pos_cursor+2] == b'\r\n':
                                    break
                                pos_cursor += 1
                            
                            speech_bytes = data[speech_start:pos_cursor]
                            
                            # Replace marker byte sequences before processing
                            speech_bytes = speech_bytes.replace(b'\xff\x80{\xfe', '«PROMPT-MARKER»'.encode('utf-8'))
                            
                            # Remove trailing control characters before CRLF
                            while speech_bytes and speech_bytes[-1] < 32:
                                speech_bytes = speech_bytes[:-1]
                            
                            # Remove icon prefix patterns and preserve icon if not already set
                            while speech_bytes and speech_bytes[0] < 0x20:
                                speech_bytes = speech_bytes[1:]
                            
                            # Check for PROMPT-MARKER in speech
                            prompt_name_f1 = None
                            prompt_marker_str = '«PROMPT-MARKER»'
                            if prompt_marker_str.encode('utf-8') in speech_bytes:
                                parts = speech_bytes.split(prompt_marker_str.encode('utf-8'))
                                speech_bytes = parts[0]  # Keep only speech before marker
                                # Extract name from after marker
                                if len(parts) > 1:
                                    raw_name_bytes = parts[-1].strip()
                                    # Extract only alphabetic characters and spaces
                                    clean_chars = []
                                    for byte_val in raw_name_bytes:
                                        if (65 <= byte_val <= 90) or (97 <= byte_val <= 122) or byte_val == 32:  # A-Z, a-z, space
                                            clean_chars.append(chr(byte_val))
                                        elif clean_chars:
                                            # Stop at first non-alphabetic char
                                            break
                                    prompt_name_f1 = ' '.join(''.join(clean_chars).split())
                                    # Only use prompt_name as button name if the current button_name is generic (like "GO-BACK-PAGE")
                                    # or if prompt_name is significantly different/better
                                    if prompt_name_f1 and button_name in ['GO-BACK-PAGE', 'CLEAR-DISPLAY', '', None]:
                                        button_name = prompt_name_f1
                            
                            exc_pos = speech_bytes.find(b'!')
                            caret_pos = speech_bytes.find(b'^')
                            sep_pos = -1
                            if exc_pos != -1 and caret_pos != -1:
                                sep_pos = min(exc_pos, caret_pos)
                            elif exc_pos != -1:
                                sep_pos = exc_pos
                            elif caret_pos != -1:
                                sep_pos = caret_pos
                            
                            if sep_pos != -1 and 0 < sep_pos <= 20:
                                prefix = speech_bytes[:sep_pos]
                                is_icon_name = all(
                                    (65 <= b <= 90) or (48 <= b <= 57) or b == 95 or b == 126
                                    for b in prefix
                                )
                                if is_icon_name and len(prefix) >= 3:
                                    if not icon_name:
                                        icon_name = prefix.decode('ascii', errors='ignore')
                                    speech_bytes = speech_bytes[sep_pos+1:]
                            
                            # Remove function markers from speech bytes
                            # INSERT-DATE: FF 80 67 FE
                            speech_bytes = speech_bytes.replace(b'\xff\x80\x67\xfe', b'')
                            # SPEAK-DATE: FF 80 63 FE
                            speech_bytes = speech_bytes.replace(b'\xff\x80\x63\xfe', b'')
                            # INSERT-TIME: FF 80 66 FE
                            speech_bytes = speech_bytes.replace(b'\xff\x80\x66\xfe', b'')
                            # SPEAK-TIME: FF 80 62 FE
                            speech_bytes = speech_bytes.replace(b'\xff\x80\x62\xfe', b'')                            # Check if these patterns were found and add to functions
                            if insert_date_pos != -1:
                                functions.append('INSERT-DATE')
                            if speak_date_pos != -1:
                                functions.append('SPEAK-DATE')
                            if insert_time_pos != -1:
                                functions.append('INSERT-TIME')
                            if speak_time_pos != -1:
                                functions.append('SPEAK-TIME')
                            
                            # Remove embedded null bytes before decoding
                            speech_bytes = speech_bytes.replace(b'\x00', b'')
                            
                            speech = speech_bytes.decode('ascii', errors='ignore')
                            # Remove trailing high-ASCII characters
                            while speech and ord(speech[-1]) >= 127:
                                speech = speech[:-1]
                            speech = speech.rstrip()
                            
                            # Remove trailing garbage characters (same logic as Format 2)
                            # Pattern 1: Single non-alphanumeric char preceded by space
                            while speech and len(speech) >= 2:
                                if speech[-2] == ' ' and not speech[-1].isalnum() and speech[-1] not in ["'", "!", "?", ".", ","]:
                                    speech = speech[:-1].rstrip()
                                else:
                                    break
                            # Pattern 1b: Single lowercase letter preceded by space - likely garbage
                            if speech and len(speech) >= 2:
                                if speech[-2] == ' ' and len(speech[-1]) == 1 and speech[-1].islower():
                                    speech = speech[:-1].rstrip()
                            # Pattern 1c: Single digit or single uppercase letter preceded by space - likely garbage
                            if speech and len(speech) >= 2:
                                if speech[-2] == ' ' and len(speech[-1]) == 1 and (speech[-1].isdigit() or speech[-1].isupper()):
                                    speech = speech[:-1].rstrip()
                            # Pattern 2: Trailing punctuation that looks like garbage
                            if speech and not speech[-1].isalnum() and speech[-1] not in ["'", "!", "?", ".", ",", ")", '"']:
                                if len(speech) >= 2 and speech[-2].isalnum():
                                    speech = speech[:-1]
                        
                            if not speech:
                                speech = button_name
                    
                    # Fallback for icon buttons: if still no speech after all extraction attempts, use button_name
                    # This handles icon buttons with 0xA4 function markers that don't have explicit speech
                    # Use a marker value to indicate this is a fallback, not extracted speech
                    if not speech and button_name:
                        speech = f"«FALLBACK:{button_name}»"
                        # DEBUG
                        if page_id_str == '0001' and sequence == 11:
                            print(f"DEBUG 0001/11: Set speech = fallback marker for '{button_name}'")
                
                format_stats['Format 1 - Standard'] += 1
                
            # Format 4: Simple speech (name_len 50-100)
            elif 50 <= byte_9 <= 100:
                name_len = byte_9
                extra_buttons = []
                
                # Find the actual end of button name by looking for CRLF marker
                # The name_len might extend past the button boundary, so limit it
                search_limit = pos + 10 + name_len + 10
                crlf_pos = data.find(b'\r\n', pos + 10)
                
                if crlf_pos > 0 and crlf_pos < search_limit:
                    # Use CRLF as the boundary - read only up to CRLF
                    name_bytes = data[pos+10:crlf_pos]
                    button_name = name_bytes.decode('ascii', errors='ignore').strip()
                    pos_cursor = crlf_pos + 2
                else:
                    # Fallback: use name_len
                    name_bytes = data[pos+10:pos+10+name_len]
                    button_name = name_bytes.decode('ascii', errors='ignore').strip()
                    pos_cursor = pos + 10 + name_len
                    
                    # Skip 0x00 separator
                    if pos_cursor < len(data) and data[pos_cursor] == 0:
                        pos_cursor += 1
                
                # Extract text runs from raw name bytes (split on control chars)
                text_runs = []
                current = []
                for b in name_bytes:
                    if 32 <= b < 127:
                        current.append(chr(b))
                    else:
                        if current:
                            run = ''.join(current).strip()
                            if run:
                                text_runs.append(run)
                            current = []
                if current:
                    run = ''.join(current).strip()
                    if run:
                        text_runs.append(run)
                
                # Read speech - look for ^ marker which indicates actual speech start
                speech_start = pos_cursor
                caret_pos = data.find(b'^', pos_cursor)
                
                if caret_pos > 0 and caret_pos < pos_cursor + 100:
                    # Found caret marker, speech starts after it
                    speech_start = caret_pos + 1
                
                # Find end of speech (ONLY stop at m-record, NOT at CRLF for Format 4)
                # CRLF can appear in the middle of multi-line speech
                speech_end = speech_start
                while speech_end < len(data) - 4:
                    if data[speech_end:speech_end+4] == b'm\x00\x04\xfd':  # Next button marker
                        break
                    speech_end += 1
                
                speech_bytes = data[speech_start:speech_end]
                
                # Normalize known marker byte sequences before decoding
                speech_bytes = speech_bytes.replace(b'\xff\x80\x1c\xfe', '«WAIT-ANY-KEY»'.encode('utf-8'))
                speech_bytes = speech_bytes.replace(b'\x1c', '«WAIT-ANY-KEY»'.encode('utf-8'))
                speech_bytes = speech_bytes.replace(b'\xff\x80{\xfe', '«PROMPT-MARKER»'.encode('utf-8'))
                # Remove problematic byte sequences - order matters!
                speech_bytes = speech_bytes.replace(b'?\r\n\x00\x80', b'')  # Literal ? + CRLF+null+0x80
                speech_bytes = speech_bytes.replace(b'\r\n\x00\x80', b'')  # CRLF+null+0x80 combo  
                speech_bytes = speech_bytes.replace(b'?\r\nx\x00\x80', b'')  # Specific corruption pattern
                speech_bytes = speech_bytes.replace(b'\x00\x804r', b'r')  # null+0x80+4r -> r (pe4rformances fix)
                speech_bytes = speech_bytes.replace(b'\x00\x804', b'')  # null+0x80+4 pattern
                speech_bytes = speech_bytes.replace(b'\x00\x80', b'')  # null+0x80
                speech_bytes = speech_bytes.replace(b'\r\n', b'')  # CRLF
                speech_bytes = speech_bytes.replace(b'\x00', b'')  # null
                speech_bytes = speech_bytes.replace(b'\x80', b'')  # 0x80
                speech_bytes = speech_bytes.replace(b'4r', b'r')  # Remove lingering 4r corruption
                speech_bytes = speech_bytes.replace(b'?x4', b'')  # Remove corruption artifacts
                speech_bytes = speech_bytes.replace(b'?x', b'')  # Remove corruption artifacts
                
                speech = speech_bytes.decode('utf-8', errors='ignore').strip()
                
                # Remove any remaining control characters (keep only 32-126 plus guillemets)
                speech = ''.join(ch for ch in speech if (32 <= ord(ch) <= 126) or ch in ['«', '»'])

                # Normalize markers without guillemets to the full marker text
                if 'WAIT-ANY-KEY' in speech and '«WAIT-ANY-KEY»' not in speech:
                    speech = speech.replace('WAIT-ANY-KEY', '«WAIT-ANY-KEY»')

                prompt_name = None
                prompt_token = None
                for token in ['«PROMPT-MARKER»', 'PROMPT-MARKER']:
                    if token in speech:
                        prompt_token = token
                        break
                
                # If PROMPT-MARKER appears in speech, name is after it
                if prompt_token:
                    speech_parts = speech.split(prompt_token)
                    speech_before_marker = speech_parts[0].strip()
                    if len(speech_parts) > 1:
                        raw_prompt_name = speech_parts[-1].strip()
                        # Take all alphabetic words and spaces only
                        clean_chars = []
                        for ch in raw_prompt_name:
                            if ch.isalpha() or ch == ' ':
                                clean_chars.append(ch)
                            elif clean_chars and clean_chars[-1] != ' ':
                                # Hit non-alphabetic char - might be end of name
                                # Only continue if we haven't collected any words yet
                                if ' ' in ''.join(clean_chars) or len(''.join(clean_chars)) > 0:
                                    break  # We have at least one word, stop here
                        
                        # Clean up multiple spaces and trim
                        prompt_name = ' '.join(''.join(clean_chars).split())
                        if not prompt_name:
                            prompt_name = None
                    speech = speech_before_marker
                    
                # Replace «WAIT-ANY-KEY» with [PAUSE] for cleaner speech storage
                speech = speech.replace('«WAIT-ANY-KEY»', '[PAUSE]')
                
                # Fix specific text corruption patterns  
                speech = speech.replace('pe4r', 'per')  # Fix "pe4rformances" → "performances"
                speech = speech.replace('4r', 'r')  # Catch any remaining "4r" patterns
                
                # Select a primary name run for possible split (prefer lowercase/mixed-case)
                candidate_name = None
                for run in text_runs:
                    if any(ch.islower() for ch in run) or ' ' in run:
                        candidate_name = run
                        break
                if not candidate_name and text_runs:
                    candidate_name = text_runs[0]
                if candidate_name:
                    button_name = candidate_name
                
                # If there's a second run that looks like an icon, set icon name
                if len(text_runs) > 1 and not icon_name:
                    possible_icon = text_runs[1]
                    if possible_icon and possible_icon.replace('_', '').isalnum() and possible_icon.upper() == possible_icon and len(possible_icon) <= 12:
                        icon_name = possible_icon
                
                # If prompt_name exists and differs, split into two buttons
                if prompt_name and candidate_name and prompt_name != candidate_name:
                    # Primary button uses the candidate name (e.g., "go back")
                    button_name = candidate_name
                    # Primary button gets no speech (it's a navigation button)
                    speech_for_primary = None
                    
                    # Look for icon name - check multiple sources but exclude speech content words
                    icon_for_secondary = None
                    import re
                    
                    # Common words to exclude (from speech content)
                    exclude_words = {'BIG', 'AIR', 'MAX', 'THE'}
                    
                    # First: Search ALL text_runs for icon patterns (includes name_bytes content)
                    all_candidate_icons = []
                    for run in text_runs:
                        if run and len(run) >= 3 and len(run) <= 12:
                            if run.isupper() or (run[0].isupper() and any(c.isdigit() for c in run)):
                                if run not in ['ROUND', candidate_name.upper()] and run not in exclude_words:
                                    all_candidate_icons.append(run)
                    
                    # Prefer icons with digits (like GRINCH2)
                    for icon in all_candidate_icons:
                        if any(c.isdigit() for c in icon):
                            icon_for_secondary = icon
                            break
                    
                    # If no icon with digits, take first valid uppercase icon
                    if not icon_for_secondary and all_candidate_icons:
                        icon_for_secondary = all_candidate_icons[0]
                    
                    # Fallback: Parse name_bytes directly for uppercase patterns
                    if not icon_for_secondary and name_bytes:
                        name_str = name_bytes.decode('utf-8', errors='ignore')
                        icon_pattern = r'\b([A-Z][A-Z0-9]{2,11})\b'
                        name_icons = re.findall(icon_pattern, name_str)
                        for icon in name_icons:
                            if icon not in ['ROUND'] and icon not in exclude_words:
                                if any(c.isdigit() for c in icon):
                                    icon_for_secondary = icon
                                    break
                    
                    # Secondary button uses prompt_name and carries the speech
                    next_sequence = sequence + 1
                    next_row = next_sequence // 16
                    next_col = next_sequence % 16
                    extra_buttons.append({
                        'page_id': page_id_str,
                        'sequence': next_sequence,
                        'row': next_row,
                        'col': next_col,
                        'name': prompt_name,
                        'icon': icon_for_secondary,
                        'speech': speech if speech else prompt_name,
                        'functions': None,
                        'navigation_type': None,
                        'navigation_target': None
                    })
                    speech = speech_for_primary
                else:
                    # No split needed; if prompt_name exists, use it for this button
                    if prompt_name:
                        button_name = prompt_name
                
                if not speech:
                    speech = button_name
                
                format_stats['Format 4 - Simple speech'] += 1
                
            else:
                format_stats['Complex format'] += 1
                pos += 1
                continue
            
            # NEW LOGIC: Extract speech and name based on PROMPT-MARKER presence
            # Rule: Speech = text OUTSIDE of ALL functions/markers
            #       If PROMPT-MARKER exists: its parameter becomes the button name
            #       If NO PROMPT-MARKER: the text is BOTH speech and name
            if speech:
                speech_str = speech
                has_prompt_marker = '«PROMPT-MARKER»' in speech_str
                
                if has_prompt_marker:
                    # Extract text outside of functions (before first marker or between markers)
                    # and the PROMPT-MARKER parameter as name
                    
                    # Split by « to identify all markers
                    parts = speech_str.split('«')
                    text_outside = []
                    prompt_param = None
                    
                    for i, part in enumerate(parts):
                        if i == 0:
                            # First part, before any marker
                            if part.strip():
                                text_outside.append(part.strip())
                        else:
                            # Part after a « marker
                            # Format: "FUNCTION(params)»rest" or "FUNCTION»rest"
                            if '»' in part:
                                marker_part, rest = part.split('»', 1)
                                # rest is text after this marker
                                if rest.strip() and marker_part != 'PROMPT-MARKER':
                                    # Text after non-PROMPT-MARKER functions is outside
                                    text_outside.append(rest.strip())
                                elif marker_part == 'PROMPT-MARKER':
                                    # PROMPT-MARKER parameter is the rest until next marker/end
                                    prompt_param = rest.strip()
                    
                    # Extract speech as concatenation of outside text
                    speech = ' '.join(text_outside) if text_outside else None
                    
                    # If PROMPT-MARKER parameter exists, use it as name
                    if prompt_param and prompt_param not in ['', None]:
                        if not button_name or button_name == '':
                            button_name = prompt_param
                    
                else:
                    # NO PROMPT-MARKER: text is BOTH speech and name
                    if not button_name or button_name == '':
                        button_name = speech
                    # If name is very short (1-3 chars) but speech is meaningful, use speech as name
                    # This handles cases where parsing picked up junk in the name field
                    elif button_name and speech and len(button_name) <= 3 and len(speech) > len(button_name):
                        button_name = speech
                    
                    # Clean speech to remove control characters (stop at first control char)
                    if speech:
                        clean_speech = []
                        for ch in speech:
                            if ord(ch) < 0x20 and ord(ch) not in [0x09]:  # Stop at control chars except tab
                                break
                            clean_speech.append(ch)
                        speech = ''.join(clean_speech).strip() if clean_speech else None
                        
                        # Also update button_name if it came from speech
                        if button_name and speech and button_name != speech:
                            # button_name might have the junk too, so clean it the same way
                            clean_name = []
                            for ch in button_name:
                                if ord(ch) < 0x20 and ord(ch) not in [0x09]:
                                    break
                                clean_name.append(ch)
                            button_name = ''.join(clean_name).strip() if clean_name else button_name
            
            # Ensure GOTO-HOME buttons have a proper name for display
            if 'GOTO-HOME' in (functions or []) and (not button_name or button_name == ''):
                button_name = 'home'
            
            # If no icon was extracted, use button name as icon
            if not icon_name and button_name:
                icon_name = button_name
            
            # Create button object
            button = {
                'page_id': page_id_str,
                'sequence': sequence,
                'row': row,
                'col': col,
                'name': button_name,
                'icon': icon_name,
                'speech': speech,
                'functions': functions if functions else None,
                'navigation_type': navigation_type,
                'navigation_target': navigation_target
            }
            
            # DEBUG
            if page_id_str == '0001' and sequence == 11:
                print(f"DEBUG 0001/11: Created button with speech='{speech}' (repr: {repr(speech)})")
            
            # Clean up speech: Replace WAIT-ANY-KEY markers with [PAUSE]
            if button['speech']:
                # Stop speech at CRLF or any control character (except space, tab)
                # This prevents reading past button boundaries
                clean_speech = []
                for ch in button['speech']:
                    if ord(ch) < 0x20 and ord(ch) not in [0x09]:  # Stop at control chars except tab
                        break
                    clean_speech.append(ch)
                button['speech'] = ''.join(clean_speech).strip() if clean_speech else None
                
                if not button['speech']:
                    # If speech became empty, skip further processing
                    pass
                else:
                    # Replace 0x1C control character (WAIT-ANY-KEY marker) with [PAUSE]
                    button['speech'] = button['speech'].replace('\x1c', '[PAUSE]')
                
                # Detect and remove VOICE-SET-TEMPORARY marker (0x03 followed by voice params)
                if '\x03' in button['speech']:
                    # Extract voice parameters (format: \x03VoiceName,PersonName u)
                    parts = button['speech'].split('\x03', 1)
                    if len(parts) > 1:
                        # Find the end of voice params (usually ends with 'u' or space)
                        voice_params = parts[1]
                        param_end = 0
                        for i, ch in enumerate(voice_params):
                            if ch == 'u' and i > 0:
                                param_end = i + 1
                                break
                        
                        if param_end > 0:
                            voice_setting = voice_params[:param_end].strip()
                            # Add to functions
                            if not button['functions']:
                                button['functions'] = []
                            button['functions'].append(f'VOICE-SET-TEMPORARY({voice_setting})')
                            # Remove from speech
                            button['speech'] = parts[0] + voice_params[param_end:].strip()
                        else:
                            # No clear end found, just remove the marker
                            button['speech'] = parts[0] + parts[1]
                
                # Detect and remove VOICE-CLEAR-TEMPORARY marker (0x04)
                if '\x04' in button['speech']:
                    # Remove the marker and add to functions
                    button['speech'] = button['speech'].replace('\x04', '')
                    if not button['functions']:
                        button['functions'] = []
                    button['functions'].append('VOICE-CLEAR-TEMPORARY')
                
                # Handle PROMPT-MARKER: text before { is speech, text after is button name
                if '{' in button['speech']:
                    parts = button['speech'].split('{', 1)  # Split only on first {
                    speech_before_marker = parts[0].strip()
                    # Only keep speech if there's actual text before the marker
                    button['speech'] = speech_before_marker if speech_before_marker else None
                    
                    # If the original name contained the marker, it needs updating
                    if len(parts) > 1 and '{' in button['name']:
                        # Extract name from after marker
                        raw_name = parts[-1].strip()
                        clean_chars = []
                        for ch in raw_name:
                            if ch.isalpha() or ch == ' ':
                                clean_chars.append(ch)
                            elif clean_chars:
                                break
                        prompt_name = ' '.join(''.join(clean_chars).split())
                        if prompt_name:
                            button['name'] = prompt_name

            # Clean malformed name artifacts (PROMPT-MARKER / SET-PAGE / duplicated words)
            if button.get('name'):
                import re
                original_name = button['name']
                cleaned_name = original_name

                # Remove guillemet markers like «SET-PAGE(...)» or «PROMPT-MARKER»
                cleaned_name = re.sub(r'«[A-Z\-]+(?:\([^)]*\))?»', '', cleaned_name).strip()

                # Remove raw SET-PAGE(...) text if present
                cleaned_name = re.sub(r'\bSET-PAGE\s*\([^)]*\)', '', cleaned_name, flags=re.IGNORECASE).strip()

                # If marker brace is present, keep text before it (or after if before is empty)
                if '{' in cleaned_name:
                    left, right = cleaned_name.split('{', 1)
                    cleaned_name = left.strip() if left.strip() else right.strip()

                # If navigation target text leaked in, keep leading alphabetic words only
                if re.search(r'\bpage\b', cleaned_name, re.IGNORECASE) or re.search(r'\b0\s+[a-z]', cleaned_name):
                    alpha_match = re.match(r"[A-Za-z ]+", cleaned_name)
                    if alpha_match:
                        cleaned_name = alpha_match.group(0).strip()

                # Collapse duplicate word sequences (e.g., "this weekthis week" -> "this week")
                words = [w for w in cleaned_name.split() if w]
                if len(words) % 2 == 0 and words[:len(words)//2] == words[len(words)//2:]:
                    cleaned_name = " ".join(words[:len(words)//2])

                # Also collapse exact string duplication (no word-boundary split)
                if cleaned_name and len(cleaned_name) % 2 == 0:
                    half = len(cleaned_name) // 2
                    if cleaned_name[:half] == cleaned_name[half:]:
                        cleaned_name = cleaned_name[:half].strip()

                if cleaned_name:
                    button['name'] = cleaned_name

            # Common navigation button names that should have no speech
            nav_button_names = ['home', 'go back', 'goback', 'back', 'return']
            if speech and button_name:
                speech_lower = speech.lower().strip()
                name_lower = button_name.lower().strip()
                # If speech exactly matches name and it's a navigation-like name, clear it
                if speech_lower == name_lower and name_lower in nav_button_names:
                    button['speech'] = None
            
            # Clear speech for navigation buttons only when it appears to be navigation junk
            # (e.g., speech is the nav target itself, not the button label)
            if button.get('navigation_type') and button.get('speech'):
                speech_lower = button['speech'].strip().lower()
                nav_target = button.get('navigation_target', '').strip().lower()
                
                # Clear if speech is contained IN navigation target (like nav target leaked into speech)
                # But DON'T clear just because speech matches button name
                if nav_target and (speech_lower in nav_target or nav_target in speech_lower):
                    button['speech'] = None
                # Clear if speech is the nav target with "0 " prefix removed
                elif nav_target.startswith('0 ') and speech_lower == nav_target[2:].strip():
                    button['speech'] = None

            # Heuristic: Detect GOTO-HOME buttons by icon/speech/label patterns
            if (button.get('icon') == 'HOME' and
                not button.get('speech') and
                (not button.get('functions') or len(button.get('functions')) == 0)):
                button['functions'] = ['GOTO-HOME']
                button['navigation_type'] = 'PERMANENT'
                button['navigation_target'] = '0400'

            if not button.get('functions') and not button.get('navigation_type'):
                name_lower = (button.get('name') or '').strip().lower()
                icon_lower = (button.get('icon') or '').strip().lower()
                if name_lower:
                    is_home_label = name_lower in ['home', 'go home', 'go to home'] or (
                        'home' in name_lower and 'go' in name_lower
                    )
                    has_home_icon = 'home' in icon_lower or 'house' in icon_lower
                    if is_home_label and has_home_icon:
                        button['functions'] = ['GOTO-HOME']
                        button['navigation_type'] = 'PERMANENT'
                        button['navigation_target'] = '0400'
                        button['speech'] = None
            
            # Skip buttons with unsupported functions (like DELETE-LAST-SELECTION)
            # These don't have corresponding app functionality
            raw_name = button.get('name') or ''
            raw_speech = button.get('speech') or ''
            skip_delete_last_selection = (
                'DELETE-LAST-SELECTION' in raw_name or
                'DELETE-LAST-SELECTION' in raw_speech
            )
            # Some MTI files encode DELETE-LAST-SELECTION without text markers.
            # In the 84-button layouts this shows up as an icon-only "o" button with icon='9'.
            skip_delete_last_selection_icon = (
                (button.get('icon') or '').strip() == '9' and
                (button.get('name') or '').strip().lower() == 'o' and
                (button.get('speech') or '').strip().lower() in ['o', ''] and
                not button.get('functions') and
                not button.get('navigation_type') and
                not button.get('navigation_target')
            )
            
            # Clean up button name and speech: remove all control characters (bytes < 0x20 except tab/newline/CR)
            # This ensures stray control chars don't make it into the final JSON
            if button.get('name'):
                cleaned_name = ''.join(c for c in button['name'] if ord(c) >= 0x20 or c in '\t\n\r')
                button['name'] = cleaned_name.rstrip() if cleaned_name else None
            
            if button.get('speech'):
                # Clean the speech
                cleaned_speech = ''.join(c for c in button['speech'] if ord(c) >= 0x20 or c in '\t\n\r')
                button['speech'] = cleaned_speech.rstrip() if cleaned_speech else None


            
            if not (skip_delete_last_selection or skip_delete_last_selection_icon):
                # Add to page
                if page_id_str not in pages:
                    pages[page_id_str] = {
                        'page_id': page_id_str,
                        'inferred_name': f'Page_{page_id_str}',
                        'button_count': 0,
                        'buttons': []
                    }
                
                pages[page_id_str]['buttons'].append(button)
                pages[page_id_str]['button_count'] += 1
                button_count += 1

                # Append any extra buttons (split entries)
                if extra_buttons:
                    for extra_button in extra_buttons:
                        pages[page_id_str]['buttons'].append(extra_button)
                        pages[page_id_str]['button_count'] += 1
                        button_count += 1
            
            # Store 40XX metadata for page naming
            if page_id_str.startswith('40'):
                page_names[(page_id_str, sequence)] = button_name
            
            # Move past this m-record to continue searching
            pos += 4  # Move past the 'm\x00\x04\xfd' marker
            
        except Exception as e:
            pos += 1
            continue
    
    print(f"Extracted {button_count} buttons from {len(pages)} pages")
    
    # POST-PROCESSING: Ensure home/home-like buttons have GOTO-HOME function
    # This catches buttons that might have been parsed but not properly flagged as GOTO-HOME
    for page_id, page_data in pages.items():
        for btn in page_data['buttons']:
            name_lower = (btn.get('name') or '').lower().strip()
            # Clean up the name for checking - keep spaces and alphanumeric
            name_clean = ''.join(c if c.isalnum() or c.isspace() else '' for c in name_lower)
            words = name_clean.split()
            
            # Check if this is specifically a "home" or "go to home" button
            # More precise: "home" alone, or "go to home", or "go home"
            is_home_button = (
                'home' in words and len(words) <= 3 and 
                not any(w in words for w in ['homework', 'homes', 'homemade', 'homeless'])
            )
            
            if is_home_button and (not btn.get('functions') or 'GOTO-HOME' not in btn.get('functions', [])):
                # This is a home button that doesn't have GOTO-HOME function
                # Assign it now
                if not btn.get('functions'):
                    btn['functions'] = []
                if 'GOTO-HOME' not in btn['functions']:
                    btn['functions'] = ['GOTO-HOME']
                    btn['navigation_type'] = 'PERMANENT'
                    btn['navigation_target'] = '0400'
                    # DEBUG: Only print if this looks right (not "homes" or "my home" variations)
                    if len(words) <= 3:
                        print(f"[POST] Assigned GOTO-HOME to {page_id} seq={btn['sequence']}: '{btn['name']}'")
    
    # PHASE 3: Apply metadata overlays to buttons
    print("Phase 3: Applying metadata overlays to buttons...")
    metadata_applied_count = 0
    
    for page_id, page_data in pages.items():
        for btn in page_data['buttons']:
            # Check if this button's name has overlay metadata
            btn_name_lower = btn['name'].lower().strip() if btn['name'] else ''
            
            if btn_name_lower in metadata_map:
                overlay = metadata_map[btn_name_lower]
                # Store the navigation target NAME from metadata
                # (Will be converted to ID in next phase)
                btn['navigation_target'] = overlay['navigation_target_name']
                btn['navigation_type'] = 'PERMANENT'
                metadata_applied_count += 1
    
    print(f"  Applied navigation data to {metadata_applied_count} buttons via metadata overlays")
    
    # Apply page names from 40XX metadata
    # Pattern: Page 40XX, sequence S → defines name for page XXSS
    print("Applying page names from metadata...")
    for (meta_page_id, seq), name in page_names.items():
        # Extract XX from 40XX
        target_prefix = meta_page_id[2:]  # Get last 2 chars
        # Format sequence as 2-digit hex
        target_suffix = f"{seq:02x}"
        target_page_id = target_prefix + target_suffix
        
        if target_page_id in pages:
            pages[target_page_id]['inferred_name'] = name
            print(f"  Page {target_page_id} → '{name}'")

    # Exclude standard Accent template pages from output
    # Exclusion patterns: 84, VS, 45, COMPUTER ACCESS, IT, SCENE BLANK, XPVERB, ZZ
    excluded_pages = []
    for page_id, page_data in list(pages.items()):
        inferred_name = (page_data.get('inferred_name') or '').strip()
        if re.match(r'(?i)^(84|vs|45|computer access|it|scene blank|xpverb|zz)', inferred_name):
            excluded_pages.append({'page_id': page_id, 'inferred_name': inferred_name})
            del pages[page_id]
    if excluded_pages:
        print(f"\nExcluded {len(excluded_pages)} template pages:")
        # Group by prefix
        excluded_84 = [p for p in excluded_pages if re.match(r'(?i)^84', p['inferred_name'])]
        excluded_vs = [p for p in excluded_pages if re.match(r'(?i)^vs', p['inferred_name'])]
        excluded_45 = [p for p in excluded_pages if re.match(r'(?i)^45', p['inferred_name'])]
        excluded_ca = [p for p in excluded_pages if re.match(r'(?i)^computer access', p['inferred_name'])]
        excluded_it = [p for p in excluded_pages if re.match(r'(?i)^it', p['inferred_name'])]
        excluded_sb = [p for p in excluded_pages if re.match(r'(?i)^scene blank', p['inferred_name'])]
        excluded_xp = [p for p in excluded_pages if re.match(r'(?i)^xpverb', p['inferred_name'])]
        excluded_zz = [p for p in excluded_pages if re.match(r'(?i)^zz', p['inferred_name'])]
        
        if excluded_84:
            print(f"  - Pages starting with '84': {len(excluded_84)}")
            for p in sorted(excluded_84, key=lambda x: x['inferred_name'])[:10]:
                print(f"    {p['page_id']}: {p['inferred_name']}")
            if len(excluded_84) > 10:
                print(f"    ... and {len(excluded_84) - 10} more")
        
        if excluded_vs:
            print(f"  - Pages starting with 'VS': {len(excluded_vs)}")
            for p in sorted(excluded_vs, key=lambda x: x['inferred_name'])[:10]:
                print(f"    {p['page_id']}: {p['inferred_name']}")
            if len(excluded_vs) > 10:
                print(f"    ... and {len(excluded_vs) - 10} more")
        
        if excluded_45:
            print(f"  - Pages starting with '45': {len(excluded_45)}")
            for p in sorted(excluded_45, key=lambda x: x['inferred_name']):
                print(f"    {p['page_id']}: {p['inferred_name']}")
        
        if excluded_ca:
            print(f"  - Pages starting with 'COMPUTER ACCESS': {len(excluded_ca)}")
            for p in sorted(excluded_ca, key=lambda x: x['inferred_name']):
                print(f"    {p['page_id']}: {p['inferred_name']}")
        
        if excluded_it:
            print(f"  - Pages starting with 'IT': {len(excluded_it)}")
            for p in sorted(excluded_it, key=lambda x: x['inferred_name']):
                print(f"    {p['page_id']}: {p['inferred_name']}")
        
        if excluded_sb:
            print(f"  - Pages starting with 'SCENE BLANK': {len(excluded_sb)}")
            for p in sorted(excluded_sb, key=lambda x: x['inferred_name']):
                print(f"    {p['page_id']}: {p['inferred_name']}")
        
        if excluded_xp:
            print(f"  - Pages starting with 'XPVERB': {len(excluded_xp)}")
            for p in sorted(excluded_xp, key=lambda x: x['inferred_name']):
                print(f"    {p['page_id']}: {p['inferred_name']}")
        
        if excluded_zz:
            print(f"  - Pages starting with 'ZZ': {len(excluded_zz)}")
            for p in sorted(excluded_zz, key=lambda x: x['inferred_name']):
                print(f"    {p['page_id']}: {p['inferred_name']}")
        print()
    
    # Process navigation and SET-PAGE functions
    print("Processing navigation targets...")
    
    # Build page name to ID map and reverse ID to name map
    page_name_to_id = {page_data['inferred_name'].lower().strip(): page_id 
                       for page_id, page_data in pages.items()}
    page_id_to_name = {page_id: page_data['inferred_name'].lower().strip()
                       for page_id, page_data in pages.items()}
    
    for page_id, page_data in pages.items():
        for btn in page_data['buttons']:
            # Extract SET-PAGE from speech markers
            if btn['speech'] and '\ufffd' in btn['speech']:
                parts = btn['speech'].split('\ufffd')
                for part in parts:
                    part_clean = part.strip().lower()
                    if part_clean in page_name_to_id:
                        btn['navigation_type'] = 'PERMANENT'
                        btn['navigation_target'] = page_name_to_id[part_clean]
                        # Clear speech for navigation-only buttons
                        if not btn['speech'].split('\ufffd')[0].strip() or \
                           btn['speech'].split('\ufffd')[0].strip().endswith(('.', '?')):
                            btn['speech'] = None
                        break
            
            # Check implicit SET-PAGE (speech == name and name matches page)
            # Skip if button has GOTO-HOME function (navigation already set to 'home')
            # CRITICAL FIX: Only apply if button already has navigation indicators (functions, etc)
            # Don't treat speech==name as navigation if the button looks like a regular button
            #  (i.e., has extracted speech/name content with no navigation markers)
            implicit_set_check = (btn['speech'] and btn['name'] and \
               btn['speech'].strip().lower() == btn['name'].strip().lower() and \
               not btn['navigation_type'] and \
               not (btn.get('functions') and 'GOTO-HOME' in btn['functions']))
            
            # Additional check: Only apply if button has functions indicating navigation
            # Regular buttons with extracted text should NOT be treated as implicit navigation
            has_nav_functions = btn.get('functions') and any(
                f for f in btn['functions'] if f in ['GO-BACK-PAGE', 'SET-PAGE', 'GOTO-HOME']
            )
            
            if implicit_set_check and has_nav_functions:
                
                name_lower = btn['name'].strip().lower()
                
                # Try direct match
                if name_lower in page_name_to_id:
                    btn['navigation_type'] = 'PERMANENT'
                    btn['navigation_target'] = page_name_to_id[name_lower]
                    btn['speech'] = None
                # Try with "0 " prefix
                elif f"0 {name_lower}" in page_name_to_id:
                    btn['navigation_type'] = 'PERMANENT'
                    btn['navigation_target'] = page_name_to_id[f"0 {name_lower}"]
                    btn['speech'] = None
            
            # Extract navigation from speech patterns
            if btn['speech'] and not btn['navigation_type']:
                import re
                speech = btn['speech']
                nav_target = None
                clean_speech = speech
                
                # Helper function to find page by name (with normalization)
                def find_page_id(name):
                    name_lower = name.strip().lower()
                    # Try exact match
                    if name_lower in page_name_to_id:
                        return page_name_to_id[name_lower]
                    # Try with "0 " prefix
                    with_prefix = f"0 {name_lower}"
                    if with_prefix in page_name_to_id:
                        return page_name_to_id[with_prefix]
                    # Try fuzzy match (ignore trailing spaces/punctuation)
                    for page_name, page_id in page_name_to_id.items():
                        if page_name.strip().lower() == name_lower:
                            return page_id
                        if page_name.strip().lower() == with_prefix.strip():
                            return page_id
                    return None
                
                # Pattern 1a: (page_name) or (page_name at the end
                match = re.search(r'\(([^)]+)\)\s*[A-Z+\-,;:/]*\s*$', speech)
                if not match:
                    # Pattern 1b: incomplete parenthesis at the end
                    match = re.search(r'\(([^()]+)\s*$', speech)
                if not match:
                    # Pattern 1c: word(s) followed by opening paren at end (e.g., "feelings(")
                    match = re.search(r'\s+([a-z\s]+)\($', speech)
                
                if match:
                    nav_target = find_page_id(match.group(1))
                    if nav_target:
                        # Remove the navigation marker from speech
                        clean_speech = speech[:match.start()].strip()
                
                # Pattern 2: "0 page_name" at the end or as entire speech
                if not nav_target:
                    match = re.search(r'\b0\s+([^.!?]+?)(?:\s*[A-Z+\-,;:/]*)?$', speech)
                    if match:
                        nav_target = find_page_id(match.group(1))
                        if nav_target:
                            # If speech is just "0 page_name", clear it
                            if speech.strip().startswith('0 '):
                                prefix_part = speech[:match.start()].strip()
                                if not prefix_part or prefix_part == '0':
                                    clean_speech = None
                                else:
                                    clean_speech = prefix_part
                            else:
                                clean_speech = speech[:match.start()].strip()
                
                # Pattern 3: :PageName with trailing punctuation (e.g., ":WP- Clothes,")
                if not nav_target and speech.startswith(':'):
                    # Remove leading colon and trailing punctuation
                    content = speech[1:].rstrip(',;:/+')
                    nav_target = find_page_id(content)
                    if nav_target:
                        clean_speech = None
                
                # Pattern 4: :text followed by page_name (space-separated)
                if not nav_target and speech.startswith(':'):
                    # Try to find page name at the end
                    parts = speech[1:].split()
                    if len(parts) > 0:
                        # Check last few words
                        for i in range(len(parts), 0, -1):
                            potential_name = ' '.join(parts[i-1:])
                            nav_target = find_page_id(potential_name)
                            if nav_target:
                                # Keep the text before the page name
                                clean_speech = ' '.join(parts[:i-1]).strip()
                                if not clean_speech:
                                    clean_speech = None
                                break
                
                # Pattern 5: page_name with trailing lowercase letter marker (e.g., "word powerz", "0 don't m")
                # The trailing letter is a navigation marker, not part of the actual text
                if not nav_target and len(speech) > 1:
                    # Try removing the last character if it's a single lowercase letter
                    # Check if removing it gives us a valid page name
                    potential_name = speech[:-1].strip()
                    if potential_name:  # Make sure there's something left
                        nav_target = find_page_id(potential_name)
                        if nav_target:
                            clean_speech = None
                
                # Pattern 6: "text... page_name[digit]" - navigation target at end with trailing digit/letter
                # (e.g., "I want to spell my message, ok? 84 KEYBOARD SCAN7")
                # Guard: only run when speech contains uppercase codes or digits to avoid
                # accidentally matching normal phrases that happen to be page names.
                if not nav_target and ' ' in speech:
                    words = speech.split()
                    has_nav_marker_word = any(
                        any(ch.isdigit() for ch in w) or (w.isupper() and len(w) > 1)
                        for w in words
                    )
                    if has_nav_marker_word:
                        # Look for pattern: sentence ending with space + potential page name + optional trailing char
                        # Try last 2-5 words as potential page name (with optional trailing char)
                        for word_count in range(5, 1, -1):
                            if len(words) >= word_count:
                                potential_with_marker = ' '.join(words[-word_count:])
                                # Try with and without last character
                                for name_to_try in [potential_with_marker, potential_with_marker[:-1]]:
                                    test_target = find_page_id(name_to_try)
                                    if test_target:
                                        nav_target = test_target
                                        # Clean speech is everything before the navigation
                                        clean_speech = ' '.join(words[:-word_count]).strip()
                                        if not clean_speech:
                                            clean_speech = None
                                        break
                                if nav_target:
                                    break
                
                if nav_target:
                    btn['navigation_type'] = 'PERMANENT'
                    btn['navigation_target'] = nav_target
                    btn['speech'] = clean_speech
            
            # Fix navigation targets (convert page names to IDs)
            if btn['navigation_target'] and btn['navigation_target'] not in pages:
                # Try to find page ID from name
                target_clean = btn['navigation_target'].split(')')[0].strip().lower()
                
                if target_clean in page_name_to_id:
                    btn['navigation_target'] = page_name_to_id[target_clean]
                elif f"0 {target_clean}" in page_name_to_id:
                    # Try with "0 " prefix (metadata overlays strip this prefix)
                    btn['navigation_target'] = page_name_to_id[f"0 {target_clean}"]

            # Clear speech if it's obviously junk (contains full navigation target or control chars)
            # This handles Format 3 buttons where speech field may contain page names or junk data
            if btn['navigation_target'] and btn['speech']:
                # Remove control characters from speech for comparison
                speech_clean = ''.join(ch for ch in btn['speech'] if ord(ch) >= 0x20 or ch in '\n\r\t')
                has_control_chars = speech_clean != btn['speech']
                
                # Clear if has control chars (definite junk)
                if has_control_chars:
                    btn['speech'] = None
                # Check if speech is duplicated junk or contains the full page name
                elif btn['navigation_target'] in page_id_to_name:
                    nav_target_page_name = page_id_to_name[btn['navigation_target']]
                    speech_lower = speech_clean.lower().strip()
                    
                    # Only clear if:
                    # 1. Speech is longer than the page name (has extra junk like "peoplepeople 0 people 7-21")
                    # 2. Speech contains the full page name as a substring
                    if len(speech_lower) > len(nav_target_page_name) and \
                       (nav_target_page_name in speech_lower or \
                        nav_target_page_name.replace('0 ', '', 1) in speech_lower):
                        btn['speech'] = None
    
    # Separate metadata pages (40XX range)
    metadata_pages = {pid: pdata for pid, pdata in pages.items() if pid.startswith('4')}
    real_pages = {pid: pdata for pid, pdata in pages.items() if not pid.startswith('4')}
    
    print(f"Found {len(real_pages)} real pages and {len(metadata_pages)} metadata pages")
    
    # Create output structure
    result = {
        'file': mti_file_path.split('/')[-1],
        'extraction_date': datetime.now().strftime('%Y-%m-%d'),
        'extraction_notes': 'COMPLETE - All 5 formats: Standard, Null-terminated (full name=speech), Offset name, Simple speech, Function-based (RANDOM-CHOICE). SET-PAGE navigation extracted: explicit markers in speech + implicit name=page matches. Navigation-only buttons have speech cleared.',
        'total_pages': len(real_pages),
        'total_buttons': sum(p['button_count'] for p in real_pages.values()),
        'metadata_pages_filtered': len(metadata_pages),
        'grid_size': '16 columns (sequence = row * 16 + col)',
        'button_formats': format_stats,
        'pages': real_pages,
        'metadata_pages': metadata_pages
    }
    
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_mti_to_json.py <mti_file_path>")
        sys.exit(1)
    
    mti_file_path = sys.argv[1]
    
    print("=" * 60)
    print("Accent MTI File Extractor")
    print("=" * 60)
    print()
    
    # Extract data
    result = extract_mti_file(mti_file_path)
    
    if result:
        # Save to JSON in the AccentToBravo directory
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, 'all_pages_FINAL.json')
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print()
        print("=" * 60)
        print("Extraction Complete!")
        print("=" * 60)
        print(f"Output file: {output_file}")
        print(f"Total pages: {result['total_pages']}")
        print(f"Total buttons: {result['total_buttons']}")
        print(f"Metadata pages: {result['metadata_pages_filtered']}")
        print()
        print("Format breakdown:")
        for format_name, count in result['button_formats'].items():
            print(f"  {format_name}: {count}")
        print()
    else:
        print("Extraction failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
