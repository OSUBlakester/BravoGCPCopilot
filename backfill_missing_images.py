#!/usr/bin/env python3
"""
Backfill script to scan all pages/buttons for the current account/user and generate a CSV of missing-image terms.
This calls the server-side `/api/missing-images/scan` endpoint which uses the same image-search logic and writes to Firestore.

Usage:
  python backfill_missing_images.py --base-url https://dev.talkwithbravo.com --id-token <FIREBASE_ID_TOKEN>

If you don't provide an ID token, the script attempts to read it from the FIREBASE_ID_TOKEN env var.
"""

import argparse
import csv
import os
import sys
import json
import asyncio
import aiohttp


async def run_scan(base_url, id_token, out_file):
    headers = {
        'Authorization': f'Bearer {id_token}',
        'Content-Type': 'application/json'
    }

    scan_url = f"{base_url}/api/missing-images/scan"
    async with aiohttp.ClientSession() as session:
        async with session.post(scan_url, headers=headers) as resp:
            if resp.status != 200:
                print(f"Scan failed: HTTP {resp.status}")
                print(await resp.text())
                return 1
            data = await resp.json()

    details = data.get('details', [])
    if not details:
        print("No terms scanned or no details returned")
        return 0

    with open(out_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['term', 'found', 'error'])
        writer.writeheader()
        for row in details:
            writer.writerow({
                'term': row.get('term'),
                'found': row.get('found'),
                'error': row.get('error', '')
            })

    print(f"Scan complete. Results written to {out_file}")
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True, help='Base URL of the app (e.g., https://dev.talkwithbravo.com)')
    parser.add_argument('--id-token', required=False, help='Firebase ID token for an authenticated user (reads FIREBASE_ID_TOKEN env var if not provided)')
    parser.add_argument('--out', default='missing_images_scan.csv', help='Output CSV filename')

    args = parser.parse_args()
    id_token = args.id_token or os.environ.get('FIREBASE_ID_TOKEN')
    if not id_token:
        print('ERROR: You must provide a Firebase ID token via --id-token or FIREBASE_ID_TOKEN env var')
        sys.exit(1)

    asyncio.run(run_scan(args.base_url.rstrip('/'), id_token, args.out))
