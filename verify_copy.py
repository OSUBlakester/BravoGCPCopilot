import requests
import json

# Use the working profile copy endpoint to check what happened
print("Testing profile copy with a single profile to see logs...")

url = "https://app.talkwithbravo.com/api/admin/copy-profiles-between-accounts"

data = {
    "admin_password": "admin123",
    "source_email": "demo@talkwithbravo.com",
    "target_email": "demoreadonly@talkwithbravo.com"
}

headers = {
    'Content-Type': 'application/json'
}

try:
    print("Sending profile copy request to check logs...")
    response = requests.post(url, headers=headers, json=data, timeout=60)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("Response:")
        print(json.dumps(result, indent=2))
        
        # Look for any specific info about user_info copying
        for key, value in result.items():
            if 'user_info' in key.lower() or 'copied' in key.lower():
                print(f"\nKey result: {key}: {value}")
    else:
        print("Error Response:", response.text)
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
