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

firestore = None
secretmanager = None
genai = None
types = None

# --- CONFIGURATION ---
PROJECT_ID = "bravo-prod-465323"
MODEL_ID = "models/gemini-2.5-flash-image"
OUTPUT_LOCAL_DIR = os.path.join(os.path.dirname(__file__), "BravoImages", "batch_missing_images")
STATE_FILE = os.path.join(os.path.dirname(__file__), ".free_gen_state.json")
DAILY_STATE_FILE = os.path.join(os.path.dirname(__file__), ".free_gen_daily_state.json")
API_KEY_SECRET_NAME = os.environ.get("GEMINI_API_KEY_SECRET", "BRAVO_IMAGE_API")
API_KEY_SECRET_PROJECT = os.environ.get("GEMINI_API_KEY_SECRET_PROJECT", "gen-lang-client-0169791668")

# Rate limiting: stay under 10 RPM free tier limit
REQUESTS_PER_MINUTE = 8  # Conservative: 8 RPM (limit is 10)
COOLDOWN_SECONDS = 60 / REQUESTS_PER_MINUTE  # ~7.5 seconds between requests
RETRY_DELAY = 65  # Seconds to wait after a rate limit error
MAX_RETRIES = 3   # Max retries per image on transient errors
FAIL_FAST_ON_QUOTA_EXHAUSTED = True
DEFAULT_DAILY_LIMIT = 25
KNOWN_GOOD_CA_BUNDLE = "/Library/Frameworks/Python.framework/Versions/3.12/etc/openssl/cert.pem"

