#!/usr/bin/env python3
"""
Simple script to import reorganized batch_009 files to Firestore.
Uses the same authentication method as our cleanup script.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
from pathlib import Path

def initialize_firebase():
    """Initialize Firebase using gcloud auth"""
    try:
        app = firebase_admin.get_app()
        print("Firebase app already initialized")
        return firestore.client()
    except ValueError:
        try:
            firebase_admin.initialize_app()
            print("Firebase initialized with Application Default Credentials (gcloud auth)")
            return firestore.client()
        except Exception as e:
            print(f"Failed to initialize Firebase: {e}")
            return None

def import_batch_009_files(db, batch_009_path):
    """Import reorganized batch_009 files"""
    batch_009_path = Path(batch_009_path)
    
    if not batch_009_path.exists():
        print(f"Batch 009 path not found: {batch_009_path}")
        return 0
    
    print(f"Importing files from: {batch_009_path}")
    
    imported_count = 0
    errors = []
    
    # Process each conceptual subfolder
    for concept_folder in batch_009_path.iterdir():
        if not concept_folder.is_dir():
            continue
            
        concept_name = concept_folder.name
        print(f"\nProcessing concept: {concept_name}")
        
        # Find all PNG files in this concept folder
        png_files = list(concept_folder.glob("*.png"))
        print(f"  Found {len(png_files)} images")
        
        for png_file in png_files:
            try:
                # Extract subconcept from filename (remove timestamp)
                stem_parts = png_file.stem.split('_')
                # Find where timestamp starts (8 digits)
                timestamp_idx = -1
                for i, part in enumerate(stem_parts):
                    if len(part) == 8 and part.isdigit():
                        timestamp_idx = i
                        break
                
                if timestamp_idx > 0:
                    subconcept = '_'.join(stem_parts[:timestamp_idx])
                else:
                    subconcept = stem_parts[0]
                
                # Create Firestore document
                doc_data = {
                    'concept': concept_name,
                    'subconcept': subconcept,
                    'source': 'bravo_images',
                    'filename': png_file.name,
                    'batch': 'batch_009',
                    'reorganized': True,
                    'image_path': str(png_file),
                    'tags': [subconcept.replace('_', ' '), concept_name.replace('_', ' ')],
                    'created_at': firestore.SERVER_TIMESTAMP
                }
                
                # Add to Firestore
                db.collection('aac_symbols').add(doc_data)
                imported_count += 1
                
                if imported_count % 10 == 0:
                    print(f"  Imported {imported_count}...")
                    
            except Exception as e:
                error_msg = f"Error importing {png_file.name}: {e}"
                errors.append(error_msg)
                print(f"  ❌ {error_msg}")
    
    return imported_count, errors

def main():
    """Main function"""
    print("Batch 009 Simple Import Script")
    print("=" * 40)
    
    # Initialize Firebase
    db = initialize_firebase()
    if not db:
        print("Failed to initialize Firebase. Exiting.")
        return
    
    # Import batch_009 files
    batch_009_path = "/Users/blakethomas/Documents/BravoGCPCopilot/BravoImages/batch_009_output"
    imported_count, errors = import_batch_009_files(db, batch_009_path)
    
    print(f"\n🎉 Import complete!")
    print(f"📊 Successfully imported: {imported_count} files")
    print(f"❌ Errors: {len(errors)}")
    
    if errors:
        print("\nFirst few errors:")
        for error in errors[:3]:
            print(f"  {error}")

if __name__ == "__main__":
    main()
