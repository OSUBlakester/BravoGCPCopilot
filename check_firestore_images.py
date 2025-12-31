#!/usr/bin/env python3
"""Quick script to check what's in the images collection"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials

# Initialize Firebase
if not firebase_admin._apps:
    service_account_path = CONFIG.get('service_account_key_path')
    if service_account_path and os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()

db = firestore.Client(project=CONFIG['gcp_project_id'])

print("🔍 Searching for images with concept 'College_Logos'...\n")
images_ref = db.collection('aac_images')

# Use the new filter syntax
query = images_ref.where(filter=firestore.FieldFilter('concept', '==', 'College_Logos'))
docs = list(query.stream())

print(f"📊 Found {len(docs)} images with concept 'College_Logos'\n")

if docs:
    print("First 5 images:\n")
    for doc in docs[:5]:
        data = doc.to_dict()
        print(f"ID: {doc.id}")
        print(f"  Concept: {data.get('concept')}")
        print(f"  Subconcept: {data.get('subconcept')}")
        print(f"  Tags: {data.get('tags', [])}")
        print(f"  Source: {data.get('source')}")
        print(f"  Image URL: {data.get('image_url', '')[:100]}...")
        print()
else:
    print("❌ No images found with concept 'College_Logos'")
    print("\n🔍 Let me check what concepts exist...")
    all_docs = list(images_ref.limit(20).stream())
    concepts = set()
    for doc in all_docs:
        data = doc.to_dict()
        concept = data.get('concept')
        if concept:
            concepts.add(concept)
    
    print(f"\nFound these concepts in the database:")
    for concept in sorted(concepts):
        print(f"  - '{concept}'")
