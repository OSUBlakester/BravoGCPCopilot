#!/usr/bin/env python3
"""
Quick script to check tap interface config and categories from Firestore
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    service_account_path = CONFIG.get('service_account_key_path')
    if service_account_path and os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()

db = firestore.client()

# The specific document path you provided
doc_path = "accounts/aGuIWTRq9qQJZ10FMG2WydRxgC93/users/30037ed8-dbe2-42bb-afb4-4b3af83c20ef/tap_interface_config/config"

print(f"\n=== Fetching Tap Interface Config ===")
print(f"Path: {doc_path}\n")

doc_ref = db.document(doc_path)
doc = doc_ref.get()

if doc.exists:
    data = doc.to_dict()
    print("✓ Document found!\n")
    
    # Print full config
    print("=== FULL CONFIG ===")
    print(json.dumps(data, indent=2, default=str))
    
    # Extract buttons and their prompt categories
    if 'buttons' in data:
        print("\n=== BUTTONS WITH CATEGORIES ===")
        unique_labels = set()
        for idx, button in enumerate(data['buttons']):
            label = button.get('label', 'Unnamed')
            unique_labels.add(label)
            print(f"\n[{idx}] {label}")
            if 'prompt_category' in button:
                print(f"  Category: {button['prompt_category']}")
            if 'llm_prompt' in button and button['llm_prompt']:
                prompt_preview = button['llm_prompt'][:100] if len(button['llm_prompt']) > 100 else button['llm_prompt']
                print(f"  LLM Prompt: {prompt_preview}...")
            if 'prompt_topic' in button:
                print(f"  Topic: {button['prompt_topic']}")
            if 'prompt_examples' in button:
                examples_preview = button['prompt_examples'][:100] if len(button['prompt_examples']) > 100 else button['prompt_examples']
                print(f"  Examples: {examples_preview}...")
        
        print("\n\n=== UNIQUE BUTTON LABELS (Potential Categories) ===")
        for label in sorted(unique_labels):
            print(f"  - {label}")
    
    # Check for categories collection
    print("\n\n=== Checking for prompt_categories subcollection ===")
    categories_path = f"{doc_path}/prompt_categories"
    categories_ref = db.collection(categories_path)
    categories = categories_ref.stream()
    
    category_list = []
    for cat in categories:
        category_list.append(cat.to_dict())
        print(f"  - {cat.id}: {cat.to_dict()}")
    
    if not category_list:
        print("  (No subcollection found)")
        
        # Check parent level for categories
        print("\n=== Checking parent level for categories ===")
        parent_path = "accounts/aGuIWTRq9qQJZ10FMG2WydRxgC93/users/30037ed8-dbe2-42bb-afb4-4b3af83c20ef/tap_interface_config/prompt_categories"
        parent_cat_ref = db.collection(parent_path)
        parent_cats = parent_cat_ref.stream()
        
        for cat in parent_cats:
            print(f"  - {cat.id}: {cat.to_dict()}")
    
else:
    print("✗ Document not found!")
    print("\nTrying to list all tap_interface_config documents...")
    
    parent_path = "accounts/aGuIWTRq9qQJZ10FMG2WydRxgC93/users/30037ed8-dbe2-42bb-afb4-4b3af83c20ef/tap_interface_config"
    collection_ref = db.collection(parent_path)
    docs = collection_ref.stream()
    
    for doc in docs:
        print(f"  Found: {doc.id}")
