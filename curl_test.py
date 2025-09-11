import json

# Just use a simple curl command instead
import subprocess

print("Testing with curl...")

# Simple curl test with shorter timeout
cmd = ["curl", "-X", "POST", 
       "https://app.talkwithbravo.com/api/admin/quick-user-info-check",
       "-H", "Content-Type: application/json",
       "-d", json.dumps({
           "admin_password": "admin123",
           "source_email": "demo@talkwithbravo.com", 
           "target_email": "demoreadonly@talkwithbravo.com"
       }),
       "--max-time", "5"]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
    print(f"Status: {result.returncode}")
    print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Error: {result.stderr}")
except subprocess.TimeoutExpired:
    print("Request timed out after 6 seconds")
except Exception as e:
    print(f"Error: {e}")
