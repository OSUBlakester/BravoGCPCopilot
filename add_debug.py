#!/usr/bin/env python3
"""
Trace extraction for page 2117, sequence 34 by adding debug output
"""
import sys

# Patch the extraction to add debug output
code = open('extract_mti_to_json.py').read()

# Find the section where page 2117 seq 34 would be processed and add debug
lines = code.split('\n')
new_lines = []

for i, line in enumerate(lines):
    new_lines.append(line)
    
    # Add debug output when creating button object
    if "button = {" in line and "'page_id': page_id_str," in lines[i+1]:
        # Insert debug before button creation
        indent = len(line) - len(line.lstrip())
        new_lines.insert(-1, " " * indent + "if page_id_str == '2117' and sequence == 34:")
        new_lines.insert(-1, " " * (indent + 4) + "print(f\"DEBUG 2117/34 before button creation:\")")
        new_lines.insert(-1, " " * (indent + 4) + "print(f\"  button_name={repr(button_name)}\")")
        new_lines.insert(-1, " " * (indent + 4) + "print(f\"  speech={repr(speech)}\")")
        new_lines.insert(-1, " " * (indent + 4) + "print(f\"  icon_name={repr(icon_name)}\")")

# Write modified code
with open('extract_mti_to_json_debug.py', 'w') as f:
    f.write('\n'.join(new_lines))

print("Created extract_mti_to_json_debug.py with debug output")
print("Run: python3 extract_mti_to_json_debug.py 'AccentToBravo/max user 1 2026 feb.mti' debug.json 2>&1 | grep -A 10 '2117/34'")