# Image generation prompt template (same as batch version)
PROMPT_TEMPLATE = (
    "Generate an image for the AAC vocabulary term: '{term}'. "
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


def get_firestore_module():
    """Lazy-load Firestore to avoid long silent startup delay."""
    global firestore
    if firestore is None:
        print("⏳ Loading Firestore library...", flush=True)
        from google.cloud import firestore as firestore_module
        firestore = firestore_module
        print("✅ Firestore library loaded", flush=True)
    return firestore


def get_secretmanager_module():
    """Lazy-load Secret Manager to avoid long silent startup delay."""
    global secretmanager
    if secretmanager is None:
        print("⏳ Loading Secret Manager library...", flush=True)
        from google.cloud import secretmanager as secretmanager_module
        secretmanager = secretmanager_module
        print("✅ Secret Manager library loaded", flush=True)
    return secretmanager


def get_genai_modules():
    """Lazy-load GenAI SDK to avoid long silent startup delay."""
    global genai, types
    if genai is None or types is None:
        print("⏳ Loading Gemini SDK...", flush=True)
        from google import genai as genai_module
        from google.genai import types as types_module
        genai = genai_module
        types = types_module
        print("✅ Gemini SDK loaded", flush=True)
    return genai, types


def ensure_ssl_ca_bundle():
    """Work around broken venv certifi bundle on macOS Python.org installs."""
    if os.environ.get("SSL_CERT_FILE") and os.environ.get("REQUESTS_CA_BUNDLE"):
        return

    if os.path.exists(KNOWN_GOOD_CA_BUNDLE):
        os.environ.setdefault("SSL_CERT_FILE", KNOWN_GOOD_CA_BUNDLE)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", KNOWN_GOOD_CA_BUNDLE)
        print(f"🔒 Using CA bundle: {KNOWN_GOOD_CA_BUNDLE}", flush=True)


def clean_api_key(raw_key):
    """Normalize pasted API key text (strip quotes/whitespace/smart quotes)."""
    if raw_key is None:
        return None

    key = str(raw_key).strip()
    key = key.strip("\"'")
    key = key.strip("“”‘’")
    return key


def get_api_key():
    """Get Gemini API key from Environment first, falling back to Secret Manager."""
    env_vars = ("GEMINI_IMAGE_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")

    for env_var in env_vars:
        key = clean_api_key(os.environ.get(env_var))
        if key:
            return key, f"env:{env_var}"

    # Fall back to Secret Manager.
    try:
        secretmanager_module = get_secretmanager_module()
        client = secretmanager_module.SecretManagerServiceClient()
        secret_resource = f"projects/{API_KEY_SECRET_PROJECT}/secrets/{API_KEY_SECRET_NAME}/versions/latest"
        response = client.access_secret_version(request={"name": secret_resource})
        key = clean_api_key(response.payload.data.decode("UTF-8"))
        if key:
            return key, f"secret_manager:{API_KEY_SECRET_PROJECT}/{API_KEY_SECRET_NAME}"
        print("⚠️  Secret Manager returned an empty API key after normalization.")
    except Exception as e:
        print(f"⚠️  Secret Manager unavailable and no env vars found: {e}")

    print("❌ Could not get API key from Secret Manager or env vars.")
    print("   Set GEMINI_IMAGE_API_KEY (preferred), GEMINI_API_KEY, or GOOGLE_API_KEY.")
    print("   You can override secret location with --api-key-secret-name and --api-key-secret-project")
    sys.exit(1)


def get_missing_images():
    """Fetch all missing images from Firestore"""
    firestore_module = get_firestore_module()
    db = firestore_module.Client(project=PROJECT_ID)
    docs = db.collection("missing_images").where(
        filter=firestore_module.FieldFilter("status", "==", "missing")
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
    """Get set of terms that already have generated images (recursive)."""
    already = set()
    if os.path.exists(OUTPUT_LOCAL_DIR):
        for root, _, files in os.walk(OUTPUT_LOCAL_DIR):
            for f in files:
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    already.add(os.path.splitext(f)[0])
    return already


def image_exists_for_safe_name(safe_name):
    """Return True if an image exists for the given safe filename base in output tree."""
    exts = (".png", ".jpg", ".jpeg")
    if not os.path.exists(OUTPUT_LOCAL_DIR):
        return False

    for root, _, files in os.walk(OUTPUT_LOCAL_DIR):
        for f in files:
            if not f.lower().endswith(exts):
                continue
            if os.path.splitext(f)[0] == safe_name:
                return True
    return False


def generate_single_image(client, term):
    """Generate a single image using generate_content (free tier)"""
    _, types_module = get_genai_modules()
    prompt = PROMPT_TEMPLATE.format(term=term)
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types_module.GenerateContentConfig(
            # Explicitly request image output.
            response_modalities=["IMAGE"],
            temperature=1.0,
            top_p=0.95,
            top_k=40,
            safety_settings=[
                types_module.SafetySetting(
                    category=types_module.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types_module.HarmBlockThreshold.BLOCK_NONE,
                ),
                types_module.SafetySetting(
                    category=types_module.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types_module.HarmBlockThreshold.BLOCK_NONE,
                ),
                types_module.SafetySetting(
                    category=types_module.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types_module.HarmBlockThreshold.BLOCK_NONE,
                ),
                types_module.SafetySetting(
                    category=types_module.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types_module.HarmBlockThreshold.BLOCK_NONE,
                ),
            ],
        ),
    )

    if not response:
        return None, "No response returned"

    parts = []

    if getattr(response, "parts", None):
        parts.extend(response.parts)

    if getattr(response, "candidates", None):
        first_candidate = response.candidates[0]
        candidate_content = getattr(first_candidate, "content", None)
        if candidate_content and getattr(candidate_content, "parts", None):
            parts.extend(candidate_content.parts)

    if not parts:
        return None, "No image/text parts in response"

    for part in parts:
        if hasattr(part, 'inline_data') and part.inline_data:
            return part.inline_data, None
        if hasattr(part, 'blob') and part.blob:
            return part.blob, None

    return None, "Model returned no image data (check safety filters or prompt)"


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


def load_daily_state():
    """Load per-day generation counts."""
    if os.path.exists(DAILY_STATE_FILE):
        with open(DAILY_STATE_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    return {}


def save_daily_state(daily_state):
    """Persist per-day generation counts."""
    with open(DAILY_STATE_FILE, "w") as f:
        json.dump(daily_state, f, indent=2)


def get_today_key():
    return datetime.now().strftime("%Y-%m-%d")


def migrate_today_count_from_state_if_needed(daily_state):
    """Best-effort one-time migration from legacy STATE_FILE into daily counter."""
    today = get_today_key()
    if str(today) in daily_state:
        return daily_state

    state = load_state()
    if not state:
        return daily_state

    generated_at = state.get("generated_at")
    terms = state.get("terms", [])
    if not generated_at or not isinstance(terms, list):
        return daily_state

    try:
        generated_date = datetime.fromisoformat(generated_at).strftime("%Y-%m-%d")
        if generated_date == today:
            daily_state[today] = max(0, len(terms))
    except Exception:
        pass

    return daily_state


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
    
    print(f"\n💰 Cost: Potentially PAID (depends on model/tier/project billing)")


def generate_flow(limit=None, resume=False, daily_limit=DEFAULT_DAILY_LIMIT):
    """Generate images one by one with rate limiting"""
    print("🎨 Starting FREE TIER image generation...\n")
    print(f"⚠️  Billing note: {MODEL_ID} may incur paid image-generation charges on billed projects.\n")
    
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
    
    # 3. Enforce per-day generation limit
    daily_state = load_daily_state()
    daily_state = migrate_today_count_from_state_if_needed(daily_state)
    today = get_today_key()
    generated_today = int(daily_state.get(today, 0))
    remaining_today = max(0, daily_limit - generated_today)

    print(f"  Daily quota: {generated_today}/{daily_limit} used today ({remaining_today} remaining)")
    if remaining_today <= 0:
        print("✅ Daily limit reached. Nothing to generate right now.")
        return

    # 4. Apply request limit + daily remaining
    effective_limit = min(len(missing_images), remaining_today)
    if limit is not None:
        effective_limit = min(effective_limit, max(0, int(limit)))

    if effective_limit <= 0:
        print("✅ Effective limit is 0 after applying constraints.")
        return

    if effective_limit < len(missing_images):
        print(f"  Limiting to {effective_limit} images (of {len(missing_images)} remaining)\n")
        missing_images = missing_images[:effective_limit]
    
    # 5. Initialize client
    api_key, key_source = get_api_key()
    print(f"🔐 API key source: {key_source}")
    genai_module, _ = get_genai_modules()
    client = genai_module.Client(api_key=api_key)
    os.makedirs(OUTPUT_LOCAL_DIR, exist_ok=True)
    
    # 6. Generate loop
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
        if image_exists_for_safe_name(safe_name):
            print(f"  [{i+1}/{total}] ⏭️  {term} (already exists)")
            skip_count += 1
            generated_terms.append(term)
            generated_doc_ids.append(img["doc_id"])
            continue
        
        # Generate with retry
        success = False
        failure_recorded = False
        quota_exhausted = False
        for attempt in range(MAX_RETRIES):
            try:
                image_data, error = generate_single_image(client, term)
                
                if error:
                    print(f"  [{i+1}/{total}] ⚠️  {term}: {error}")
                    fail_count += 1
                    failure_recorded = True
                    break  # Don't retry on "no image data" - model issue
                
                filepath, size = save_image(image_data, term)
                elapsed = time.time() - start_time
                rate = (success_count + 1) / (elapsed / 60) if elapsed > 0 else 0
                
                print(f"  [{i+1}/{total}] ✅ {term} ({size:,} bytes) [{rate:.1f} img/min]")
                success_count += 1
                generated_terms.append(term)
                generated_doc_ids.append(img["doc_id"])
                daily_state[today] = int(daily_state.get(today, 0)) + 1
                save_daily_state(daily_state)
                success = True
                break
                
            except Exception as e:
                error_str = str(e).lower()

                if "does not support the requested response modalities" in error_str:
                    print(f"  [{i+1}/{total}] ❌ {term}: Model/modality mismatch: {e}")
                    print("     This model cannot generate images with response_modalities=['IMAGE'].")
                    fail_count += 1
                    failure_recorded = True
                    quota_exhausted = True
                    break
                
                if "429" in str(e) or "rate" in error_str or "quota" in error_str or "resource_exhausted" in error_str:
                    # "limit: 0" means the API key is from a billing-enabled project with no free-tier quota
                    hard_quota_zero = "limit: 0" in str(e) or ", limit: 0," in str(e)
                    quota_likely_exhausted = hard_quota_zero or any(
                        marker in error_str
                        for marker in ["resource_exhausted", "quota", "daily", "per day", "exceeded"]
                    )

                    if FAIL_FAST_ON_QUOTA_EXHAUSTED and quota_likely_exhausted:
                        print(f"  [{i+1}/{total}] ❌ {term}: Quota exhausted — stopping all generation")
                        if hard_quota_zero:
                            print(f"\n  ⚠️  DIAGNOSIS: Active API key source '{key_source}' returned free-tier limit: 0.")
                            print(f"     This key/project currently has no usable free-tier quota entitlement")
                            print(f"     for this model (or account/region).")
                            print(f"     → Verify in AI Studio rate limits: https://ai.dev/rate-limit")
                            print(f"     → Try a different AI Studio key/project/account to confirm eligibility.")
                        else:
                            print(f"     Details: {e}")
                        fail_count += 1
                        failure_recorded = True
                        quota_exhausted = True
                        break

                    wait = RETRY_DELAY * (attempt + 1)
                    if attempt < MAX_RETRIES - 1:
                        print(f"  [{i+1}/{total}] ⏳ {term}: Rate limited (attempt {attempt+1}/{MAX_RETRIES}). Waiting {wait}s...")
                        time.sleep(wait)
                    else:
                        print(f"  [{i+1}/{total}] ❌ {term}: Rate limited after {MAX_RETRIES} attempts")
                        print(f"     Details: {e}")
                        fail_count += 1
                        failure_recorded = True
                elif attempt < MAX_RETRIES - 1:
                    print(f"  [{i+1}/{total}] ⚠️  {term}: Error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
                    time.sleep(10)
                else:
                    print(f"  [{i+1}/{total}] ❌ {term}: Failed after {MAX_RETRIES} attempts: {e}")
                    fail_count += 1
                    failure_recorded = True

        if not success and not failure_recorded:
            fail_count += 1

        if quota_exhausted:
            print(f"\n  Remaining {total - i - 1} items skipped due to quota exhaustion.")
            fail_count += total - i - 1
            break
        
        # Rate limit cooldown (skip if we already slept due to an error/retry)
        if i < total - 1:  # Don't sleep after the last one
            time.sleep(COOLDOWN_SECONDS)
    
    # 7. Save state for finalize step
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
    print(f"  💰 Cost:    Potentially PAID (depends on model/tier/project billing)")
    
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
    downloaded = get_already_generated()
    
    firestore_module = get_firestore_module()
    db = firestore_module.Client(project=PROJECT_ID)
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
    global REQUESTS_PER_MINUTE, COOLDOWN_SECONDS, FAIL_FAST_ON_QUOTA_EXHAUSTED
    global API_KEY_SECRET_NAME, API_KEY_SECRET_PROJECT

    ensure_ssl_ca_bundle()
    
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
    parser.add_argument(
        "--daily-limit",
        type=int,
        default=DEFAULT_DAILY_LIMIT,
        help=f"Max successful generations per calendar day (default: {DEFAULT_DAILY_LIMIT})",
    )
    parser.add_argument("--rpm", type=int, default=REQUESTS_PER_MINUTE, help=f"Requests per minute (default: {REQUESTS_PER_MINUTE})")
    parser.add_argument(
        "--retry-rate-limits",
        action="store_true",
        help="Retry on 429/resource exhausted (default: fail fast to avoid long waits)",
    )
    parser.add_argument(
        "--api-key-secret-name",
        type=str,
        default=API_KEY_SECRET_NAME,
        help=f"Secret Manager secret name for Gemini API key (default: {API_KEY_SECRET_NAME})",
    )
    parser.add_argument(
        "--api-key-secret-project",
        type=str,
        default=API_KEY_SECRET_PROJECT,
        help=f"Project containing API key secret (default: {API_KEY_SECRET_PROJECT})",
    )
    
    args = parser.parse_args()
    
    # Allow RPM override
    if args.rpm != REQUESTS_PER_MINUTE:
        REQUESTS_PER_MINUTE = max(1, min(10, args.rpm))
        COOLDOWN_SECONDS = 60 / REQUESTS_PER_MINUTE
        print(f"⚙️  RPM override: {REQUESTS_PER_MINUTE} ({COOLDOWN_SECONDS:.1f}s cooldown)\n")

    FAIL_FAST_ON_QUOTA_EXHAUSTED = not args.retry_rate_limits

    API_KEY_SECRET_NAME = args.api_key_secret_name
    API_KEY_SECRET_PROJECT = args.api_key_secret_project
    
    if args.dry_run:
        dry_run()
    elif args.generate:
        generate_flow(limit=args.limit, resume=args.resume, daily_limit=max(1, args.daily_limit))
    elif args.finalize:
        finalize()


if __name__ == "__main__":
    main()
