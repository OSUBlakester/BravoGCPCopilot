#!/usr/bin/env python3
"""
Batch Generate Missing Images using Google AI Studio (Gemini Batch API)

This script:
1. Reads the missing_images collection from Firestore (status='missing')
2. Submits an inline batch job to the Gemini API (google-genai SDK)
3. Polls for completion, then downloads and saves PNGs locally
4. Moves processed entries from missing_images to processed_images

Uses the Google AI Studio free tier / Gemini API with 50% batch discount.

Usage:
    # Step 1: Dry run - see what would be generated
    python batch_generate_missing_images.py --dry-run

    # Step 2: Submit the batch job
    python batch_generate_missing_images.py --submit

    # Step 3: Check job status
    python batch_generate_missing_images.py --status

    # Step 4: Download results when job is complete
    python batch_generate_missing_images.py --download
    
    # Step 5: Move processed entries from missing_images to processed_images
    python batch_generate_missing_images.py --finalize
"""

import os
import sys
import json
import argparse
import base64
import re
from datetime import datetime
from pathlib import Path

from google.cloud import firestore, secretmanager
try:
    from google import genai
    from google.genai import types
except ImportError as e:
    print("❌ Could not import the Google GenAI SDK.")
    print(f"   Error: {e}")
    print("   This script must be run with the project virtual environment.")
    print("   Use: ./runbatch --submit --limit 20 --allow-batch-billing")
    sys.exit(1)

# --- CONFIGURATION ---
PROJECT_ID = "bravo-prod-465323"
MODEL_ID = "models/gemini-2.5-flash-image"  # Nano Banana - Gemini 2.5 Flash with image generation
OUTPUT_LOCAL_DIR = os.path.join(os.path.dirname(__file__), "BravoImages", "batch_missing_images")
STATE_FILE = os.path.join(os.path.dirname(__file__), ".batch_job_state.json")
BATCH_DISABLED_BY_DEFAULT = True
KNOWN_GOOD_CA_BUNDLE = "/Library/Frameworks/Python.framework/Versions/3.12/etc/openssl/cert.pem"
DEFAULT_BATCH_IMAGE_PRICE = 0.039
ESTIMATED_BATCH_DISCOUNT = 0.50

# Image generation prompt template
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
    """Get Gemini API key from bravo-prod Secret Manager first, env fallback second."""
    # Prefer the bravo-prod secret explicitly for billed batch runs.
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_name = f"projects/{PROJECT_ID}/secrets/bravo-google-api-key/versions/latest"
        response = client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8"), f"secret_manager:{PROJECT_ID}/bravo-google-api-key"
    except Exception as e:
        print(f"⚠️  Secret Manager unavailable, trying environment fallback: {e}")

    for env_var in ('GEMINI_API_KEY', 'GOOGLE_API_KEY'):
        api_key = os.environ.get(env_var)
        if api_key:
            return api_key, f"env:{env_var}"

    print("❌ Could not get bravo-prod batch API key.")
    print("   Expected Secret Manager secret: projects/bravo-prod-465323/secrets/bravo-google-api-key")
    print("   Fallback env vars checked: GEMINI_API_KEY, GOOGLE_API_KEY")
    sys.exit(1)


def ensure_ssl_ca_bundle():
    """Work around broken venv certifi bundle on macOS Python.org installs."""
    if os.environ.get("SSL_CERT_FILE") and os.environ.get("REQUESTS_CA_BUNDLE"):
        return

    if os.path.exists(KNOWN_GOOD_CA_BUNDLE):
        os.environ.setdefault("SSL_CERT_FILE", KNOWN_GOOD_CA_BUNDLE)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", KNOWN_GOOD_CA_BUNDLE)
        print(f"🔒 Using CA bundle: {KNOWN_GOOD_CA_BUNDLE}")


def estimate_batch_cost(image_count):
    """Estimate output-image cost assuming 50% batch discount."""
    standard_cost = image_count * DEFAULT_BATCH_IMAGE_PRICE
    batch_cost = standard_cost * ESTIMATED_BATCH_DISCOUNT
    return standard_cost, batch_cost


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


def build_batch_requests(missing_images):
    """Build inline batch requests for the Gemini API"""
    requests = []
    for img in missing_images:
        term = img["search_term"]
        prompt = PROMPT_TEMPLATE.format(term=term)
        
        req = types.CreateCachedContentConfig(
            # This is actually unused - we build raw request dicts
        )
        
        requests.append({
            "term": term,
            "doc_id": img["doc_id"],
            "prompt": prompt,
        })
    
    return requests


