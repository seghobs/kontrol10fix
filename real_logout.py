import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import uuid
from app_core.storage import init_storage, load_tokens
from app_core.instagram_api import build_auth_headers, _get_http_session, _update_session_from_response, validate_token

init_storage()
tokens = load_tokens(include_deleted=True)
target_username = "kendin_yap332"
target_token = next((t for t in tokens if t.get("username") == target_username), None)

if not target_token:
    print("Error: Token not found.")
    sys.exit(1)

username = target_token.get("username")
token = target_token.get("token")
user_agent = target_token.get("user_agent")
android_id = target_token.get("android_id_yeni")
device_id = target_token.get("device_id")

headers = build_auth_headers(token, user_agent, android_id, device_id, username=username)
headers["Authorization"] = token
headers.update({
    "x-ig-app-locale": "tr_TR",
    "x-ig-device-locale": "tr_TR",
    "x-ig-mapped-locale": "tr_TR",
    "x-ig-capabilities": "3brTv10=",
    "x-ig-connection-type": "WIFI",
    "x-fb-connection-type": "WIFI",
    "accept-language": "tr-TR, en-US",
})

payload = {
    "phone_id": str(uuid.uuid4()),
    "device_id": device_id,
    "guid": device_id,
    "one_tap_app_login": "false",
    "username": username
}

print("Sending POST request to Instagram logout API with full payload...")
print(f"Headers sent: {json.dumps({k: v[:30] + '...' if len(v) > 30 else v for k, v in headers.items()}, indent=2)}")
session = _get_http_session(username)
response = session.post(

    "https://i.instagram.com/api/v1/accounts/logout/",
    headers=headers,
    data=payload,
    timeout=15
)
_update_session_from_response(username, response)
print(f"Response status: {response.status_code}")
print(f"Response text: {response.text}")

print("Testing validation now...")
is_valid = validate_token(target_token)
print(f"validate_token result after logout: {is_valid}")
