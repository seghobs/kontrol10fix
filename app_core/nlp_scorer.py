import re
from app_core.storage import get_user_recent_comments

GENERIC_SPAM_WORDS = {
    "harika", "guzel", "güzel", "super", "süper", "muhtesem", "muhteşem", 
    "post", "paylasim", "paylaşım", "foto", "resim", "tebrik", "tebrikler", 
    "basarilar", "başarılar", "amazing", "great", "nice", "cool", "wow", 
    "harikasin", "harikasın", "mükemmel", "mukemmel", "efsane", "cok", "çok",
    "iyi", "guzeldi", "güzeldi", "harikaa", "harikaaa"
}

def count_emojis(text):
    if not text:
        return 0
    emoji_count = 0
    for char in text:
        cp = ord(char)
        if (0x1F600 <= cp <= 0x1F64F) or \
           (0x1F300 <= cp <= 0x1F5FF) or \
           (0x1F680 <= cp <= 0x1F6FF) or \
           (0x1F1E0 <= cp <= 0x1F1FF) or \
           (0x2600 <= cp <= 0x27BF) or \
           (0x1F900 <= cp <= 0x1F9FF) or \
           (0x1FA70 <= cp <= 0x1FAFF):
            emoji_count += 1
    return emoji_count

def clean_text_words(text):
    if not text:
        return []
    # Remove emojis first
    cleaned_chars = []
    for char in text:
        cp = ord(char)
        if not ((0x1F600 <= cp <= 0x1F64F) or \
                (0x1F300 <= cp <= 0x1F5FF) or \
                (0x1F680 <= cp <= 0x1F6FF) or \
                (0x1F1E0 <= cp <= 0x1F1FF) or \
                (0x2600 <= cp <= 0x27BF) or \
                (0x1F900 <= cp <= 0x1F9FF) or \
                (0x1FA70 <= cp <= 0x1FAFF)):
            cleaned_chars.append(char)
    cleaned_text = "".join(cleaned_chars).lower()
    # Replace punctuation with space
    cleaned_text = re.sub(r'[^\w\s]', ' ', cleaned_text)
    return [w for w in cleaned_text.split() if len(w) > 0]

def calculate_comment_spam_score(username, comment_text):
    if not comment_text or not comment_text.strip():
        return 100.0  # Empty comment is full spam
        
    score = 0.0
    text = comment_text.strip()
    words = clean_text_words(text)
    emojis_count = count_emojis(text)
    
    # 1. Length check
    if len(text) < 10:
        score += 30
    elif len(text) < 18:
        score += 15
        
    # 2. Word count check
    if len(words) == 0:
        score += 50
    elif len(words) == 1:
        score += 35
    elif len(words) == 2:
        score += 15
        
    # 3. Generic/Spam word density
    if len(words) > 0:
        generic_count = sum(1 for w in words if w in GENERIC_SPAM_WORDS)
        generic_ratio = generic_count / len(words)
        if generic_ratio >= 0.8:
            score += 30
        elif generic_ratio >= 0.5:
            score += 15
            
    # 4. Emoji density (too many emojis relative to words)
    if len(words) > 0:
        emoji_word_ratio = emojis_count / len(words)
        if emoji_word_ratio > 2.0:
            score += 25
        elif emoji_word_ratio > 1.0:
            score += 15
    else:
        if emojis_count > 0:
            score += 35
            
    # 5. Comment repetition/duplicates check (History-based)
    recent_comments = get_user_recent_comments(username, limit=5)
    if recent_comments:
        clean_text = text.lower().strip()
        exact_matches = sum(1 for rc in recent_comments if rc.lower().strip() == clean_text)
        if exact_matches >= 3:
            score += 50  # Spammed the exact same comment 3+ times recently
        elif exact_matches >= 1:
            score += 25  # Repeated the exact same comment recently
            
    # Cap score at 100.0 and round to 1 decimal place
    return round(min(score, 100.0), 1)
