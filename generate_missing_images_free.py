#!/usr/bin/env python3
"""
Generate Missing Images using Google AI Studio FREE TIER (No Batch API)

This script generates images one-by-one using standard generate_content() calls
instead of the Batch API. This stays within the Free Tier limits:
  - ~10 requests per minute (RPM)
  - ~50 images per day (daily quota fluctuates)

The Batch API triggers paid billing even with a free-tier project.
This loop approach avoids that by using inline single requests with rate limiting.

Usage:
    # Step 1: Dry run - see what would be generated
    python generate_missing_images_free.py --dry-run

    # Step 2: Generate images (rate-limited loop)
    python generate_missing_images_free.py --generate

    # Step 3: Generate with a specific limit (e.g., 50 images)
    python generate_missing_images_free.py --generate --limit 50

    # Step 4: Resume from where you left off (skips already-generated)
    python generate_missing_images_free.py --generate --resume

    # Step 5: Move processed entries from missing_images to processed_images
    python generate_missing_images_free.py --finalize

Pipeline:
    generate_missing_images_free.py --generate
        → saves PNGs to BravoImages/batch_missing_images/
    bulk_import_bravo_images.py
        → uploads to GCS & registers in Firestore
    generate_missing_images_free.py --finalize
        → moves missing_images → processed_images in Firestore
"""

import os
import sys
import json
import argparse
import base64
import re
import time
from datetime import datetime
from pathlib import Path

from google.cloud import firestore, secretmanager
from google import genai
from google.genai import types

# --- CONFIGURATION ---
PROJECT_ID = "bravo-prod-465323"
MODEL_ID = "models/gemini-2.5-flash-image"  # Nano Banana - Gemini 2.5 Flash with image generation
OUTPUT_LOCAL_DIR = os.path.join(os.path.dirname(__file__), "BravoImages", "batch_missing_images")
STATE_FILE = os.path.join(os.path.dirname(__file__), ".free_gen_state.json")

# Rate limiting: stay under 10 RPM free tier limit
REQUESTS_PER_MINUTE = 8  # Conservative: 8 RPM (limit is 10)
COOLDOWN_SECONDS = 60 / REQUESTS_PER_MINUTE  # ~7.5 seconds between requests
RETRY_DELAY = 65  # Seconds to wait after a rate limit error
MAX_RETRIES = 3   # Max retries per image on transient errors

# Image generation prompt template (same as batch version)
PROMPT_TEMPLATE = (
    "Generate an image for the AAC vocabulary term: '{term}'. "
    "IMPORTANT: In your text response, you MUST start with exactly: [TERM:{term}] "
    "It is critical that the image is small, but clear. Do not be too abstract. "
    "The image needs to be quickly recognized by the user, who is not literate "
    "and may have a developmental disability. Do not include ANY text at all in the image, none, zero. "
    "A small, simple, illustration with bold line work, strong perimeter lines. "
    "Bright, vibrant, flat colors with subtle shading. "
    "An image clearly communicating or expressively demonstrating '{term}'. "
    "Use basic and generally accepted objects or symbols as needed. "
    "Minimalist details, no extraneous animals, themes, items, people, or body parts. "
    "Isolated on a pure white background and no border"
)


def get_api_key():
    """Get Gemini API key from Secret Manager or environment"""
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if api_key:
        return api_key
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_name = f"projects/{PROJECT_ID}/secrets/bravo-google-api-key/versions/latest"
        response = client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"❌ Could not get API key: {e}")
        print("   Set GEMINI_API_KEY env var or configure Secret Manager")
        sys.exit(1)


def get_missing_images():
    """Fetch all missing images from Firestore"""
    db = firestore.Client(project=PROJECT_ID)
    docs = db.collection("missing_images").where(
        filter=firestore.FieldFilter("status", "==", "missing")
    ).stream()
    
    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append({
            "doc_id": doc.id,
            "search_term": data.get("search_term", doc.id),
            "normalized_term": data.get("normalized_term", doc.id),
            "search_count": data.get("search_count", 0),
        })
    
    # Sort by search_count descending (most requested first)
    results.sort(key=lambda x: x["search_count"], reverse=True)
    return results


def term_to_filename(term):
    """Convert a term to a safe filename (without extension)"""
    return re.sub(r'[^\w\s-]', '', term.lower()).strip().replace(' ', '_')


