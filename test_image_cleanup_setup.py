#!/usr/bin/env python3
"""
Test setup script for the image cleanup process

This script helps you:
1. Create the Delete_Images folder structure
2. Move a few test images to test the cleanup process
3. Run the cleanup in dry-run mode to see what would happen

Usage: python3 test_image_cleanup_setup.py
"""

import os
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_delete_folder_structure():
    """Create Delete_Images folder and subfolders"""
    delete_folder = Path("Delete_Images")
    
    if delete_folder.exists():
        logger.info(f"✅ Delete_Images folder already exists")
    else:
        delete_folder.mkdir()
        logger.info(f"✅ Created Delete_Images folder")
    
    # Create some example subfolders to maintain organization
    example_folders = [
        "batch_001_examples",
        "batch_002_examples", 
        "animals_to_remove",
        "actions_to_remove",
        "misc_to_remove"
    ]
    
    for folder in example_folders:
        subfolder = delete_folder / folder
        if not subfolder.exists():
            subfolder.mkdir()
            logger.info(f"  📁 Created {folder}/")
    
    return delete_folder

def find_sample_images():
    """Find some sample images to use for testing"""
    bravo_images = Path("BravoImages")
    sample_images = []
    
    if not bravo_images.exists():
        logger.warning("⚠️ BravoImages folder not found. Cannot find sample images.")
        return sample_images
    
    # Look for a few sample images
    png_files = list(bravo_images.rglob("*.png"))
    
    if png_files:
        # Take first 3 images as samples
        sample_images = png_files[:3]
        logger.info(f"🖼️ Found {len(sample_images)} sample images for testing:")
        for img in sample_images:
            logger.info(f"  - {img}")
    else:
        logger.warning("⚠️ No PNG files found in BravoImages folder")
    
    return sample_images

def show_usage_instructions(delete_folder: Path):
    """Show instructions for using the cleanup system"""
    print(f"""
{'='*60}
🗂️  IMAGE CLEANUP SYSTEM SETUP COMPLETE
{'='*60}

📁  Your Delete_Images folder is ready at: {delete_folder.absolute()}

📝  HOW TO USE THE CLEANUP SYSTEM:

1️⃣  MOVE UNWANTED IMAGES:
   • Navigate to your BravoImages folders (batch_001_output, etc.)
   • Move unwanted images to the Delete_Images folder
   • You can organize them in subfolders or put them directly in Delete_Images/

2️⃣  TEST WITH DRY RUN (RECOMMENDED FIRST):
   • Run: python3 cleanup_images_from_delete_folder.py --dry-run --verbose
   • This shows what would be deleted WITHOUT actually deleting anything
   • Review the report carefully

3️⃣  RUN THE ACTUAL CLEANUP:
   • Run: python3 cleanup_images_from_delete_folder.py
   • You'll be asked to confirm before deletion
   • A backup file will be created automatically

📋  EXAMPLE WORKFLOW:

   # Test first (safe)
   python3 cleanup_images_from_delete_folder.py --dry-run --verbose
   
   # If the results look good, run for real
   python3 cleanup_images_from_delete_folder.py

⚠️   IMPORTANT NOTES:

   • The script matches images by filename patterns (concept_subconcept_timestamp.png)
   • It creates backups before deletion
   • Always run --dry-run first to verify what will be deleted
   • You can organize images in subfolders within Delete_Images/

🔍  MATCHING LOGIC:

   • Exact matches: concept + subconcept match exactly
   • Fuzzy matches: subconcept matches, or found in image tags, or partial URL match
   • Multiple matching strategies ensure images are found even if moved between batches

{'='*60}
✅  READY TO START CLEANING UP YOUR IMAGES!
{'='*60}
""")

def main():
    """Set up the image cleanup system"""
    print("🚀 Setting up Image Cleanup System...")
    
    # Create folder structure  
    delete_folder = create_delete_folder_structure()
    
    # Look for sample images
    sample_images = find_sample_images()
    
    # Show usage instructions
    show_usage_instructions(delete_folder)
    
    # Optional: create example files to show the structure
    example_file = delete_folder / "README.txt"
    if not example_file.exists():
        with open(example_file, 'w') as f:
            f.write("""Delete_Images Folder

This folder is used by the cleanup_images_from_delete_folder.py script.

Instructions:
1. Move unwanted images from BravoImages subfolders to this folder
2. You can organize them in subfolders or put them directly here
3. Run the cleanup script with --dry-run first to test
4. Then run without --dry-run to actually delete from Firestore

The script will match images by filename and delete corresponding Firestore records.
""")
    
    print(f"\n🎯 Next step: Move some unwanted images to {delete_folder}/ and run:")
    print(f"   python3 cleanup_images_from_delete_folder.py --dry-run --verbose")

if __name__ == "__main__":
    main()