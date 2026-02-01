#!/usr/bin/env python3
"""
Auto-trim whitespace and transparency from images.
This script processes images and removes extra transparent/white space around the content.
"""

from PIL import Image
import os
from pathlib import Path

def trim_image(image_path, output_path=None, padding=0, h_padding=None, v_padding=None, proportional_padding=0):
    """
    Trim transparent or white space from an image.
    
    Args:
        image_path: Path to the input image
        output_path: Path to save trimmed image (if None, overwrites original)
        padding: Number of pixels to add uniformly (overridden by h_padding/v_padding)
        h_padding: Horizontal padding (left/right)
        v_padding: Vertical padding (top/bottom)
        proportional_padding: Percentage of image dimension to add as padding (0-50)
    
    Returns:
        Tuple of (success, width_reduction, height_reduction)
    """
    try:
        # Open the image
        img = Image.open(image_path)
        
        # Store original size
        original_width, original_height = img.size
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Get the bounding box of non-transparent content
        # This finds the smallest rectangle containing all non-transparent pixels
        bbox = img.getbbox()
        
        if bbox is None:
            # Image is completely transparent - skip
            print(f"⚠️  Skipped (fully transparent): {os.path.basename(image_path)}")
            return False, 0, 0
        
        # Calculate size reduction
        width_reduction = original_width - (bbox[2] - bbox[0])
        height_reduction = original_height - (bbox[3] - bbox[1])
        
        # Only trim if there's actual whitespace to remove
        if width_reduction <= 1 and height_reduction <= 1:
            print(f"✓ Skipped (already tight): {os.path.basename(image_path)}")
            return False, 0, 0
        
        # Crop to the bounding box
        cropped = img.crop(bbox)
        
        # Calculate padding values
        if proportional_padding > 0:
            # Add proportional padding based on image dimensions
            h_pad = int(cropped.width * (proportional_padding / 100))
            v_pad = int(cropped.height * (proportional_padding / 100))
        elif h_padding is not None or v_padding is not None:
            # Use specified horizontal and vertical padding
            h_pad = h_padding if h_padding is not None else padding
            v_pad = v_padding if v_padding is not None else padding
        else:
            # Use uniform padding
            h_pad = v_pad = padding
        
        # Add padding if requested
        if h_pad > 0 or v_pad > 0:
            new_width = cropped.width + (h_pad * 2)
            new_height = cropped.height + (v_pad * 2)
            padded = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
            padded.paste(cropped, (h_pad, v_pad))
            cropped = padded
        
        # Save the trimmed image
        if output_path is None:
            output_path = image_path
        
        cropped.save(output_path, 'PNG', optimize=True)
        
        new_width, new_height = cropped.size
        reduction_pct = ((width_reduction + height_reduction) / (original_width + original_height)) * 100
        
        print(f"✂️  Trimmed: {os.path.basename(image_path)}")
        print(f"   {original_width}x{original_height} → {new_width}x{new_height} ({reduction_pct:.1f}% reduction)")
        
        return True, width_reduction, height_reduction
        
    except Exception as e:
        print(f"❌ Error processing {os.path.basename(image_path)}: {e}")
        return False, 0, 0


