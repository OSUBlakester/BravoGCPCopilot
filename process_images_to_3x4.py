#!/usr/bin/env python3
"""
Script to process images to 3:4 aspect ratio:
1. Convert white background to transparent
2. Trim transparent edges
3. Pad to exact 3:4 aspect ratio
"""

import os
from pathlib import Path
from PIL import Image
import shutil

# Target aspect ratio (1:1 square)
TARGET_ASPECT = 1.0  # 1.0 for square


def make_background_transparent(img, tolerance=30):
    """Convert white/light backgrounds to transparent"""
    img = img.convert("RGBA")
    datas = img.getdata()
    
    newData = []
    for item in datas:
        # Check if pixel is white or near-white
        if item[0] > 255 - tolerance and item[1] > 255 - tolerance and item[2] > 255 - tolerance:
            # Make it transparent
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    
    img.putdata(newData)
    return img


def trim_transparent_edges(img, proportional_padding=10):
    """
    Trim transparent edges from the image and add proportional padding
    
    Args:
        img: PIL Image
        proportional_padding: Percentage of image dimensions to add as padding (default 10%)
    """
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Get the bounding box of non-transparent content
    bbox = img.getbbox()
    
    if bbox is None:
        # Image is completely transparent - return as is
        return img, 0, 0
    
    # Calculate reduction
    width_reduction = img.width - (bbox[2] - bbox[0])
    height_reduction = img.height - (bbox[3] - bbox[1])
    
    # Crop to bounding box if there's significant whitespace
    if width_reduction > 1 or height_reduction > 1:
        cropped = img.crop(bbox)
    else:
        # No trimming needed, but still use the image
        cropped = img
        width_reduction = 0
        height_reduction = 0
    
    # Always add proportional padding to give breathing room
    if proportional_padding > 0:
        h_pad = int(cropped.width * (proportional_padding / 100))
        v_pad = int(cropped.height * (proportional_padding / 100))
        
        new_width = cropped.width + (h_pad * 2)
        new_height = cropped.height + (v_pad * 2)
        padded = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
        padded.paste(cropped, (h_pad, v_pad))
        cropped = padded
    
    return cropped, width_reduction, height_reduction


def pad_to_square(img):
    """
    Pad image to exact 1:1 (square) aspect ratio while maintaining content.
    
    Args:
        img: PIL Image
    
    Returns:
        Padded PIL Image at 3:4 aspect ratio
    """
    current_aspect = img.width / img.height
    
    if abs(current_aspect - TARGET_ASPECT) < 0.001:
        # Already at target aspect
        return img
    
    if current_aspect > TARGET_ASPECT:
        # Image is too wide - add vertical padding
        new_height = int(img.width / TARGET_ASPECT)
        new_width = img.width
        v_padding = (new_height - img.height) // 2
        h_padding = 0
    else:
        # Image is too tall - add horizontal padding
        new_width = int(img.height * TARGET_ASPECT)
        new_height = img.height
        h_padding = (new_width - img.width) // 2
        v_padding = 0
    
    # Create new image with padding
    padded = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
    padded.paste(img, (h_padding, v_padding))
    
    return padded


def process_image(image_path, output_path=None):
    """
    Process a single image: transparency, trim, pad to 3:4
    
    Returns:
        Tuple of (success, original_size, final_size)
    """
    try:
        with Image.open(image_path) as img:
            original_size = img.size
            
            # Step 1: Convert white to transparent
            transparent_img = make_background_transparent(img)
            
            # Step 2: Trim transparent edges
            trimmed_img, w_reduction, h_reduction = trim_transparent_edges(transparent_img)
            
            # Step 3: Pad to 1:1 (square) aspect ratio
            final_img = pad_to_square(trimmed_img)
            
            # Save
            if output_path is None:
                output_path = image_path
            
            final_img.save(output_path, 'PNG')
            
            return True, original_size, final_img.size
    
    except Exception as e:
        print(f"❌ Error processing {image_path.name}: {e}")
        return False, (0, 0), (0, 0)


def process_directory(directory, backup=True):
    """
    Process all PNG files in a directory
    
    Args:
        directory: Path to directory
        backup: Create backup before processing
    """
    directory = Path(directory)
    
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    # Get all PNG files
    png_files = sorted([f for f in directory.glob("*.png")])
    
    if not png_files:
        print(f"❌ No PNG files found in {directory}")
        return
    
    print(f"\n{'='*70}")
    print(f"📊 PROCESSING: {directory.name}")
    print(f"Found {len(png_files)} PNG files")
    print(f"{'='*70}\n")
    
    # Create backup if requested
    if backup:
        backup_dir = directory / "originals_backup"
        if not backup_dir.exists():
            backup_dir.mkdir()
            print(f"📁 Created backup folder: {backup_dir.name}/\n")
        else:
            print(f"📁 Using existing backup folder: {backup_dir.name}/\n")
    
    processed_count = 0
    skipped_count = 0
    
    for png_file in png_files:
        # Create backup if requested
        if backup:
            backup_path = backup_dir / png_file.name
            if not backup_path.exists():
                shutil.copy2(png_file, backup_path)
        
        # Process the image
        success, original_size, final_size = process_image(png_file)
        
        if success:
            processed_count += 1
            print(f"✓ {png_file.name:40} {original_size[0]}x{original_size[1]} → {final_size[0]}x{final_size[1]}")
        else:
            skipped_count += 1
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY for {directory.name}")
    print(f"   ✓ Processed: {processed_count} images")
    if skipped_count > 0:
        print(f"   ❌ Failed: {skipped_count} images")
    if backup:
        print(f"   💾 Backups saved in: {backup_dir.name}/")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    print("🖼️  IMAGE PROCESSOR TO 1:1 (SQUARE) ASPECT RATIO")
    print("="*70)
    print("This will:")
    print("  1. Convert white backgrounds to transparent")
    print("  2. Trim transparent edges")
    print("  3. Add 10% proportional padding for breathing room")
    print("  4. Pad to exact 1:1 (square) aspect ratio")
    print("="*70)
    
    # Define directories
    base_dir = Path(__file__).parent / "BravoImages"
    
    # You can specify custom directories here
    print("\nEnter directory path (or press Enter for needs_recreation folders):")
    custom_path = input("> ").strip()
    
    if custom_path:
        # Process custom directory
        process_directory(Path(custom_path), backup=True)
    else:
        # Process needs_recreation folders by default
        dir_003 = base_dir / "bravo_buddy_003" / "Categories" / "needs_recreation"
        dir_004 = base_dir / "bravo_buddy_004" / "Categories" / "needs_recreation"
        
        response = input("\nCreate backups before processing? (Y/n): ").strip().lower()
        backup = response != 'n'
        
        if dir_003.exists():
            process_directory(dir_003, backup=backup)
        else:
            print(f"⚠️  Directory not found: {dir_003}")
        
        if dir_004.exists():
            process_directory(dir_004, backup=backup)
        else:
            print(f"⚠️  Directory not found: {dir_004}")
    
    print("✅ Done!")
