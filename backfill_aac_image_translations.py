#!/usr/bin/env python3

import argparse
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

from google.cloud import firestore

from aac_image_translation_utils import (
    AacGeminiTranslator,
    STANDARD_LOCALES,
    dedupe_preserve_order,
    expand_locale_tags_with_inflections,
    locale_bases_set,
    normalize_locale_tag,
    parse_locale_list,
    sanitize_translated_text,
)
from config import CONFIG


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill localized_tags/localized_labels for existing aac_images documents."
    )
    parser.add_argument("--limit", type=int, default=0, help="Max documents to process (0 = no limit)")
    parser.add_argument("--source", default="bravo_images", help="Only process docs with this source value")
    parser.add_argument(
        "--locales",
        default=",".join(STANDARD_LOCALES),
        help="Comma-separated locales to fill, e.g. es-US,fr-FR,de-DE,it-IT,pt-BR,ar-XA",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing locale entries")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing Firestore")
    parser.add_argument(
        "--expand-inflections",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="[DEPRECATED] Expand localized tags with inflected forms. Disabled by default - use client-side normalization instead.",
    )
    parser.add_argument(
        "--inflection-locales",
        default="es",
        help="Comma-separated locales/language codes where inflection expansion is enabled.",
    )
    return parser.parse_args()


def parse_locales(raw: str) -> List[str]:
    locales: List[str] = []
    for token in raw.split(","):
        normalized = normalize_locale_tag(token)
        if normalized and normalized != "en-US" and normalized not in locales:
            locales.append(normalized)
    return locales or STANDARD_LOCALES


def translate_for_locale(
    translator: AacGeminiTranslator,
    english_tags: List[str],
    english_label: str,
    locale: str,
) -> Dict[str, Any]:
    lines = [*english_tags, english_label]
    translated_lines = translator.translate_lines(lines=lines, source_locale="en-US", target_locale=locale)
    translated_tags = dedupe_preserve_order(translated_lines[:-1])
    translated_label = sanitize_translated_text(translated_lines[-1]) if translated_lines else ""
    return {
        "tags": translated_tags,
        "label": translated_label,
    }


async def run_backfill(args: argparse.Namespace) -> None:
    firestore_db = firestore.Client(project=CONFIG["gcp_project_id"])
    translator = AacGeminiTranslator()
    target_locales = parse_locales(args.locales)
    inflection_locale_bases = locale_bases_set(parse_locale_list(args.inflection_locales))

    query = firestore_db.collection("aac_images")
    if args.source:
        query = query.where("source", "==", args.source)
    docs = await asyncio.to_thread(query.get)

    processed = 0
    updated = 0
    skipped = 0

    for doc in docs:
        if args.limit and processed >= args.limit:
            break
        processed += 1

        data = doc.to_dict() or {}
        concept = sanitize_translated_text(data.get("concept", ""))
        subconcept = sanitize_translated_text(data.get("subconcept", ""))
        english_label = subconcept or concept

        tags_raw = data.get("tags")
        english_tags = []
        if isinstance(tags_raw, list):
            english_tags = dedupe_preserve_order([str(tag) for tag in tags_raw])
        if not english_tags:
            english_tags = dedupe_preserve_order([concept, subconcept])

        if not english_label and not english_tags:
            skipped += 1
            print(f"SKIP {doc.id}: no source text")
            continue

        existing_lt = data.get("localized_tags") if isinstance(data.get("localized_tags"), dict) else {}
        existing_ll = data.get("localized_labels") if isinstance(data.get("localized_labels"), dict) else {}

        next_lt: Dict[str, List[str]] = dict(existing_lt)
        next_ll: Dict[str, str] = dict(existing_ll)

        changed = False
        for locale in target_locales:
            has_tags = isinstance(next_lt.get(locale), list) and len(next_lt.get(locale) or []) > 0
            has_label = isinstance(next_ll.get(locale), str) and bool(next_ll.get(locale).strip())
            if not args.overwrite and has_tags and has_label:
                locale_tags = dedupe_preserve_order([str(tag) for tag in (next_lt.get(locale) or [])])
                if args.expand_inflections:
                    expanded_tags = expand_locale_tags_with_inflections(
                        translator=translator,
                        locale=locale,
                        tags=locale_tags,
                        enabled_locale_bases=inflection_locale_bases,
                    )
                    if expanded_tags != locale_tags:
                        next_lt[locale] = expanded_tags
                        changed = True
                continue

            translated = translate_for_locale(
                translator=translator,
                english_tags=english_tags,
                english_label=english_label,
                locale=locale,
            )

            translated_tags = translated["tags"]
            if args.expand_inflections:
                translated_tags = expand_locale_tags_with_inflections(
                    translator=translator,
                    locale=locale,
                    tags=translated_tags,
                    enabled_locale_bases=inflection_locale_bases,
                )

            next_lt[locale] = translated_tags
            next_ll[locale] = translated["label"]
            changed = True

        if not changed:
            skipped += 1
            continue

        update_data = {
            "localized_tags": next_lt,
            "localized_labels": next_ll,
            "updated_at": datetime.now(timezone.utc),
        }

        if args.dry_run:
            print(f"DRY-RUN UPDATE {doc.id}: locales={target_locales}")
        else:
            await asyncio.to_thread(doc.reference.update, update_data)
            print(f"UPDATED {doc.id}: locales={target_locales}")
        updated += 1

    print("\nBackfill complete")
    print(f"Processed: {processed}")
    print(f"Updated:   {updated}")
    print(f"Skipped:   {skipped}")


def main() -> None:
    args = parse_args()
    asyncio.run(run_backfill(args))


if __name__ == "__main__":
    main()