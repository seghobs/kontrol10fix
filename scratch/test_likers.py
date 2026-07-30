import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_likers_failover_real")

from app_core.token_service import get_working_active_token, validate_token, fetch_likers_with_failover
from donustur import donustur

def main():
    token_record = get_working_active_token(skip_validation=True)
    if not token_record:
        logger.error("No token")
        return
        
    validate_token(token_record)
    
    post_link = "https://www.instagram.com/p/DaNPyqHDPRT"
    media_id = donustur(post_link)
    
    likers = fetch_likers_with_failover(media_id, token_record=token_record)
    logger.info("fetch_likers_with_failover returned type: %s", type(likers))
    if isinstance(likers, set):
        logger.info("Success! Likers count: %d", len(likers))
        logger.info("Likers list preview: %s", sorted(list(likers))[:10])
    else:
        logger.error("Failed: %s", likers)

if __name__ == "__main__":
    main()
