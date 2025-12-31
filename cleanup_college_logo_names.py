#!/usr/bin/env python3
"""
Clean up College Logo filenames by removing extra text like -logo-tumb, -Logo-thumb, etc.
Keeps only the college and mascot name.
"""

import os
import re
from pathlib import Path

# Path to the College Logos folder
COLLEGE_LOGOS_DIR = "/Users/blakethomas/Documents/BravoGCPCopilot/BravoImages/College_Logos/College Logos"

# Patterns to remove from filenames (case insensitive)
PATTERNS_TO_REMOVE = [
    r'-[Ll]ogo-\d+x\d+',      # Matches -logo-768x432, -Logo-1024x768, etc.
    r'-[Ll]ogo-[Tt]umb',      # Matches -logo-tumb, -Logo-tumb
    r'-[Ll]ogo-[Tt]humb',     # Matches -logo-thumb, -Logo-thumb
    r'-\d+x\d+',              # Matches dimension patterns like -768x432
    r'\s+[Ll]ogo',            # Matches " logo", " Logo" (with space)
    r'-[Ll]ogo',              # Matches -logo, -Logo
    r'-[Tt]umb',              # Matches -tumb, -Tumb
    r'-[Tt]humb',             # Matches -thumb, -Thumb
    r'-thumbnail',            # Matches -thumbnail
    r'-[Ii]mage',             # Matches -image, -Image
]

def clean_filename(filename):
    """
    Remove extra text from filename while preserving extension.
    Returns the cleaned filename.
    """
    # Split filename and extension
    name, ext = os.path.splitext(filename)
    
    # Apply all removal patterns
    cleaned_name = name
    for pattern in PATTERNS_TO_REMOVE:
        cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE)
    
    # Return cleaned filename with original extension
    return cleaned_name + ext

def main():
    # Check if directory exists
    if not os.path.exists(COLLEGE_LOGOS_DIR):
        print(f"❌ Directory not found: {COLLEGE_LOGOS_DIR}")
        return
    
    print(f"📁 Processing files in: {COLLEGE_LOGOS_DIR}\n")
    
    # Get all files in the directory
    files = [f for f in os.listdir(COLLEGE_LOGOS_DIR) if os.path.isfile(os.path.join(COLLEGE_LOGOS_DIR, f))]
    
    renamed_count = 0
    skipped_count = 0
    
    for filename in files:
        cleaned_filename = clean_filename(filename)
        
        # Check if filename needs to be changed
        if filename != cleaned_filename:
            old_path = os.path.join(COLLEGE_LOGOS_DIR, filename)
            new_path = os.path.join(COLLEGE_LOGOS_DIR, cleaned_filename)
            
            # Check if target filename already exists
            if os.path.exists(new_path):
                print(f"⚠️  SKIP: {filename}")
                print(f"   Target already exists: {cleaned_filename}\n")
                skipped_count += 1
            else:
                # Rename the file
                os.rename(old_path, new_path)
                print(f"✅ RENAMED:")
                print(f"   From: {filename}")
                print(f"   To:   {cleaned_filename}\n")
                renamed_count += 1
        else:
            # Filename is already clean
            pass
    
    # Summary
    print("\n" + "="*60)
    print(f"✨ Cleanup complete!")
    print(f"   Files renamed: {renamed_count}")
    print(f"   Files skipped (target exists): {skipped_count}")
    print(f"   Files already clean: {len(files) - renamed_count - skipped_count}")
    print("="*60)

if __name__ == "__main__":
    main()
