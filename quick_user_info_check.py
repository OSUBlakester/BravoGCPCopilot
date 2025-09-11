import requests
import time

# Quick check of user info data
url = "https://app.talkwithbravo.com/api/admin/quick-user-info-check"

headers = {
    'Content-Type': 'application/json'
}

data = {
    'admin_password': 'admin123',
    'source_email': 'demo@talkwithbravo.com',
    'target_email': 'demoreadonly@talkwithbravo.com'
}

print("Sending quick user info check request...")
start_time = time.time()

try:
    response = requests.post(url, headers=headers, json=data, timeout=10)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("Response:", result)
    else:
        print("Error Response:", response.text)
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")

print(f"Request took {time.time() - start_time:.2f} seconds")
