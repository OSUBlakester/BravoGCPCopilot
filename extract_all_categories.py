#!/usr/bin/env python3
"""Extract all unique categories from tap interface config"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    service_account_path = CONFIG.get('service_account_key_path')
    if service_account_path and os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()

db = firestore.client()

doc_path = "accounts/aGuIWTRq9qQJZ10FMG2WydRxgC93/users/30037ed8-dbe2-42bb-afb4-4b3af83c20ef/tap_interface_config/config"
doc_ref = db.document(doc_path)
doc = doc_ref.get()

def extract_labels(buttons, depth=0):
    """Recursively extract all button labels"""
    labels = []
    for button in buttons:
        label = button.get('label', '')
        if label and label not in ['Test', 'Favorite Colors', 'Current Events']:  # Skip test/special buttons
            labels.append(label)
        if button.get('children'):
            labels.extend(extract_labels(button['children'], depth + 1))
    return labels

if doc.exists:
    data = doc.to_dict()
    all_labels = extract_labels(data.get('buttons', []))
    
    # Remove duplicates and sort
    unique_labels = sorted(set(all_labels))
    
    print("=== ALL UNIQUE CATEGORIES ===")
    for label in unique_labels:
        print(f"  - {label}")
    
    print(f"\n\nTotal: {len(unique_labels)} categories")
    
    # Generate category_key: prompt mapping
    print("\n\n=== CATEGORY MAPPING (for code) ===")
    for label in unique_labels:
        key = label.lower().replace(' ', '_').replace('&', 'and')
        print(f"                '{key}': 'Generate words and phrases about {label.lower()}',")
