#!/usr/bin/env python3
"""
Generate static_image_assignments.py from the Firestore aac_images collection.

Connects directly to Firestore using your local Application Default Credentials
(the same ones the dev Docker container uses via ~/.config/gcloud/).

Usage:
    python generate_image_assignments.py
    python generate_image_assignments.py --mascots bobby bonnie buddy
    python generate_image_assignments.py --project bravo-dev-465400

Outputs: static_image_assignments.py  (commit this file to the repo)
"""
import argparse
import asyncio
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Set

# ---------------------------------------------------------------------------
# CLI args
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Generate static image assignments")
parser.add_argument(
    "--project", default="bravo-dev-465400",
    help="GCP project ID (default: bravo-dev-465400)"
)
parser.add_argument(
    "--mascots", nargs="*",
    help="Mascot names to process (default: discover from Firestore)"
)
parser.add_argument(
    "--output", default="static_image_assignments.py",
    help="Output file path (default: static_image_assignments.py)"
)
args = parser.parse_args()

PROJECT_ID = args.project
BUCKET_NAME = f"{PROJECT_ID}-aac-images"
GCS_BASE = f"https://storage.googleapis.com/{BUCKET_NAME}/"

# ---------------------------------------------------------------------------
# Firestore setup via Application Default Credentials
# ---------------------------------------------------------------------------
try:
    import firebase_admin
    from firebase_admin import credentials, firestore as fb_firestore
except ImportError:
    sys.exit("ERROR: firebase-admin not installed. Run: pip install firebase-admin")

try:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {"projectId": PROJECT_ID})
    db = fb_firestore.client()
    print(f"Connected to Firestore project: {PROJECT_ID}")
except Exception as e:
    sys.exit(
        f"ERROR: Could not connect to Firestore.\n{e}\n\n"
        "Make sure you're authenticated:\n"
        "  gcloud auth application-default login"
    )

# ---------------------------------------------------------------------------
# Load pool labels
# ---------------------------------------------------------------------------
try:
    from scratch_pools import CATEGORY_STATIC_POOLS
except ImportError:
    sys.exit("ERROR: scratch_pools.py not found. Run from the project root directory.")

all_pool_labels: List[str] = []
for words in CATEGORY_STATIC_POOLS.values():
    all_pool_labels.extend(str(w).strip() for w in words if str(w).strip())
unique_labels: List[str] = list(dict.fromkeys(all_pool_labels))
print(f"Pool labels: {len(unique_labels)} unique across {len(CATEGORY_STATIC_POOLS)} pools")


# ---------------------------------------------------------------------------
# Normalisation helpers (mirrors _lookup_images_for_labels in server.py)
# ---------------------------------------------------------------------------
def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(s or "").strip().lower()).split())


_LEAD_STOPS = frozenset({
    "a", "an", "the", "and", "or", "but",
    "to", "in", "on", "at", "for", "with", "of", "by", "from", "into", "about",
    "up", "out", "since", "after", "before", "until", "while", "when", "because",
    "like", "than", "though", "as",
    "my", "your", "his", "her", "its", "our", "their", "own",
    "some", "any", "this", "that", "these", "those",
    "i", "we", "you", "he", "she", "they", "it",
    "m", "re", "ve", "ll", "d", "s",
    "am", "is", "are", "was", "were", "be", "been", "being",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
    "have", "has", "had", "do", "does", "did",
    "want", "need", "love", "feel", "get", "let", "try", "feeling",
    "look", "looks", "looked", "looking", "wants", "needs",
    "so", "very", "really", "quite", "pretty", "too",
    "extremely", "super", "totally", "just", "kind", "sort", "easy",
    "there", "doing", "go", "something", "somewhere",
    "what", "how", "then", "towards", "down", "going", "if",
})

def _key_term(norm: str) -> str:
    words = norm.split()
    while len(words) > 1 and words[0] in _LEAD_STOPS:
        if len(words) >= 2 and words[1] == "t":
            break
        words = words[1:]
    return " ".join(words)


def _chunked(seq: list, n: int = 10):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


