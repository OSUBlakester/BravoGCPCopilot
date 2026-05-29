#!/usr/bin/env python3
"""
Migration script: Normalize expanded inflected tags back to their base forms.

This reverses the tag expansion done in Phase 2, converting tags like:
  ['quiero', 'quieres', 'quiere', 'queremos', ...] → ['querer']

Uses the aac_inflection_utils lookup table to identify inflected forms and map them
back to their base forms. Deduplicates and cleans up tags post-migration.

Usage:
  python3 normalize_tags_to_base_forms.py --dry-run                    # Test on 10 records
  python3 normalize_tags_to_base_forms.py --limit 50                   # Migrate 50 records
  python3 normalize_tags_to_base_forms.py                              # Migrate all records
"""

import argparse
import asyncio
from datetime import datetime, timezone
from google.cloud import firestore
from config import CONFIG
from aac_inflection_utils import get_inflection_lookup


def get_available_locales():
    """Get list of locales available in the inflection lookup."""
    lookup = get_inflection_lookup()
    return lookup.get_available_locales()


def normalize_tags_for_locale(tags, locale):
    """
    Normalize a list of tags to base forms for the given locale.
    
    Converts inflected forms back to their base/infinitive forms using
    the inflection lookup table. Non-matching tags are kept as-is.
    
    Args:
        tags: List of tag strings
        locale: Language locale (e.g., 'es', 'es-US')
    
    Returns:
        List of deduplicated base-form tags
    """
    if not tags or not isinstance(tags, list):
        return []
    
    lookup = get_inflection_lookup()
    base_forms = set()
    
    for tag in tags:
        if not tag or not isinstance(tag, str):
            continue
        
        # Try to normalize the tag to its base form
        normalized = lookup.normalize(tag, locale)
        base_forms.add(normalized)
    
    # Return sorted list for consistency
    return sorted(list(base_forms))


async def run_migration(args):
    """Main migration logic."""
    db = firestore.Client(project=CONFIG['gcp_project_id'])
    
    # Get query parameters
    limit = args.limit
    dry_run = args.dry_run
    locales = set(args.locales.split(',')) if args.locales else {'es', 'es-US'}
    available_locales = set(get_available_locales())
    
    # Only process locales that have inflection data
    target_locales = locales & available_locales
    if not target_locales:
        print(f"⚠️  No inflection data for locales: {locales}")
        print(f"   Available: {available_locales}")
        return
    
    print(f"📍 Migration Configuration:")
    print(f"   Target locales: {sorted(target_locales)}")
    print(f"   Dry run: {dry_run}")
    if limit:
        print(f"   Limit: {limit} records")
    print()
    
    # Build query
    q = db.collection('aac_images').where('source', '==', 'bravo_images')
    
    # Apply limit for testing if specified
    if limit:
        q = q.limit(limit)
    
    docs = list(q.stream())
    print(f"📊 Processing {len(docs)} images...")
    print()
    
    processed = 0
    updated = 0
    skipped = 0
    
    for doc in docs:
        processed += 1
        data = doc.to_dict() or {}
        localized_tags = data.get('localized_tags')
        
        # Skip if no localized_tags
        if not localized_tags or not isinstance(localized_tags, dict):
            skipped += 1
            continue
        
        # Normalize tags for each target locale
        normalized_tags = {}
        changed = False
        
        for locale in target_locales:
            if locale not in localized_tags:
                continue
            
            tags = localized_tags[locale]
            if not isinstance(tags, list):
                continue
            
            # Normalize to base forms
            normalized = normalize_tags_for_locale(tags, locale)
            normalized_tags[locale] = normalized
            
            # Track if changed
            if normalized != tags:
                changed = True
        
        # Skip if no changes
        if not changed:
            skipped += 1
            continue
        
        # Prepare update
        update_data = {
            'localized_tags': {**localized_tags, **normalized_tags},
            'updated_at': datetime.now(timezone.utc)
        }
        
        if dry_run:
            old_sample = localized_tags.get(next(iter(target_locales)), [])[:3]
            new_sample = normalized_tags.get(next(iter(target_locales)), [])[:3]
            print(f"DRY-RUN UPDATE {doc.id}:")
            print(f"  Old: {old_sample}")
            print(f"  New: {new_sample}")
            updated += 1
        else:
            await asyncio.to_thread(doc.reference.update, update_data)
            old_sample = localized_tags.get(next(iter(target_locales)), [])[:3]
            new_sample = normalized_tags.get(next(iter(target_locales)), [])[:3]
            print(f"✅ UPDATED {doc.id}:")
            print(f"   Old: {old_sample}")
            print(f"   New: {new_sample}")
            updated += 1
        
        # Progress indicator
        if processed % 50 == 0:
            print(f"   ... {processed}/{len(docs)} processed")
    
    print()
    print("=" * 60)
    print("📊 Migration Summary:")
    print(f"   Processed: {processed}")
    print(f"   Updated:   {updated}")
    print(f"   Skipped:   {skipped}")
    if dry_run:
        print("   Mode:      DRY RUN (no changes to Firestore)")
    print("=" * 60)


def main():
    """Parse arguments and run migration."""
    parser = argparse.ArgumentParser(
        description='Normalize expanded inflected tags back to base forms',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Test on 10 records (dry-run)
  python3 normalize_tags_to_base_forms.py --dry-run
  
  # Normalize 50 Spanish records
  python3 normalize_tags_to_base_forms.py --limit 50 --locales es,es-US
  
  # Normalize all records (production migration)
  python3 normalize_tags_to_base_forms.py
        '''
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without updating Firestore'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of records to process (for testing)'
    )
    parser.add_argument(
        '--locales',
        type=str,
        default='es,es-US',
        help='Comma-separated locale codes to normalize (default: es,es-US)'
    )
    
    args = parser.parse_args()
    
    # Add default limit for dry-run
    if args.dry_run and args.limit is None:
        args.limit = 10
    
    asyncio.run(run_migration(args))


if __name__ == '__main__':
    main()