def submit_batch_job(missing_images):
    """Submit a batch job using the google-genai SDK"""
    api_key, key_source = get_api_key()
    print(f"  🔐 API key source: {key_source}")
    client = genai.Client(api_key=api_key)
    
    # Build the inline requests list
    inline_requests = []
    for img in missing_images:
        term = img["search_term"]
        prompt = PROMPT_TEMPLATE.format(term=term)
        
        inline_requests.append(
            types.InlinedRequest(
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=prompt)]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    temperature=1.0,
                    top_p=0.95,
                    top_k=40,
                ),
            )
        )
    
    print(f"  Submitting {len(inline_requests)} requests to Gemini Batch API...")
    
    batch_job = client.batches.create(
        model=MODEL_ID,
        src=inline_requests,
        config=types.CreateBatchJobConfig(
            display_name=f"missing_images_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        ),
    )
    
    print(f"  ✅ Batch job created: {batch_job.name}")
    print(f"  📊 State: {batch_job.state}")
    
    # Save job state
    save_state({
        "job_name": batch_job.name,
        "submitted_at": datetime.now().isoformat(),
        "status": "submitted",
        "terms": [img["search_term"] for img in missing_images],
        "doc_ids": [img["doc_id"] for img in missing_images],
        "api": "genai",  # Mark as genai batch (not vertex)
    })
    
    return batch_job


def check_job_status():
    """Check the status of the most recent batch job"""
    state = load_state()
    if not state:
        print("❌ No batch job found. Run with --submit first.")
        return None
    
    api_key, key_source = get_api_key()
    print(f"🔐 API key source: {key_source}")
    client = genai.Client(api_key=api_key)
    
    job_name = state["job_name"]
    print(f"🔍 Checking job: {job_name}")
    
    job = client.batches.get(name=job_name)
    
    print(f"  State: {job.state}")
    print(f"  Submitted: {state.get('submitted_at', 'unknown')}")
    
    if hasattr(job, 'stats') and job.stats:
        print(f"  Total: {job.stats.total_count}")
        print(f"  Succeeded: {job.stats.success_count}")
        print(f"  Failed: {job.stats.failed_count}")
    
    state_str = str(job.state).upper()
    if "SUCCEEDED" in state_str or "JOB_STATE_SUCCEEDED" in state_str:
        print("  ✅ Job completed! Run with --download to get results.")
        state["status"] = "completed"
        save_state(state)
    elif "FAILED" in state_str:
        print("  ❌ Job failed!")
        state["status"] = "failed"
        save_state(state)
    elif "CANCELLED" in state_str:
        print("  🚫 Job was cancelled.")
        state["status"] = "cancelled"
        save_state(state)
    else:
        print("  ⏳ Job still running. Check again later.")
    
    return job


def download_results():
    """Download batch results and save as PNG files locally"""
    state = load_state()
    if not state:
        print("❌ No batch job found. Run with --submit first.")
        return
    
    api_key, key_source = get_api_key()
    print(f"🔐 API key source: {key_source}")
    client = genai.Client(api_key=api_key)
    
    job_name = state["job_name"]
    job = client.batches.get(name=job_name)
    
    state_str = str(job.state).upper()
    if "SUCCEEDED" not in state_str and "JOB_STATE_SUCCEEDED" not in state_str:
        print(f"❌ Job is not complete yet. State: {job.state}")
        print("   Run --status to check progress.")
        return
    
    # Create output directory
    os.makedirs(OUTPUT_LOCAL_DIR, exist_ok=True)
    
    saved_count = 0
    failed_count = 0
    
    print(f"📥 Downloading results from batch job...")
    
    # Get the saved terms list - responses may NOT be in the same order as requests
    terms = state.get("terms", [])
    
    # Build lookups: normalize each term for matching against response text
    terms_lower = {t.lower(): t for t in terms}
    # Also build a stripped lookup (no hyphens/spaces) for fuzzy matching
    # e.g. "middleaged" matches "middle-aged", "ecommerce" matches "e-commerce"
    def strip_term(s):
        return re.sub(r'[\s\-_]', '', s.lower())
    terms_stripped = {strip_term(t): t for t in terms}
    used_terms = set()  # Track which terms have been matched to avoid duplicates
    
    # Results are in job.dest.inlined_responses (order may be SHUFFLED vs requests)
    responses = job.dest.inlined_responses if job.dest and job.dest.inlined_responses else []
    
    if not responses:
        print("❌ No results found in batch job.")
        return
    
    print(f"  Found {len(responses)} results\n")
    
    for idx, inlined_resp in enumerate(responses):
        try:
            resp = inlined_resp.response
            if not resp or not resp.candidates:
                print(f"  ⚠️ Result {idx}: No candidates in response")
                failed_count += 1
                continue
            
            # Find image data AND collect all response text
            image_data = None
            response_text = ""
            for candidate in resp.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                            image_data = part.inline_data
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text + " "
            
            # Extract the term from the model's response text by matching against known terms
            # Strategy: try [TERM:x] tag first, then quoted terms, then fuzzy match, then longest substring
            term = None
            
            if response_text.strip():
                resp_lower = response_text.lower()
                
                # 0. Try [TERM:xxx] tag (most reliable, from updated prompt)
                tag_match = re.search(r'\[TERM:([^\]]+)\]', response_text, re.IGNORECASE)
                if tag_match:
                    tag_val = tag_match.group(1).strip()
                    tag_lower = tag_val.lower()
                    if tag_lower in terms_lower and tag_lower not in used_terms:
                        term = terms_lower[tag_lower]
                    else:
                        tag_stripped = strip_term(tag_val)
                        if tag_stripped in terms_stripped and terms_stripped[tag_stripped].lower() not in used_terms:
                            term = terms_stripped[tag_stripped]
                
                # 1. Try quoted term patterns: 'term', "term"
                quoted_matches = re.findall(r"""['"\\"]([^'"\\\"]+)['"\\"]""", response_text)
                for qm in quoted_matches:
                    qm_lower = qm.lower().strip()
                    # Direct match
                    if qm_lower in terms_lower and qm_lower not in used_terms:
                        term = terms_lower[qm_lower]
                        break
                    # Stripped match (handles hyphens: "middle-aged" -> "middleaged")
                    qm_stripped = strip_term(qm)
                    if qm_stripped in terms_stripped and terms_stripped[qm_stripped].lower() not in used_terms:
                        term = terms_stripped[qm_stripped]
                        break
                
                # 2. If no quoted match, search for known terms in the text (longest match first)
                if not term:
                    best_match = None
                    best_len = 0
                    for t_lower, t_orig in terms_lower.items():
                        if t_lower not in used_terms:
                            # Use word boundary for short terms to avoid partial matches
                            # e.g. "AI" matching inside "wait"
                            if len(t_lower) <= 3:
                                pattern = r'\b' + re.escape(t_lower) + r'\b'
                                if re.search(pattern, resp_lower):
                                    if len(t_lower) > best_len:
                                        best_match = t_orig
                                        best_len = len(t_lower)
                            elif t_lower in resp_lower:
                                if len(t_lower) > best_len:
                                    best_match = t_orig
                                    best_len = len(t_lower)
                    if best_match:
                        term = best_match
            
            if not term:
                term = f"unknown_{idx}"
                print(f"  ⚠️ Result {idx}: Could not identify term from response text: {response_text[:100]}")
            
            used_terms.add(term.lower())
            
            if not image_data:
                print(f"  ⚠️ {term}: No image data in response (finish_reason may be OTHER)")
                failed_count += 1
                continue
            
            # Save the image
            mime_type = getattr(image_data, 'mime_type', 'image/png')
            ext = "png" if "png" in str(mime_type) else "jpg"
            raw_bytes = image_data.data
            
            # If data is base64 encoded string, decode it
            if isinstance(raw_bytes, str):
                raw_bytes = base64.b64decode(raw_bytes)
            
            safe_name = re.sub(r'[^\w\s-]', '', term.lower()).strip().replace(' ', '_')
            filename = f"{safe_name}.{ext}"
            filepath = os.path.join(OUTPUT_LOCAL_DIR, filename)
            
            with open(filepath, "wb") as f:
                f.write(raw_bytes)
            
            print(f"  ✅ Saved: {filename} ({len(raw_bytes)} bytes)")
            saved_count += 1
            
        except Exception as e:
            print(f"  ❌ {term}: Error - {e}")
            failed_count += 1
    
    # Second pass: identify unknown images using AI vision
    unknown_files = [f for f in os.listdir(OUTPUT_LOCAL_DIR) if f.startswith("unknown_")]
    remaining_terms = [t for t in terms if t.lower() not in used_terms]
    
    if unknown_files and remaining_terms:
        print(f"\n🔍 AI Identification Pass: {len(unknown_files)} unknowns, {len(remaining_terms)} remaining terms")
        
        try:
            remaining_lower = {t.lower(): t for t in remaining_terms}
            remaining_stripped = {strip_term(t): t for t in remaining_terms}
            identified = 0
            
            for uf in unknown_files:
                filepath = os.path.join(OUTPUT_LOCAL_DIR, uf)
                try:
                    with open(filepath, "rb") as f:
                        img_bytes = f.read()
                    
                    # Ask Gemini to identify what the image depicts
                    terms_list = ", ".join(remaining_terms[:50])  # Limit context size
                    identify_resp = client.models.generate_content(
                        model=MODEL_ID.replace("-image", ""),  # Use non-image model for text
                        contents=[
                            types.Content(parts=[
                                types.Part(text=f"This image is an AAC (communication) icon. Which ONE of these terms does it represent? Reply with ONLY the term, nothing else. Terms: {terms_list}"),
                                types.Part(inline_data=types.Blob(mime_type="image/png", data=img_bytes)),
                            ])
                        ],
                    )
                    
                    if identify_resp and identify_resp.text:
                        guess = identify_resp.text.strip().lower()
                        matched_term = None
                        
                        # Try exact match
                        if guess in remaining_lower:
                            matched_term = remaining_lower[guess]
                        else:
                            # Try stripped match
                            guess_stripped = strip_term(guess)
                            if guess_stripped in remaining_stripped:
                                matched_term = remaining_stripped[guess_stripped]
                            else:
                                # Try substring match against remaining terms
                                for rt_lower, rt_orig in remaining_lower.items():
                                    if rt_lower in guess or guess in rt_lower:
                                        matched_term = rt_orig
                                        break
                        
                        if matched_term and matched_term.lower() not in used_terms:
                            safe_name = re.sub(r'[^\w\s-]', '', matched_term.lower()).strip().replace(' ', '_')
                            new_filename = f"{safe_name}.png"
                            new_filepath = os.path.join(OUTPUT_LOCAL_DIR, new_filename)
                            os.rename(filepath, new_filepath)
                            used_terms.add(matched_term.lower())
                            remaining_lower.pop(matched_term.lower(), None)
                            remaining_stripped.pop(strip_term(matched_term), None)
                            print(f"  🔍 {uf} → {new_filename} (AI identified)")
                            identified += 1
                        else:
                            print(f"  ❓ {uf}: AI guessed '{guess}' - no match in remaining terms")
                    
                    import time
                    time.sleep(0.5)  # Rate limit
                    
                except Exception as e:
                    print(f"  ❌ {uf}: AI identification error - {e}")
            
            print(f"  AI identified: {identified}/{len(unknown_files)}")
            saved_count += identified  # Update count since unknowns were already saved
            
        except Exception as e:
            print(f"  ❌ AI identification pass failed: {e}")
    
    print(f"\n📊 Download Summary:")
    print(f"  Saved: {saved_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Output: {OUTPUT_LOCAL_DIR}")
    
    if saved_count > 0:
        print(f"\n💡 Next step: Run process_and_upload_images.py to process and upload to GCS/Firestore")
        
        # Auto-finalize: move processed entries from missing_images to processed_images
        print(f"\n🔄 Auto-finalizing: moving {saved_count} entries from missing_images to processed_images...")
        finalize()


def save_state(state):
    """Save batch job state to a local file"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_state():
    """Load batch job state from local file"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return None


def dry_run():
    """Show what would be generated without actually submitting"""
    print("🔍 Dry Run - Fetching missing images from Firestore...")
    missing_images = get_missing_images()
    
    if not missing_images:
        print("✅ No missing images found!")
        return
    
    print(f"\n📋 Found {len(missing_images)} missing images:\n")
    print(f"{'#':<4} {'Search Term':<30} {'Doc ID':<30} {'Count':<6}")
    print("-" * 70)
    
    for i, img in enumerate(missing_images, 1):
        print(f"{i:<4} {img['search_term']:<30} {img['doc_id']:<30} {img['search_count']:<6}")
    
    print(f"\n📝 Sample prompt for '{missing_images[0]['search_term']}':")
    print(f"   {PROMPT_TEMPLATE.format(term=missing_images[0]['search_term'])}")
    
    standard_cost, batch_cost = estimate_batch_cost(len(missing_images))
    print(f"\n📦 Would submit {len(missing_images)} inline requests via Gemini Batch API")
    print(f"📂 Images would be saved to: {OUTPUT_LOCAL_DIR}")
    print(f"🤖 Model: {MODEL_ID}")
    print(f"💰 Estimated standard image-output cost: ~${standard_cost:.2f}")
    print(f"💰 Estimated batch image-output cost:    ~${batch_cost:.2f} (assuming 50% batch discount)")


def submit_flow(limit=None):
    """Full submit flow: fetch missing images, submit batch"""
    print("🚀 Starting batch image generation (Google AI Studio)...\n")
    
    # 1. Fetch missing images
    print("Step 1: Fetching missing images from Firestore...")
    missing_images = get_missing_images()
    
    if not missing_images:
        print("✅ No missing images found! Nothing to generate.")
        return

    if limit is not None:
        limit = max(0, int(limit))
        if limit == 0:
            print("✅ Limit is 0. Nothing to submit.")
            return
        if limit < len(missing_images):
            missing_images = missing_images[:limit]
            print(f"  Limiting to {len(missing_images)} missing images for this test\n")
    
    print(f"  Found {len(missing_images)} missing images\n")

    standard_cost, batch_cost = estimate_batch_cost(len(missing_images))
    print(f"  Estimated standard image-output cost: ~${standard_cost:.2f}")
    print(f"  Estimated batch image-output cost:    ~${batch_cost:.2f} (assuming 50% batch discount)\n")
    
    # 2. Submit batch job
    print("Step 2: Submitting to Gemini Batch API...")
    batch_job = submit_batch_job(missing_images)
    
    print(f"\n✅ Batch job submitted! Use --status to check progress.")
    print(f"   Once complete, use --download to save images locally.")


def finalize():
    """Move processed entries from missing_images to processed_images in Firestore"""
    state = load_state()
    if not state:
        print("❌ No batch job found. Run with --submit first.")
        return
    
    doc_ids = state.get("doc_ids", [])
    if not doc_ids:
        print("❌ No doc_ids found in state. Was --submit run properly?")
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
            # Read from missing_images
            doc = missing_ref.document(doc_id).get()
            if not doc.exists:
                print(f"  ⚠️  {doc_id}: Not found in missing_images (already moved?)")
                skipped_count += 1
                continue
            
            data = doc.to_dict()
            
            # Check if we have a downloaded image for this term
            safe_name = re.sub(r'[^\w\s-]', '', (data.get('search_term', doc_id)).lower()).strip().replace(' ', '_')
            has_image = safe_name in downloaded
            
            # Add processing metadata
            data["processed_at"] = datetime.now()
            data["batch_job"] = state.get("job_name", "unknown")
            data["image_generated"] = has_image
            if has_image:
                data["local_image_path"] = os.path.join(OUTPUT_LOCAL_DIR, f"{safe_name}.png")
            data["previous_status"] = data.get("status", "missing")
            data["status"] = "processed"
            
            # Write to processed_images
            processed_ref.document(doc_id).set(data)
            
            # Delete from missing_images
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
    ensure_ssl_ca_bundle()

    parser = argparse.ArgumentParser(description="Batch generate missing images using Google AI Studio (Gemini Batch API)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    group.add_argument("--submit", action="store_true", help="Submit the batch job")
    group.add_argument("--status", action="store_true", help="Check batch job status")
    group.add_argument("--download", action="store_true", help="Download completed results")
    group.add_argument("--finalize", action="store_true", help="Move processed entries to processed_images collection")
    parser.add_argument(
        "--allow-batch-billing",
        action="store_true",
        help="Required for non-dry-run batch actions because batch usage is billable",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit batch submission to the first N missing images for testing",
    )
    
    args = parser.parse_args()

    if BATCH_DISABLED_BY_DEFAULT and not args.dry_run and not args.allow_batch_billing:
        print("❌ Batch operations are disabled by default to prevent accidental billing.")
        print("   Re-run with --allow-batch-billing to proceed intentionally.")
        print("   Recommended: use generate_missing_images_free.py for non-batch generation.")
        sys.exit(1)
    
    if args.dry_run:
        dry_run()
    elif args.submit:
        submit_flow(limit=args.limit)
    elif args.status:
        check_job_status()
    elif args.download:
        download_results()
    elif args.finalize:
        finalize()


if __name__ == "__main__":
    main()
