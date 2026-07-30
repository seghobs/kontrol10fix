import sys
import os
import requests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
logging.basicConfig(level=logging.INFO)

from app_core.storage import load_tokens
from app_core.instagram_api import _get_username, build_auth_headers
from donustur import donustur

tokens = load_tokens()
active_token = next((t for t in tokens if t.get("is_active")), None)

if not active_token:
    print("No active token found!")
    sys.exit(1)

username = _get_username(active_token)
token = active_token.get("token", "")
user_agent = active_token.get("user_agent", "")
android_id = active_token.get("android_id_yeni", "")
device_id = active_token.get("device_id", "")

headers = build_auth_headers(token, user_agent, android_id, device_id, username=username)

# Famous post (public, has millions of likes)
link = "https://www.instagram.com/p/C-0c2jVop1w" # A public post code
media_id = donustur(link)

print("TRYING FAMOUS POST:")
response = requests.get(
    f"https://i.instagram.com/api/v1/media/{media_id}/likers/",
    headers=headers,
    timeout=15,
)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    usernames = {u.get("username") for u in response.json().get("users", [])}
    print(f"Liker usernames count: {len(usernames)}")
    print(f"Liker usernames snippet: {list(usernames)[:10]}")
else:
    print(f"Error response: {response.text}")
