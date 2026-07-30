import re
import logging

logger = logging.getLogger(__name__)


def donustur(link_gir):
    def shortcode_to_numeric_media_id(shortcode):
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        base = len(alphabet)
        numeric_id = 0
        for char in shortcode:
            numeric_id = numeric_id * base + alphabet.index(char)
        return numeric_id

    link = str(link_gir or "").strip()
    match = re.search(r"instagram\.com/(?:p|reel|tv)/([a-zA-Z0-9\-_]+)", link)

    if not match:
        logger.warning("Gecersiz Instagram linki: %s", link)
        return None

    shortcode = match.group(1)
    numeric_media_id = shortcode_to_numeric_media_id(shortcode)
    logger.info("Link: %s | Shortcode: %s | Media ID: %s", link, shortcode, numeric_media_id)
    return numeric_media_id
