import json

# Check the button in the JSON to understand its source
with open('/Users/blakethomas/Documents/BravoGCPCopilot/AccentToBravo/all_pages_FINAL.json', 'r') as f:
    all_data = json.load(f)

page = all_data['pages']['0017']
button = [b for b in page['buttons'] if b['sequence'] == 35][0]

print("Button 0017/35 from JSON:")
print(json.dumps(button, indent=2))
print()

# Check if this page has other buttons to understand the pattern
print(f"All buttons on page 0017:")
for b in page['buttons']:
    print(f"  {b['sequence']:3d}: name={repr(b['name']):20s} speech={repr(b['speech']):20s} nav={b['navigation_type']} icon={b['icon']}")
