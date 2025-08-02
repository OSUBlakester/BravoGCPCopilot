#!/usr/bin/env python3
"""Fix broken Unicode characters in gridpage.js"""

# Read the file
with open('static/gridpage.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Define replacements for broken emojis
replacements = {
    "'excuse me': '�'": "'excuse me': '🙏'",
    "'job': '�'": "'job': '💼'", 
    "'read': '�'": "'read': '📖'",
    "'say': '�'": "'say': '💬'",
    "'dancing': '�'": "'dancing': '💃'",
    "'water': '�'": "'water': '💧'", 
    "'fish': '�'": "'fish': '🐟'",
    "'cool': '�'": "'cool': '❄️'",
    "'outdoors': '�'": "'outdoors': '🌲'",
    "'shower': '�'": "'shower': '🚿'",
    "'people': '�'": "'people': '👥'",
    "'student': '�‍🎓'": "'student': '👨‍🎓'",
    "'computer': '�'": "'computer': '💻'",
    "'clothes': '�'": "'clothes': '👕'",
    "'coin': '�'": "'coin': '🪙'",
    "'wind': '�'": "'wind': '💨'",
    "'arm': '�'": "'arm': '💪'",
    "'weak': '�'": "'weak': '😞'",
    "'there': '�'": "'there': '👆'",
    "'stop': '�'": "'stop': '✋'",
    "'quick': '�'": "'quick': '⚡'",
    "'grey': '�'": "'grey': '🔘'", 
    "'ten': '�'": "'ten': '🔟'",
    "'large': '�'": "'large': '📏'",
    "'many': '�'": "'many': '📊'",
    "'broken': '�'": "'broken': '💔'",
    "'answer': '�'": "'answer': '💡'",
    "'ambulance': '�'": "'ambulance': '🚑'",
    "'call': '�'": "'call': '📞'",
    "'video': '�'": "'video': '📹'",
    "'photo': '�'": "'photo': '📷'",
    "'picture': '�️'": "'picture': '🖼️'",
    "'cheap': '�'": "'cheap': '💰'"
}

# Apply replacements
for old, new in replacements.items():
    content = content.replace(old, new)

# Write back
with open('static/gridpage.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed broken emojis in gridpage.js")