def trim_directory(directory_path, backup=True, padding=0, h_padding=None, v_padding=None, proportional_padding=0):
    """
    Trim all PNG images in a directory.
    
    Args:
        directory_path: Path to the directory containing images
        backup: If True, creates a backup of original images
        padding: Number of pixels to add uniformly after trimming
        h_padding: Horizontal padding (overrides padding for horizontal)
        v_padding: Vertical padding (overrides padding for vertical)
        proportional_padding: Percentage of image dimension to add as padding (0-50)
    """
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"❌ Directory not found: {directory_path}")
        return
    
    # Create backup directory if requested
    if backup:
        backup_dir = directory / "originals_backup"
        backup_dir.mkdir(exist_ok=True)
        print(f"📁 Backup directory: {backup_dir}")
    
    # Find all PNG files
    png_files = list(directory.glob("*.png"))
    
    if not png_files:
        print(f"⚠️  No PNG files found in {directory_path}")
        return
    
    print(f"\n📊 Found {len(png_files)} PNG files to process")
    
    # Show padding info
    if proportional_padding > 0:
        print(f"🎨 Using proportional padding: {proportional_padding}% of image dimensions")
    elif h_padding is not None or v_padding is not None:
        h_val = h_padding if h_padding is not None else padding
        v_val = v_padding if v_padding is not None else padding
        print(f"🎨 Using padding: {h_val}px horizontal, {v_val}px vertical")
    elif padding > 0:
        print(f"🎨 Using uniform padding: {padding}px")
    
    print(f"{'='*60}\n")
    
    # Process each image
    trimmed_count = 0
    skipped_count = 0
    total_width_reduction = 0
    total_height_reduction = 0
    
    for png_file in sorted(png_files):
        # Create backup if requested
        if backup:
            backup_path = backup_dir / png_file.name
            if not backup_path.exists():
                Image.open(png_file).save(backup_path, 'PNG')
        
        # Trim the image
        success, w_reduction, h_reduction = trim_image(
            png_file, 
            padding=padding,
            h_padding=h_padding,
            v_padding=v_padding,
            proportional_padding=proportional_padding
        )
        
        if success:
            trimmed_count += 1
            total_width_reduction += w_reduction
            total_height_reduction += h_reduction
        else:
            skipped_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY for {directory.name}")
    print(f"   ✂️  Trimmed: {trimmed_count} images")
    print(f"   ✓ Skipped: {skipped_count} images")
    if trimmed_count > 0:
        avg_w_reduction = total_width_reduction / trimmed_count
        avg_h_reduction = total_height_reduction / trimmed_count
        print(f"   📏 Average reduction: {avg_w_reduction:.0f}px width, {avg_h_reduction:.0f}px height")
    if backup:
        print(f"   💾 Backups saved in: {backup_dir.name}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print("🖼️  IMAGE WHITESPACE TRIMMER")
    print("="*60)
    print("This will trim transparent space from images in:")
    print("  - BravoImages/bravo_buddy_003/Categories")
    print("  - BravoImages/bravo_buddy_004/Categories")
    print("="*60)
    
    # Define directories
    base_dir = Path(__file__).parent / "BravoImages"
    dir_003 = base_dir / "bravo_buddy_003" / "Categories"
    dir_004 = base_dir / "bravo_buddy_004" / "Categories"
    
    # Ask for confirmation
    response = input("\nCreate backups before trimming? (Y/n): ").strip().lower()
    backup = response != 'n'
    
    # Padding options
    print("\nPadding options:")
    print("  1. Proportional padding (percentage of image size) - RECOMMENDED")
    print("  2. Fixed padding (same pixels for all images)")
    print("  3. Custom horizontal/vertical padding")
    
    padding_choice = input("\nSelect padding option (1-3, default=1): ").strip() or "1"
    
    padding = 0
    h_padding = None
    v_padding = None
    proportional_padding = 0
    
    if padding_choice == "1":
        response = input("Proportional padding percentage (5-30%, default=15): ").strip()
        try:
            proportional_padding = int(response) if response else 15
            proportional_padding = max(5, min(30, proportional_padding))
        except:
            proportional_padding = 15
        print(f"✓ Using {proportional_padding}% proportional padding")
    
    elif padding_choice == "2":
        response = input("Fixed padding in pixels (0-100, default=50): ").strip()
        try:
            padding = int(response) if response else 50
            padding = max(0, min(100, padding))
        except:
            padding = 50
        print(f"✓ Using {padding}px uniform padding")
    
    elif padding_choice == "3":
        h_response = input("Horizontal padding in pixels (0-200, default=80): ").strip()
        v_response = input("Vertical padding in pixels (0-100, default=20): ").strip()
        try:
            h_padding = int(h_response) if h_response else 80
            v_padding = int(v_response) if v_response else 20
            h_padding = max(0, min(200, h_padding))
            v_padding = max(0, min(100, v_padding))
        except:
            h_padding = 80
            v_padding = 20
        print(f"✓ Using {h_padding}px horizontal, {v_padding}px vertical padding")
    
    print(f"\n🚀 Starting trim process\n")
    
    # Process both directories
    if dir_003.exists():
        trim_directory(dir_003, backup=backup, padding=padding, 
                      h_padding=h_padding, v_padding=v_padding,
                      proportional_padding=proportional_padding)
    else:
        print(f"⚠️  Directory not found: {dir_003}")
    
    if dir_004.exists():
        trim_directory(dir_004, backup=backup, padding=padding,
                      h_padding=h_padding, v_padding=v_padding,
                      proportional_padding=proportional_padding)
    else:
        print(f"⚠️  Directory not found: {dir_004}")
    
    print("✅ Done!")
