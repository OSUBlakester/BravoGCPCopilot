#!/usr/bin/env python3
"""
Convert JPEG images to PNG format

This script converts all JPEG/JPG images in a specified directory to PNG format.
You can choose to keep or delete the original JPEG files after conversion.
"""

import os
from pathlib import Path
from PIL import Image


def convert_jpegs_to_png(directory_path: str, delete_originals: bool = False):
    """
    Convert all JPEG images in a directory to PNG format.
    
    Args:
        directory_path: Path to the directory containing JPEG images
        delete_originals: Whether to delete original JPEG files after conversion
    """
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"❌ Error: Directory does not exist: {directory_path}")
        return
    
    if not directory.is_dir():
        print(f"❌ Error: Path is not a directory: {directory_path}")
        return
    
    # Find all JPEG files (case-insensitive)
    jpeg_extensions = ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG']
    jpeg_files = []
    for ext in jpeg_extensions:
        jpeg_files.extend(directory.glob(ext))
    
    if not jpeg_files:
        print(f"ℹ️  No JPEG files found in: {directory_path}")
        return
    
    print(f"📁 Found {len(jpeg_files)} JPEG file(s) in: {directory_path}")
    print()
    
    converted_count = 0
    error_count = 0
    
    for jpeg_file in jpeg_files:
        try:
            # Create PNG filename
            png_file = jpeg_file.with_suffix('.png')
            
            # Skip if PNG already exists
            if png_file.exists():
                print(f"⏭️  Skipped (PNG exists): {jpeg_file.name} -> {png_file.name}")
                continue
            
            # Open and convert image
            with Image.open(jpeg_file) as img:
                # Convert to RGB if necessary (JPEG doesn't support transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Keep transparency for images that have it
                    img.save(png_file, 'PNG')
                else:
                    # Convert to RGB for standard JPEGs
                    rgb_img = img.convert('RGB')
                    rgb_img.save(png_file, 'PNG')
            
            print(f"✅ Converted: {jpeg_file.name} -> {png_file.name}")
            converted_count += 1
            
            # Delete original if requested
            if delete_originals:
                jpeg_file.unlink()
                print(f"   🗑️  Deleted original: {jpeg_file.name}")
        
        except Exception as e:
            print(f"❌ Error converting {jpeg_file.name}: {e}")
            error_count += 1
    
    print()
    print("=" * 60)
    print(f"✨ Conversion complete!")
    print(f"   Converted: {converted_count}")
    print(f"   Errors: {error_count}")
    print(f"   Skipped: {len(jpeg_files) - converted_count - error_count}")
    print("=" * 60)


def main():
    """Main function to run the conversion script."""
    print("=" * 60)
    print("🖼️  JPEG to PNG Converter")
    print("=" * 60)
    print()
    
    # Prompt for directory path
    directory_path = input("Enter the directory path containing JPEG images:\n> ").strip()
    
    # Remove quotes if user copied path with quotes
    directory_path = directory_path.strip('"').strip("'")
    
    if not directory_path:
        print("❌ Error: No path provided")
        return
    
    # Expand home directory if using ~
    directory_path = os.path.expanduser(directory_path)
    
    print()
    print(f"📂 Target directory: {directory_path}")
    print()
    
    # Ask if user wants to delete originals
    delete_response = input("Delete original JPEG files after conversion? (y/N): ").strip().lower()
    delete_originals = delete_response in ('y', 'yes')
    
    if delete_originals:
        confirm = input("⚠️  Are you sure? This cannot be undone! (yes/N): ").strip().lower()
        if confirm != 'yes':
            delete_originals = False
            print("ℹ️  Original files will be kept.")
    
    print()
    print("🔄 Starting conversion...")
    print()
    
    # Run conversion
    convert_jpegs_to_png(directory_path, delete_originals)


if __name__ == "__main__":
    main()
