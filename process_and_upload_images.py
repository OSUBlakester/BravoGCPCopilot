#!/usr/bin/env python3
"""
All-in-one script for processing and uploading bravo_buddy images.

This script combines:
1. White background to transparent conversion
2. Transparent edge trimming
3. 10% proportional padding (always applied)
4. Square (1:1) aspect ratio conversion
5. Optional upload to Firestore with AI-generated tags

Usage:
    python3 process_and_upload_images.py /path/to/image/directory [--upload] [--project PROJECT] [--replace]
    
Examples:
    # Process images only
    python3 process_and_upload_images.py BravoImages/bravo_buddy_006/Categories
    
    # Process and upload to production
    python3 process_and_upload_images.py BravoImages/bravo_buddy_006/Categories --upload --project bravo-copilot-prod --replace
    
    # Process and upload to dev
    python3 process_and_upload_images.py BravoImages/bravo_buddy_006/Categories --upload --project bravo-copilot-dev
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from PIL import Image
import subprocess

# Target aspect ratio (1.0 = square)
TARGET_ASPECT = 1.0


def make_background_transparent(img, tolerance=40):
    """
    Convert white/light backgrounds to transparent.
    
    Args:
        img: PIL Image object
        tolerance: How close to white (0-255) to make transparent
    
    Returns:
        PIL Image with transparent background
    """
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    data = img.getdata()
    new_data = []
    
    for item in data:
        # Check if pixel is close to white
        if item[0] > 255 - tolerance and item[1] > 255 - tolerance and item[2] > 255 - tolerance:
            # Make it transparent
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    
    img.putdata(new_data)
    return img


def trim_transparent_edges(img, proportional_padding=10):
    """
    Trim transparent edges and ALWAYS add proportional padding.
    
    Args:
        img: PIL Image object (RGBA)
        proportional_padding: Percentage of dimensions to add as padding (default 10%)
    
    Returns:
        Trimmed and padded image, width reduction, height reduction
    """
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Get bounding box of non-transparent content
    bbox = img.getbbox()
    
    if bbox is None:
        # Fully transparent image
        return img, 0, 0
    
    width, height = img.size
    left, upper, right, lower = bbox
    
    width_reduction = (left + (width - right))
    height_reduction = (upper + (height - lower))
    
    # Decide whether to trim
    if width_reduction > 1 or height_reduction > 1:
        # Trim the image to content
        cropped = img.crop(bbox)
    else:
        # No trimming needed, but still continue to padding
        cropped = img
    
    # ALWAYS apply proportional padding (critical fix for Flow images)
    if proportional_padding > 0:
        crop_width, crop_height = cropped.size
        
        # Calculate padding based on percentage of dimensions
        h_pad = int(crop_width * (proportional_padding / 100))
        v_pad = int(crop_height * (proportional_padding / 100))
        
        # Create new image with padding
        new_width = crop_width + (h_pad * 2)
        new_height = crop_height + (v_pad * 2)
        
        padded = Image.new('RGBA', (new_width, new_height), (255, 255, 255, 0))
        padded.paste(cropped, (h_pad, v_pad))
        
        return padded, width_reduction, height_reduction
    
    return cropped, width_reduction, height_reduction


def pad_to_square(img):
    """
    Pad image to exact 1:1 square aspect ratio.
    
    Args:
        img: PIL Image object (RGBA)
    
    Returns:
        Square image with transparent padding
    """
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    width, height = img.size
    
    # Already square
    if width == height:
        return img
    
    # Determine target size (larger dimension)
    target_size = max(width, height)
    
    # Create square canvas
    square = Image.new('RGBA', (target_size, target_size), (255, 255, 255, 0))
    
    # Calculate paste position (center the image)
    paste_x = (target_size - width) // 2
    paste_y = (target_size - height) // 2
    
    square.paste(img, (paste_x, paste_y))
    
    return square


def process_image(image_path, output_path=None):
    """
    Process a single image through all transformations.
    
    Args:
        image_path: Path to input image
        output_path: Path to save output (if None, overwrites input)
    
    Returns:
        Tuple of (original_size, final_size) or None if error
    """
    try:
        img = Image.open(image_path)
        original_size = img.size
        
        # Step 1: Convert background to transparent
        img = make_background_transparent(img, tolerance=40)
        
        # Step 2: Trim transparent edges and add 10% padding
        img, _, _ = trim_transparent_edges(img, proportional_padding=10)
        
        # Step 3: Convert to square
        img = pad_to_square(img)
        
        final_size = img.size
        
        # Save
        if output_path is None:
            output_path = image_path
        
        img.save(output_path, 'PNG')
        
        return original_size, final_size
        
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None


def process_directory(directory_path, create_backup=True):
    """
    Process all PNG images in a directory.
    
    Args:
        directory_path: Path to directory containing images
        create_backup: Whether to create originals_backup folder
    
    Returns:
        Number of images processed
    """
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        return 0
    
    # Create backup folder
    if create_backup:
        backup_dir = directory / "originals_backup"
        backup_dir.mkdir(exist_ok=True)
        print(f"Created backup directory: {backup_dir}")
    
    # Find all PNG files
    png_files = list(directory.glob("*.png"))
    
    if not png_files:
        print(f"No PNG files found in {directory}")
        return 0
    
    print(f"\nFound {len(png_files)} PNG files to process")
    print("=" * 60)
    
    processed_count = 0
    
    for png_file in sorted(png_files):
        # Skip backup directory
        if "originals_backup" in str(png_file):
            continue
        
        # Backup original
        if create_backup:
            backup_path = backup_dir / png_file.name
            if not backup_path.exists():
                shutil.copy2(png_file, backup_path)
        
        # Process image
        result = process_image(png_file)
        
        if result:
            orig_size, final_size = result
            print(f"{png_file.name}: {orig_size[0]}x{orig_size[1]} → {final_size[0]}x{final_size[1]}")
            processed_count += 1
        else:
            print(f"Failed: {png_file.name}")
    
    print("=" * 60)
    print(f"\nProcessed {processed_count} images successfully")
    
    return processed_count


def upload_to_firestore(directory_path, project_id, replace=False):
    """
    Upload processed images to Firestore using bulk_import_bravo_images.py
    
    Args:
        directory_path: Path to directory containing processed images
        project_id: GCP project ID
        replace: Whether to replace existing images
    """
    print("\n" + "=" * 60)
    print("UPLOADING TO FIRESTORE")
    print("=" * 60)
    
    # Get the category name from the parent directory
    directory = Path(directory_path)
    category = directory.parent.name  # e.g., bravo_buddy_006
    
    # Build command
    cmd = [
        "python3",
        "bulk_import_bravo_images.py",
        str(directory),
        category,
        "--project", project_id
    ]
    
    if replace:
        cmd.append("--replace")
    
    print(f"Running: {' '.join(cmd)}\n")
    
    # Run the upload script
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    
    if result.returncode == 0:
        print("\n✅ Upload completed successfully")
    else:
        print(f"\n❌ Upload failed with exit code {result.returncode}")
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Process and optionally upload bravo_buddy images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process images only
  %(prog)s BravoImages/bravo_buddy_006/Categories
  
  # Process and upload to production
  %(prog)s BravoImages/bravo_buddy_006/Categories --upload --project bravo-copilot-prod --replace
  
  # Process and upload to dev
  %(prog)s BravoImages/bravo_buddy_006/Categories --upload --project bravo-copilot-dev
        """
    )
    
    parser.add_argument(
        "directory",
        help="Path to directory containing images to process"
    )
    
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload processed images to Firestore after processing"
    )
    
    parser.add_argument(
        "--project",
        default="bravo-copilot-dev",
        help="GCP project ID for upload (default: bravo-copilot-dev)"
    )
    
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing images in Firestore (use with --upload)"
    )
    
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating originals_backup folder"
    )
    
    args = parser.parse_args()
    
    # Convert to absolute path
    directory_path = Path(args.directory).resolve()
    
    print("=" * 60)
    print("BRAVO IMAGE PROCESSOR")
    print("=" * 60)
    print(f"Directory: {directory_path}")
    print(f"Create backup: {not args.no_backup}")
    print(f"Upload: {args.upload}")
    if args.upload:
        print(f"Project: {args.project}")
        print(f"Replace existing: {args.replace}")
    print("=" * 60)
    
    # Process images
    processed_count = process_directory(directory_path, create_backup=not args.no_backup)
    
    if processed_count == 0:
        print("\n❌ No images were processed")
        return 1
    
    # Upload if requested
    if args.upload:
        return upload_to_firestore(directory_path, args.project, args.replace)
    else:
        print("\n✅ Processing complete (use --upload to upload to Firestore)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
