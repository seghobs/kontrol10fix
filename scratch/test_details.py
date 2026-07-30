import sys
import os
import logging
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_feed")

from app_core.storage import load_tokens
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
    
    user_id = "48241161356" # yagmuronerr's user id
    
    try:
        url = f"https://i.instagram.com/api/v1/feed/user/{user_id}/"
        response = _get_http_session(username).get(url, headers=headers, timeout=10)
        logger.info("user feed status: %s", response.status_code)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            logger.info("Found %d items in user feed", len(items))
            if items:
                # print keys of first item
                logger.info("First item keys: %s", list(items[0].keys()))
                logger.info("First item likes: %s", items[0].get("like_count"))
        else:
            logger.info("Response text: %s", response.text[:300])
    except Exception as e:
        logger.error("Error: %s", e)

if __name__ == "__main__":
    main()
