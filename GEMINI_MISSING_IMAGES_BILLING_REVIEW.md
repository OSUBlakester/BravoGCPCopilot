# Gemini Review Packet: Missing Images Billing Investigation

## Goal
Identify why our "free-tier" missing-image workflow is still incurring charges, and recommend specific code/config changes.

## Executive Summary
- `backfill_missing_images.py` is **not** the image-generation step.
- It calls `/api/missing-images/scan`, which scans terms and logs missing entries in Firestore.
- Billable AI usage is most likely in:
  1. `generate_missing_images_free.py` (image generation calls)
  2. `batch_generate_missing_images.py` (batch API calls)
  3. `bulk_import_bravo_images.py` (Gemini tagging calls)

## Copy/Paste Prompt for Gemini
Please review this codebase flow and identify why we are still getting billed for image generation.

### Context
We maintain a Firestore collection `missing_images` in production (`bravo-prod-465323`).

#### Scan/log step (not generation)
- `backfill_missing_images.py` calls our endpoint `/api/missing-images/scan`.
- In server code, missing terms are logged when search returns no image.

#### Generation step
- `generate_missing_images_free.py` reads `missing_images` docs with `status == "missing"`.
- It calls `client.models.generate_content()` using model `models/gemini-2.5-flash-image`.
- It gets API key from env var or Secret Manager secret `bravo-google-api-key` in project `bravo-prod-465323`.

#### Alternate batch path
- `batch_generate_missing_images.py` submits Gemini batch jobs via `client.batches.create(...)`.

#### Post-generation import/tagging
- `bulk_import_bravo_images.py` uploads images, then calls Gemini again to generate tags.

### Questions to answer
1. Is `models/gemini-2.5-flash-image` billable via `generate_content()` even outside batch?
2. Does using a production key/secret explain why our "free" script still incurs charges?
3. Is the batch path definitely billable in this setup?
4. Could Gemini tagging in import also be contributing materially to charges?
5. What exact code/config changes should we make to minimize/avoid billing while keeping functionality?

### Requested output format
- Root-cause assessment
- Recommended low-cost workflow
- Exact code-level changes (by file/function)
- Validation checklist (how to prove billing dropped)

## Files to Share with Gemini

### Required (core)
1. `generate_missing_images_free.py`
   - Main image-generation loop labeled "free-tier"
   - Uses production project + secret key + `gemini-2.5-flash-image`

2. `batch_generate_missing_images.py`
   - Alternate generation path using Gemini Batch API

3. `bulk_import_bravo_images.py`
   - Post-generation import step with additional Gemini calls for tagging

4. `backfill_missing_images.py`
   - Shows scanner behavior (calls server endpoint only)

5. `server.py` (selected sections only)
   - `log_missing_image(...)`
   - `/api/missing-images/scan`
   - search path where missing terms are logged when no image is found

### Nice-to-have (supporting)
6. Any runbook/README you actually use for this pipeline (if present)
7. Example billing screenshots (Gemini API SKU labels/timestamps)
8. Example command history showing which script was run when charges occurred

## Suggested Minimal Snippets from server.py
Share only these sections (not whole file):
- Missing-term logger function (`log_missing_image`)
- Endpoint `POST /api/missing-images/scan`
- The conditional branch that logs missing terms when zero symbols found

## Why this packet matters
It separates:
- **term discovery/logging** (scan) vs
- **AI generation/tagging** (likely billable)

This helps Gemini focus on actual billing paths and avoid false positives.
