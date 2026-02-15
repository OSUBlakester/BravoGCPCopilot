#!/usr/bin/env python3
import json

with open('all_pages_FINAL.json') as f:
    data = json.load(f)

pages = data['pages']
if '3f16' in pages:
    buttons = pages['3f16']['buttons']
    btn = buttons[1]  # Button 1
    print(json.dumps(btn, indent=2))
