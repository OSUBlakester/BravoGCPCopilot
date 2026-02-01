#!/usr/bin/env python3
"""
Script to standardize images to 3:4 aspect ratio.
Images close to 3:4 will be padded to exact 3:4.
Images far from 3:4 will be moved to needs_recreation folder.
"""

import os
from pathlib import Path
from PIL import Image
import shutil

# Target aspect ratio (3:4 portrait)
TARGET_ASPECT = 3.0 / 4.0  # 0.75

# Tolerance for "close enough" (0.55 to 1.0 = wider range for portrait-ish images)
ASPECT_MIN = 0.55
ASPECT_MAX = 1.0


def get_aspect_ratio(img):
    """Calculate width/height aspect ratio"""
    return img.width / img.height


def pad_to_aspect_ratio(img, target_aspect):
    """
    Pad image to exact target aspect ratio while maintaining content.
    
    Args:
        img: PIL Image
        target_aspect: Target width/height ratio (e.g., 0.75 for 3:4)
    
    Returns:
        Padded PIL Image
    """
    current_aspect = get_aspect_ratio(img)
    
    if abs(current_aspect - target_aspect) < 0.001:
        # Already at target aspect
        return img
    
    if current_aspect > target_aspect:
        # Image is too wide - add vertical padding
        new_height = int(img.width / target_aspect)
        new_width = img.width
        v_padding = (new_height - img.height) // 2
        h_padding = 0
    else:
        # Image is too tall - add horizontal padding
        new_width = int(img.height * target_aspect)
        new_height = img.height
        h_padding = (new_width - img.width) // 2
        v_padding = 0
    
    # Create new image with padding
    padded = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
    padded.paste(img, (h_padding, v_padding))
    
    return padded


def analyze_and_process_directory(directory, dry_run=True):
    """
    Analyze images in directory and either pad to 3:4 or move to needs_recreation.
    
    Args:
        directory: Path to Categories folder
        dry_run: If True, only report what would be done
    """
    directory = Path(directory)
    
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    # Create needs_recreation folder if needed
    recreation_folder = directory / "needs_recreation"
    
    # Get all PNG files (excluding backups)
    png_files = [f for f in directory.glob("*.png")]
    
    if not png_files:
        print(f"❌ No PNG files found in {directory}")
        return
    
    print(f"\n{'='*70}")
    print(f"📊 ANALYZING: {directory.name}")
    print(f"{'='*70}\n")
    
    close_to_target = []
    needs_recreation = []
    
    # Analyze all images
    for png_file in sorted(png_files):
        with Image.open(png_file) as img:
            aspect = get_aspect_ratio(img)
            size_str = f"{img.width}x{img.height}"
            
            if ASPECT_MIN <= aspect <= ASPECT_MAX:
                # Close enough to pad
                close_to_target.append((png_file, aspect, img.size))
                status = "✓ Can pad to 3:4"
                diff = abs(aspect - TARGET_ASPECT)
            else:
                # Too far - needs recreation
                needs_recreation.append((png_file, aspect, img.size))
                status = "⚠️  Needs recreation"
                diff = abs(aspect - TARGET_ASPECT)
            
            print(f"{png_file.name:40} {size_str:12} aspect={aspect:.3f} {status}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY")
    print(f"{'='*70}")
    print(f"✓ Can pad to 3:4:        {len(close_to_target)} images")
    print(f"⚠️  Needs recreation:     {len(needs_recreation)} images")
    print(f"{'='*70}\n")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes made")
        print("\nImages that would be padded to 3:4:")
        for png_file, aspect, size in close_to_target:
            print(f"  {png_file.name:40} {size[0]}x{size[1]} → 3:4 aspect")
        
        if needs_recreation:
            print(f"\nImages that would be moved to {recreation_folder.name}/:")
            for png_file, aspect, size in needs_recreation:
                print(f"  {png_file.name:40} {size[0]}x{size[1]} (aspect={aspect:.3f})")
        
        return close_to_target, needs_recreation
    
    # Actually process the files
    padded_count = 0
    moved_count = 0
    
    # Pad images close to 3:4
    for png_file, aspect, size in close_to_target:
        with Image.open(png_file) as img:
            original_size = img.size
            padded_img = pad_to_aspect_ratio(img, TARGET_ASPECT)
            padded_img.save(png_file, 'PNG')
            padded_count += 1
            print(f"✓ Padded: {png_file.name} {original_size[0]}x{original_size[1]} → {padded_img.size[0]}x{padded_img.size[1]}")
    
    # Move images that need recreation
    if needs_recreation:
        if not recreation_folder.exists():
            recreation_folder.mkdir()
            print(f"\n📁 Created folder: {recreation_folder.name}/")
        
        for png_file, aspect, size in needs_recreation:
            dest = recreation_folder / png_file.name
            shutil.move(str(png_file), str(dest))
            moved_count += 1
            print(f"📦 Moved: {png_file.name} → {recreation_folder.name}/")
    
    print(f"\n✅ Processed {padded_count} images (padded to 3:4)")
    if moved_count > 0:
        print(f"✅ Moved {moved_count} images to {recreation_folder.name}/")
    
    return close_to_target, needs_recreation


if __name__ == "__main__":
    print("🖼️  ASPECT RATIO STANDARDIZER (3:4 Portrait)")
    print("="*70)
    print("Target: 3:4 aspect ratio (0.75)")
    print(f"Tolerance: {ASPECT_MIN:.2f} - {ASPECT_MAX:.2f}")
    print("="*70)
    
    # Define directories
    base_dir = Path(__file__).parent / "BravoImages"
    dir_003 = base_dir / "bravo_buddy_003" / "Categories"
    dir_004 = base_dir / "bravo_buddy_004" / "Categories"
    
    # First do a dry run to show what would happen
    print("\n🔍 PHASE 1: DRY RUN - Analyzing images...")
    print("="*70)
    
    all_close = []
    all_needs_recreation = []
    
    if dir_003.exists():
        close, needs = analyze_and_process_directory(dir_003, dry_run=True)
        all_close.extend(close)
        all_needs_recreation.extend(needs)
    
    if dir_004.exists():
        close, needs = analyze_and_process_directory(dir_004, dry_run=True)
        all_close.extend(close)
        all_needs_recreation.extend(needs)
    
    # Ask for confirmation
    print("\n" + "="*70)
    print(f"TOTAL: {len(all_close)} images to pad, {len(all_needs_recreation)} to move")
    print("="*70)
    
    response = input("\n✅ Proceed with padding and moving files? (y/N): ").strip().lower()
    
    if response == 'y':
        print("\n🚀 PHASE 2: PROCESSING - Making changes...")
        print("="*70)
        
        if dir_003.exists():
            analyze_and_process_directory(dir_003, dry_run=False)
        
        if dir_004.exists():
            analyze_and_process_directory(dir_004, dry_run=False)
        
        print("\n✅ All done!")
    else:
        print("\n❌ Cancelled - no changes made")
