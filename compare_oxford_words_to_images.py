#!/usr/bin/env python3
"""
Compare Oxford 3000 words to existing aac_images in Firestore prod.
Identifies missing words categorized by level and part of speech.
"""

import csv
import sys
from collections import defaultdict
from google.cloud import firestore

# Configuration
PROD_PROJECT = "bravo-prod-465323"
CSV_FILE = "Oxford 3000 Words - A1 Nouns List and Next Request.csv"

# Level and part-of-speech mapping based on CSV columns
COLUMN_MAPPING = {
    0: ("A1", "Nouns"),
    1: ("A1", "Verbs"),
    2: ("A1", "Adjectives"),
    3: ("A1", "Adverbs & Others"),
    4: ("A2", "Nouns"),
    5: ("A2", "Verbs"),
    6: ("A2", "Adjectives"),
    7: ("A2", "Adverbs & Others"),
    8: ("B1", "Nouns"),
    9: ("B1", "Verbs"),
    10: ("B1", "Adjectives"),
    11: ("B1", "Adverbs & Others"),
    12: ("B2", "Nouns"),
    13: ("B2", "Verbs"),
    14: ("B2", "Adjectives"),
}


def load_oxford_words():
    """Load Oxford 3000 words from CSV with level and part of speech."""
    words_data = []
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)  # Skip header row
        
        for row in reader:
            for col_idx, word in enumerate(row):
                if word and word.strip() and col_idx in COLUMN_MAPPING:
                    level, pos = COLUMN_MAPPING[col_idx]
                    words_data.append({
                        'word': word.strip().lower(),
                        'level': level,
                        'pos': pos,
                        'original': word.strip()
                    })
    
    print(f"📚 Loaded {len(words_data)} words from Oxford 3000")
    return words_data


def get_existing_images():
    """Query all aac_images from Firestore prod."""
    print(f"🔍 Connecting to Firestore prod: {PROD_PROJECT}")
    db = firestore.Client(project=PROD_PROJECT)
    
    # Get all images
    images_ref = db.collection('aac_images')
    docs = list(images_ref.stream())
    
    print(f"📄 Total documents in aac_images: {len(docs)}")
    
    existing_words = set()
    for doc in docs:
        data = doc.to_dict()
        # Try multiple fields (subconcept is the main one in Firestore)
        for field in ['subconcept', 'searchTerm', 'concept', 'name', 'label', 'text']:
            value = data.get(field, '').lower() if isinstance(data.get(field), str) else ''
            if value:
                existing_words.add(value)
    
    print(f"🖼️  Found {len(existing_words)} unique search terms/names")
    
    # Debug: show first 10 examples
    if existing_words:
        print(f"📝 First 10 examples: {', '.join(list(existing_words)[:10])}")
    
    return existing_words


def categorize_missing_words(oxford_words, existing_images):
    """Compare and categorize missing words."""
    missing_by_category = defaultdict(list)
    
    for word_data in oxford_words:
        word = word_data['word']
        if word not in existing_images:
            category = f"{word_data['level']} - {word_data['pos']}"
            missing_by_category[category].append(word_data['original'])
    
    return missing_by_category


def generate_report(missing_by_category, oxford_words, existing_images):
    """Generate a detailed report."""
    total_oxford = len(oxford_words)
    total_existing = len(existing_images)
    total_missing = sum(len(words) for words in missing_by_category.values())
    
    print("\n" + "="*80)
    print("OXFORD 3000 WORDS - IMAGE COVERAGE REPORT")
    print("="*80)
    print(f"\n📊 Summary:")
    print(f"   Total Oxford 3000 words: {total_oxford}")
    print(f"   Total existing images: {total_existing}")
    print(f"   Total missing images: {total_missing}")
    print(f"   Coverage: {((total_oxford - total_missing) / total_oxford * 100):.1f}%")
    
    print("\n" + "="*80)
    print("MISSING WORDS BY CATEGORY")
    print("="*80)
    
    # Sort by level (A1, A2, B1, B2) and part of speech
    level_order = ["A1", "A2", "B1", "B2"]
    sorted_categories = sorted(
        missing_by_category.items(),
        key=lambda x: (level_order.index(x[0].split(" - ")[0]), x[0])
    )
    
    for category, words in sorted_categories:
        print(f"\n📌 {category}: {len(words)} missing")
        print(f"   {', '.join(sorted(words)[:20])}", end='')
        if len(words) > 20:
            print(f" ... and {len(words) - 20} more")
        else:
            print()
    
    # Save detailed report to file
    output_file = "oxford_missing_words_report.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("OXFORD 3000 WORDS - IMAGE COVERAGE REPORT\n")
        f.write("="*80 + "\n\n")
        f.write(f"Total Oxford 3000 words: {total_oxford}\n")
        f.write(f"Total existing images: {total_existing}\n")
        f.write(f"Total missing images: {total_missing}\n")
        f.write(f"Coverage: {((total_oxford - total_missing) / total_oxford * 100):.1f}%\n\n")
        f.write("="*80 + "\n")
        f.write("MISSING WORDS BY CATEGORY\n")
        f.write("="*80 + "\n\n")
        
        for category, words in sorted_categories:
            f.write(f"\n{category} ({len(words)} words):\n")
            f.write("-" * 40 + "\n")
            for word in sorted(words):
                f.write(f"{word}\n")
    
    print(f"\n💾 Detailed report saved to: {output_file}")
    
    # Also save as CSV for easy import
    csv_output = "oxford_missing_words.csv"
    with open(csv_output, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Level', 'Part of Speech', 'Word'])
        for category, words in sorted_categories:
            level, pos = category.split(" - ")
            for word in sorted(words):
                writer.writerow([level, pos, word])
    
    print(f"📊 CSV export saved to: {csv_output}")


def main():
    try:
        # Load Oxford 3000 words
        oxford_words = load_oxford_words()
        
        # Get existing images from Firestore
        existing_images = get_existing_images()
        
        # Categorize missing words
        missing_by_category = categorize_missing_words(oxford_words, existing_images)
        
        # Generate report
        generate_report(missing_by_category, oxford_words, existing_images)
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find {CSV_FILE}")
        print("   Please ensure the CSV file is in the current directory.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