def get_already_generated():
    """Get set of terms that already have generated images"""
    already = set()
    if os.path.exists(OUTPUT_LOCAL_DIR):
        for f in os.listdir(OUTPUT_LOCAL_DIR):
            if f.endswith((".png", ".jpg")):
                already.add(os.path.splitext(f)[0])
    return already


def generate_single_image(client, term):
    """Generate a single image using generate_content (free tier)"""
    prompt = PROMPT_TEMPLATE.format(term=term)
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            temperature=1.0,
            top_p=0.95,
            top_k=40,
        ),
    )
    
    if not response or not response.candidates:
        return None, "No candidates in response"
    
    # Extract image data from response
    image_data = None
    for candidate in response.candidates:
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                    image_data = part.inline_data
                    break
        if image_data:
            break
    
    if not image_data:
        return None, "No image data in response"
    
    return image_data, None


def save_image(image_data, term):
    """Save image data to local file, return filepath"""
    os.makedirs(OUTPUT_LOCAL_DIR, exist_ok=True)
    
    mime_type = getattr(image_data, 'mime_type', 'image/png')
    ext = "png" if "png" in str(mime_type) else "jpg"
    raw_bytes = image_data.data
    
    if isinstance(raw_bytes, str):
        raw_bytes = base64.b64decode(raw_bytes)
    
    safe_name = term_to_filename(term)
    filename = f"{safe_name}.{ext}"
    filepath = os.path.join(OUTPUT_LOCAL_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(raw_bytes)
    
    return filepath, len(raw_bytes)


def save_state(state):
    """Save generation state to local file"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_state():
    """Load generation state from local file"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return None


# ===== COMMANDS =====

def dry_run():
    """Show what would be generated without actually doing it"""
    print("🔍 Dry Run - Fetching missing images from Firestore...")
    missing_images = get_missing_images()
    
    if not missing_images:
        print("✅ No missing images found!")
        return
    
    already = get_already_generated()
    remaining = [img for img in missing_images if term_to_filename(img["search_term"]) not in already]
    
    print(f"\n📋 Found {len(missing_images)} missing images ({len(already)} already generated locally):\n")
    print(f"{'#':<4} {'Search Term':<30} {'Doc ID':<30} {'Count':<6} {'Status':<10}")
    print("-" * 80)
    
    for i, img in enumerate(missing_images, 1):
        safe = term_to_filename(img["search_term"])
        status = "✅ done" if safe in already else "⏳ pending"
        print(f"{i:<4} {img['search_term']:<30} {img['doc_id']:<30} {img['search_count']:<6} {status}")
    
    print(f"\n📝 Sample prompt for '{missing_images[0]['search_term']}':")
    print(f"   {PROMPT_TEMPLATE.format(term=missing_images[0]['search_term'])[:200]}...")
    
    print(f"\n📦 Total missing: {len(missing_images)}")
    print(f"   Already generated: {len(already)}")
    print(f"   Remaining: {len(remaining)}")
    print(f"📂 Output: {OUTPUT_LOCAL_DIR}")
    print(f"🤖 Model: {MODEL_ID}")
    print(f"⏱️  Rate: {REQUESTS_PER_MINUTE} RPM ({COOLDOWN_SECONDS:.1f}s between requests)")
    
    if remaining:
        est_minutes = len(remaining) * COOLDOWN_SECONDS / 60
        print(f"⏰ Estimated time: ~{est_minutes:.0f} minutes for {len(remaining)} images")
    
    print(f"\n💰 Cost: FREE (using standard generate_content, not Batch API)")


def generate_flow(limit=None, resume=False):
    """Generate images one by one with rate limiting"""
    print("🎨 Starting FREE TIER image generation...\n")
    
    # 1. Fetch missing images
    print("Step 1: Fetching missing images from Firestore...")
    missing_images = get_missing_images()
    
    if not missing_images:
        print("✅ No missing images found! Nothing to generate.")
        return
    
    print(f"  Found {len(missing_images)} missing images\n")
    
    # 2. Filter out already-generated if resuming
    already = get_already_generated() if resume else set()
    if resume and already:
        before = len(missing_images)
        missing_images = [img for img in missing_images if term_to_filename(img["search_term"]) not in already]
        print(f"  Resume mode: skipping {before - len(missing_images)} already-generated images")
        print(f"  Remaining: {len(missing_images)}\n")
    
    if not missing_images:
        print("✅ All images already generated! Nothing to do.")
        return
    
    # 3. Apply limit
    if limit and limit < len(missing_images):
        print(f"  Limiting to {limit} images (of {len(missing_images)} remaining)\n")
        missing_images = missing_images[:limit]
    
    # 4. Initialize client
    api_key = get_api_key()
    client = genai.Client(api_key=api_key)
    os.makedirs(OUTPUT_LOCAL_DIR, exist_ok=True)
    
    # 5. Generate loop
    total = len(missing_images)
    success_count = 0
    fail_count = 0
    skip_count = 0
    generated_terms = []
    generated_doc_ids = []
    start_time = time.time()
    
    est_minutes = total * COOLDOWN_SECONDS / 60
    print(f"🚀 Generating {total} images (~{est_minutes:.0f} min estimated)")
    print(f"   Rate: {REQUESTS_PER_MINUTE} RPM | Cooldown: {COOLDOWN_SECONDS:.1f}s")
    print(f"   Output: {OUTPUT_LOCAL_DIR}\n")
    
    for i, img in enumerate(missing_images):
        term = img["search_term"]
        safe_name = term_to_filename(term)
        
        # Double-check not already generated (race condition with --resume)
        existing_path = os.path.join(OUTPUT_LOCAL_DIR, f"{safe_name}.png")
        if os.path.exists(existing_path):
            print(f"  [{i+1}/{total}] ⏭️  {term} (already exists)")
            skip_count += 1
            generated_terms.append(term)
            generated_doc_ids.append(img["doc_id"])
            continue
        
        # Generate with retry
        success = False
        for attempt in range(MAX_RETRIES):
            try:
                image_data, error = generate_single_image(client, term)
                
                if error:
                    print(f"  [{i+1}/{total}] ⚠️  {term}: {error}")
                    fail_count += 1
                    break  # Don't retry on "no image data" - model issue
                
                filepath, size = save_image(image_data, term)
                elapsed = time.time() - start_time
                rate = (success_count + 1) / (elapsed / 60) if elapsed > 0 else 0
                
                print(f"  [{i+1}/{total}] ✅ {term} ({size:,} bytes) [{rate:.1f} img/min]")
                success_count += 1
                generated_terms.append(term)
                generated_doc_ids.append(img["doc_id"])
                success = True
                break
                
            except Exception as e:
                error_str = str(e).lower()
                
                if "429" in str(e) or "rate" in error_str or "quota" in error_str or "resource_exhausted" in error_str:
                    wait = RETRY_DELAY * (attempt + 1)
                    print(f"  [{i+1}/{total}] ⏳ {term}: Rate limited (attempt {attempt+1}/{MAX_RETRIES}). Waiting {wait}s...")
                    time.sleep(wait)
                elif attempt < MAX_RETRIES - 1:
                    print(f"  [{i+1}/{total}] ⚠️  {term}: Error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
                    time.sleep(10)
                else:
                    print(f"  [{i+1}/{total}] ❌ {term}: Failed after {MAX_RETRIES} attempts: {e}")
                    fail_count += 1
        
        # Rate limit cooldown (skip if we already slept due to an error/retry)
        if i < total - 1:  # Don't sleep after the last one
            time.sleep(COOLDOWN_SECONDS)
    
    # 6. Save state for finalize step
    elapsed = time.time() - start_time
    save_state({
        "generated_at": datetime.now().isoformat(),
        "terms": generated_terms,
        "doc_ids": generated_doc_ids,
        "mode": "free_tier_loop",
    })
    
    print(f"\n{'='*60}")
    print(f"📊 Generation Summary:")
    print(f"  ✅ Success: {success_count}")
    print(f"  ⏭️  Skipped: {skip_count}")
    print(f"  ❌ Failed:  {fail_count}")
    print(f"  ⏱️  Time:   {elapsed/60:.1f} minutes")
    print(f"  📂 Output:  {OUTPUT_LOCAL_DIR}")
    print(f"  💰 Cost:    FREE")
    
    if success_count > 0:
        print(f"\n💡 Next steps:")
        print(f"   1. Review images in {OUTPUT_LOCAL_DIR}")
        print(f"   2. Run: python bulk_import_bravo_images.py")
        print(f"   3. Run: python generate_missing_images_free.py --finalize")
    
    if fail_count > 0:
        print(f"\n⚠️  {fail_count} images failed. Run again with --generate --resume to retry.")


def finalize():
    """Move processed entries from missing_images to processed_images in Firestore"""
    state = load_state()
    if not state:
        print("❌ No generation state found. Run with --generate first.")
        return
    
    doc_ids = state.get("doc_ids", [])
    if not doc_ids:
        print("❌ No doc_ids found in state. Was --generate run properly?")
        return
    
    # Check which images were actually downloaded
    downloaded = set()
    if os.path.exists(OUTPUT_LOCAL_DIR):
        for f in os.listdir(OUTPUT_LOCAL_DIR):
            if f.endswith((".png", ".jpg")):
                downloaded.add(os.path.splitext(f)[0])
    
    db = firestore.Client(project=PROJECT_ID)
    missing_ref = db.collection("missing_images")
    processed_ref = db.collection("processed_images")
    
    moved_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"🔄 Finalizing {len(doc_ids)} entries...\n")
    
    for doc_id in doc_ids:
        try:
            doc = missing_ref.document(doc_id).get()
            if not doc.exists:
                print(f"  ⚠️  {doc_id}: Not found in missing_images (already moved?)")
                skipped_count += 1
                continue
            
            data = doc.to_dict()
            
            safe_name = term_to_filename(data.get('search_term', doc_id))
            has_image = safe_name in downloaded
            
            data["processed_at"] = datetime.now()
            data["generation_mode"] = "free_tier_loop"
            data["image_generated"] = has_image
            if has_image:
                data["local_image_path"] = os.path.join(OUTPUT_LOCAL_DIR, f"{safe_name}.png")
            data["previous_status"] = data.get("status", "missing")
            data["status"] = "processed"
            
            processed_ref.document(doc_id).set(data)
            missing_ref.document(doc_id).delete()
            
            status_icon = "✅" if has_image else "⚠️"
            print(f"  {status_icon} {doc_id}: Moved to processed_images (image: {has_image})")
            moved_count += 1
            
        except Exception as e:
            print(f"  ❌ {doc_id}: Error - {e}")
            error_count += 1
    
    print(f"\n📊 Finalize Summary:")
    print(f"  Moved: {moved_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")
    
    if moved_count > 0:
        print(f"\n💡 Next step: Run bulk_import_bravo_images.py to upload images to GCS and Firestore")


def main():
    global REQUESTS_PER_MINUTE, COOLDOWN_SECONDS
    
    parser = argparse.ArgumentParser(
        description="Generate missing images using Gemini FREE TIER (no Batch API)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dry-run                  Show what would be generated
  %(prog)s --generate                 Generate all missing images
  %(prog)s --generate --limit 50      Generate up to 50 images  
  %(prog)s --generate --resume        Skip already-generated, continue
  %(prog)s --finalize                 Move processed entries in Firestore
        """
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    group.add_argument("--generate", action="store_true", help="Generate images (rate-limited loop)")
    group.add_argument("--finalize", action="store_true", help="Move processed entries to processed_images collection")
    
    parser.add_argument("--limit", type=int, default=None, help="Max number of images to generate (default: all)")
    parser.add_argument("--resume", action="store_true", help="Skip images that already exist locally")
    parser.add_argument("--rpm", type=int, default=REQUESTS_PER_MINUTE, help=f"Requests per minute (default: {REQUESTS_PER_MINUTE})")
    
    args = parser.parse_args()
    
    # Allow RPM override
    if args.rpm != REQUESTS_PER_MINUTE:
        REQUESTS_PER_MINUTE = max(1, min(10, args.rpm))
        COOLDOWN_SECONDS = 60 / REQUESTS_PER_MINUTE
        print(f"⚙️  RPM override: {REQUESTS_PER_MINUTE} ({COOLDOWN_SECONDS:.1f}s cooldown)\n")
    
    if args.dry_run:
        dry_run()
    elif args.generate:
        generate_flow(limit=args.limit, resume=args.resume)
    elif args.finalize:
        finalize()


if __name__ == "__main__":
    main()
