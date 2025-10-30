# Image Cleanup System - Quick Reference

## Overview
This system allows you to efficiently remove unwanted images from your Firestore database by simply moving the image files to a `Delete_Images` folder and running a cleanup script.

## Files Created
- `cleanup_images_from_delete_folder.py` - Main cleanup script
- `test_image_cleanup_setup.py` - Setup helper script
- `IMAGE_CLEANUP_GUIDE.md` - This guide

## Quick Start

### 1. Setup (One Time)
```bash
# Create the Delete_Images folder structure
python3 test_image_cleanup_setup.py
```

### 2. Move Unwanted Images
- Navigate to your `BravoImages/batch_XXX_output/` folders
- Move unwanted images to the `Delete_Images/` folder
- You can organize them in subfolders or put them directly in `Delete_Images/`

### 3. Test the Cleanup (ALWAYS DO THIS FIRST)
```bash
# See what would be deleted without actually deleting
python3 cleanup_images_from_delete_folder.py --dry-run --verbose
```

### 4. Run the Actual Cleanup
```bash
# Delete the records from Firestore (with confirmation prompt)
python3 cleanup_images_from_delete_folder.py
```

## Command Options

```bash
# Basic dry run
python3 cleanup_images_from_delete_folder.py --dry-run

# Verbose dry run (shows detailed matching)
python3 cleanup_images_from_delete_folder.py --dry-run --verbose

# Actual cleanup (with confirmation)
python3 cleanup_images_from_delete_folder.py

# Verbose actual cleanup
python3 cleanup_images_from_delete_folder.py --verbose

# Use specific project ID
python3 cleanup_images_from_delete_folder.py --project-id your-project-id
```

## How It Works

### Image Matching
The script matches images to Firestore records using several strategies:

1. **Exact Match**: concept + subconcept match exactly
2. **Fuzzy Subconcept**: subconcept matches but different concept
3. **Tag Match**: subconcept found in image tags
4. **URL Match**: partial filename found in image_url field

### File Name Parsing
Supports these filename formats:
- `concept_subconcept_timestamp.png` (e.g., `animals_cat_20250926_110616.png`)
- `multi_word_subconcept_timestamp.png` (e.g., `ask_for_help_20250927_172732.png`)

### Safety Features
- **Dry run mode**: Test without making changes
- **Automatic backups**: JSON backup created before deletion
- **Confirmation prompt**: Must type 'DELETE' to confirm
- **Detailed logging**: All actions logged with timestamps
- **Error handling**: Continues processing even if some operations fail

## Typical Workflow

1. **Identify bad images** while browsing your BravoImages folders
2. **Move them to Delete_Images/** folder (maintain organization if desired)
3. **Run dry-run test**:
   ```bash
   python3 cleanup_images_from_delete_folder.py --dry-run --verbose
   ```
4. **Review the report** - make sure it's finding the right images
5. **Run actual cleanup**:
   ```bash
   python3 cleanup_images_from_delete_folder.py
   ```
6. **Confirm deletion** by typing 'DELETE' when prompted

## Output Files

### Log Files
- `image_cleanup_YYYYMMDD_HHMMSS.log` - Detailed log of operations

### Backup Files  
- `firestore_backup_YYYYMMDD_HHMMSS.json` - Backup of deleted records

### Reports
The script generates detailed reports showing:
- Number of images found
- Firestore matches by type (exact, fuzzy, etc.)
- What will be/was deleted
- Any errors encountered

## Example Report Output
```
==================================================
FIRESTORE IMAGE CLEANUP REPORT
Generated: 2024-10-13 10:30:00
Mode: DRY RUN
==================================================

SUMMARY:
  Images found in Delete_Images folder: 15
  Firestore matches found: 12
    - Exact matches: 8
    - Fuzzy matches: 4
  Records deleted: 0 (dry run)
  Errors encountered: 0
  Files skipped: 3

DETAILED BREAKDOWN:

  EXACT MATCHES (8):
    - animals/cat (ID: abc12345...) -> cat_20250926_110616.png
    - actions/run (ID: def67890...) -> run_fast_20250927_143022.png
    ...
```

## Troubleshooting

### No Matches Found
- Check filename format matches expected patterns
- Verify images are actually in Firestore database
- Try --verbose mode to see parsing details

### Too Many Matches
- Fuzzy matching might be too broad
- Review matches in dry-run before proceeding
- Consider more specific organization

### Permission Errors
- Ensure Firebase credentials are properly configured
- Check Firestore permissions
- Verify project ID is correct

## Safety Tips

1. **Always use --dry-run first**
2. **Keep backups** - the script creates them automatically
3. **Start small** - test with a few images first
4. **Review reports carefully** before confirming deletion
5. **Keep original images** until you're sure cleanup worked correctly

## Integration with Your Workflow

This system fits naturally into your image management process:
1. Generate images normally
2. Review generated images
3. Move bad ones to Delete_Images/
4. Run cleanup script
5. Deploy any app updates if needed

The cleanup only affects the Firestore database - your original BravoImages files remain untouched in the Delete_Images folder for reference.