# ---------------------------------------------------------------------------
# Core image lookup — synchronous, queries aac_images directly
# ---------------------------------------------------------------------------
_ACCEPTED_SOURCES = {"bravo_images", "global"}

def _lookup_images_sync(
    labels: List[str],
    mascot: str,
) -> Dict[str, str]:
    """Return {label: image_url} for every label we can match.

    Runs all Firestore queries concurrently via a thread pool — typically
    completes in 30-90 seconds for ~10K labels instead of 10+ minutes.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    mascot_clean = mascot.strip().lower()
    images_ref = db.collection("aac_images")

    norm_map = {lbl: _norm(lbl) for lbl in labels}
    key_map  = {lbl: _key_term(norm_map[lbl]) for lbl in labels}

    all_norm: Set[str] = set()
    for lbl in labels:
        if norm_map.get(lbl):
            all_norm.add(norm_map[lbl])
        if key_map.get(lbl):
            all_norm.add(key_map[lbl])
    if not all_norm:
        return {}

    norm_list = list(all_norm)

    # Build all queries up front
    all_queries = []
    for chunk in _chunked(norm_list, 10):
        all_queries.extend([
            images_ref.where("source", "==", "bravo_images").where("subconcept", "in", chunk).limit(100),
            images_ref.where("source", "==", "global").where("subconcept", "in", chunk).limit(100),
            images_ref.where("source", "==", "bravo_images").where("concept", "in", chunk).limit(100),
            images_ref.where("source", "==", "global").where("concept", "in", chunk).limit(100),
            images_ref.where("search_terms", "array_contains_any", chunk).limit(300),
            images_ref.where("source", "==", "bravo_images").where("tags", "array_contains_any", chunk).limit(250),
            images_ref.where("source", "==", "global").where("tags", "array_contains_any", chunk).limit(250),
        ])

    print(f"  Running {len(all_queries)} Firestore queries concurrently...")

    candidate_docs: Dict[str, dict] = {}
    lock = threading.Lock()
    completed = [0]

    def _run_query(q):
        try:
            results = list(q.stream())
            with lock:
                completed[0] += 1
                if completed[0] % 100 == 0:
                    pct = completed[0] * 100 // len(all_queries)
                    print(f"  {completed[0]}/{len(all_queries)} queries done ({pct}%)", flush=True)
                for doc in results:
                    data = doc.to_dict() or {}
                    if not data.get("image_url"):
                        continue
                    if data.get("source") not in _ACCEPTED_SOURCES:
                        continue
                    candidate_docs[doc.id] = data
        except Exception as e:
            print(f"  Query error (non-fatal): {e}", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(_run_query, q) for q in all_queries]
        for _ in as_completed(futures):
            pass  # results collected inside _run_query via lock

    print(f"  Queries complete. {len(candidate_docs)} candidate images found.")
    print("  Building inverted index for scoring...")

    # Build inverted indexes keyed by normalised term so scoring is O(matches)
    # instead of O(labels × candidates).
    Entry = Dict  # {url, mascot, source, base_score}

    by_sub:    Dict[str, List[Entry]] = defaultdict(list)
    by_con:    Dict[str, List[Entry]] = defaultdict(list)
    by_sterm:  Dict[str, List[Entry]] = defaultdict(list)
    by_tag:    Dict[str, List[Entry]] = defaultdict(list)

    for data in candidate_docs.values():
        url   = data.get("image_url", "")
        img_m = str(data.get("mascot") or "").strip().lower()
        src   = str(data.get("source") or "").strip().lower()
        if not url:
            continue

        # Mascot/source modifier baked in so per-label scoring is a simple max()
        mod = 0
        if mascot_clean:
            if img_m == mascot_clean:
                mod = +500
            elif img_m and img_m != mascot_clean:
                mod = -500
        if src == "global":
            mod += 10

        entry = {"url": url, "mod": mod}

        sub = _norm(data.get("subconcept") or "")
        con = _norm(data.get("concept")    or "")
        if sub:
            by_sub[sub].append({**entry, "base": 100})
        if con:
            by_con[con].append({**entry, "base": 80})
        for t in (data.get("search_terms") or []):
            nt = _norm(t)
            if nt:
                by_sterm[nt].append({**entry, "base": 50})
        for t in (data.get("tags") or []):
            nt = _norm(t)
            if nt:
                by_tag[nt].append({**entry, "base": 30})

    def _best_for_term(term: str) -> tuple:
        """Return (score, url) for the best candidate matching this term."""
        best_score, best_url = 0, None
        for bucket in (by_sub.get(term, []), by_con.get(term, []),
                       by_sterm.get(term, []), by_tag.get(term, [])):
            for e in bucket:
                s = e["base"] + e["mod"]
                if s > best_score:
                    best_score, best_url = s, e["url"]
        return best_score, best_url

    print(f"  Scoring {len(labels)} labels...")
    label_to_url: Dict[str, str] = {}
    for lbl in labels:
        n  = norm_map.get(lbl, "")
        kt = key_map.get(lbl, "")
        best_score, best_url = 0, None
        for term in ({n, kt} if kt and kt != n else {n}):
            if not term:
                continue
            s, u = _best_for_term(term)
            if s > best_score:
                best_score, best_url = s, u
        if best_url:
            label_to_url[lbl] = best_url

    return label_to_url


# ---------------------------------------------------------------------------
# Discover mascots if not specified
# ---------------------------------------------------------------------------
def discover_mascots() -> List[str]:
    print("Discovering mascots from aac_images...")
    docs = db.collection("aac_images").select(["mascot"]).limit(3000).stream()
    mascot_set = set()
    for d in docs:
        m = str((d.to_dict() or {}).get("mascot") or "").strip().lower()
        if m:
            mascot_set.add(m)
    return sorted(mascot_set)


mascots: List[str] = args.mascots or discover_mascots()
if not mascots:
    sys.exit("No mascots found. Pass --mascots explicitly.")
print(f"Mascots to process: {mascots}")


# ---------------------------------------------------------------------------
# Build assignments per mascot
# ---------------------------------------------------------------------------
all_assignments: Dict[str, Dict[str, str]] = {}
BATCH_SIZE = 30  # labels per progress report

for mascot in mascots:
    print(f"\nProcessing mascot: {mascot!r} ...")
    done = 0
    label_to_url = _lookup_images_sync(unique_labels, mascot)
    done = len(label_to_url)
    print(f"  Resolved {done}/{len(unique_labels)} labels")

    # Convert full URLs → relative paths (strip bucket prefix)
    paths: Dict[str, str] = {}
    for label, url in sorted(label_to_url.items()):
        rel = re.sub(r"^https://storage\.googleapis\.com/[^/]+/", "", url)
        if rel:
            paths[label] = rel

    if paths:
        all_assignments[mascot] = paths
        print(f"  Stored {len(paths)} paths")

if not all_assignments:
    sys.exit("No assignments generated — check Firestore connectivity and mascot names.")


# ---------------------------------------------------------------------------
# Write output file
# ---------------------------------------------------------------------------
lines = [
    "# Auto-generated by generate_image_assignments.py",
    "# DO NOT EDIT MANUALLY — re-run the script when aac_images changes or mascots are added.",
    "#",
    "# Stores GCS-relative paths (no bucket prefix).  The server prepends:",
    "#   https://storage.googleapis.com/{AAC_IMAGES_BUCKET_NAME}/",
    "# so this file works identically in dev, test, and prod.",
    "#",
    "# To regenerate:",
    "#   python generate_image_assignments.py",
    "",
    "from typing import Dict",
    "",
    "STATIC_IMAGE_ASSIGNMENTS: Dict[str, Dict[str, str]] = {",
]

for mascot, paths in all_assignments.items():
    lines.append(f"    {mascot!r}: {{")
    for label, path in paths.items():
        lines.append(f"        {label!r}: {path!r},")
    lines.append("    },")

lines.append("}")
lines.append("")

output_path = args.output
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

total_entries = sum(len(v) for v in all_assignments.values())
print(f"\nWrote {total_entries} entries across {len(all_assignments)} mascots → {output_path}")
print("Next step: review the file, then commit it to the repo.")
