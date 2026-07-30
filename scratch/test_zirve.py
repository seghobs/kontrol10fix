import sys
import os
import logging
import base64
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_400_debug")

from app_core.token_service import get_working_active_token, validate_token
from donustur import donustur
from app_core.instagram_api import _get_username, build_auth_headers, _get_http_session

def main():
    token_record = get_working_active_token(skip_validation=True)
    if not token_record:
        logger.error("No token")
        return
        
    validate_token(token_record)
    
    username = _get_username(token_record)
    token = token_record.get("token", "")
    user_agent = token_record.get("user_agent", "")
    android_id = token_record.get("android_id_yeni", "")
    device_id = token_record.get("device_id", "")
    
    headers = build_auth_headers(token, user_agent, android_id, device_id, username=username)
    
    # Construct cookie header
    token_data = token.replace("Bearer IGT:2:", "").strip()
    missing_padding = len(token_data) % 4
    if missing_padding:
        token_data += "=" * (4 - missing_padding)
    decoded_bytes = base64.b64decode(token_data)
    decoded_str = decoded_bytes.decode("utf-8", errors="ignore")
    data = json.loads(decoded_str)
    
    ds_user_id = data.get("ds_user_id")
    sessionid = data.get("sessionid")
    if ds_user_id and sessionid:
        headers["cookie"] = f"sessionid={sessionid}; ds_user_id={ds_user_id}"
        
    post_link = "https://www.instagram.com/p/DaQZMtXioYn"
    media_id = donustur(post_link)
    
    try:
        url = f"https://i.instagram.com/api/v1/media/{media_id}/likers/"
        response = _get_http_session(username).get(url, headers=headers, timeout=10)
        logger.info("Likers status code: %s", response.status_code)
        logger.info("Likers response headers: %s", response.headers)
        logger.info("Likers response body: %s", response.text)
    except Exception as e:
        logger.error("Error: %s", e)

if __name__ == "__main__":
    main()
