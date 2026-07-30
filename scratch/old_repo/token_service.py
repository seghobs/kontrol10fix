import logging
from datetime import datetime

from log_in import giris_yap
from log_in import LoginError

from app_core.instagram_api import fetch_comment_usernames, fetch_current_user, validate_token
from app_core.storage import load_tokens, save_tokens

logger = logging.getLogger(__name__)

# Memory cache for last validation times to prevent spamming the validation endpoint
_last_validation_times = {}


def deactivate_token(tokens, username, reason):
    for token in tokens:
        if token.get("username") == username:
            token["is_active"] = False
            token["logout_reason"] = reason
            token["logout_time"] = str(datetime.now())
            logger.info("Token pasife alindi: @%s — %s", username, reason)
            return True
    return False


def clear_logout_state(token):
    token.pop("logout_reason", None)
    token.pop("logout_time", None)


def get_working_active_token(excluded_usernames=None, skip_validation=False):
    if excluded_usernames is None:
        excluded_usernames = set()

    tokens = load_tokens()

    for token_record in tokens:
        if not token_record.get("is_active", False):
            continue

        username = token_record.get("username", "")
        if username in excluded_usernames:
            continue

        android_id = token_record.get("android_id_yeni", "").strip()
        user_agent = token_record.get("user_agent", "").strip()
        device_id = token_record.get("device_id", "").strip()
        token_value = token_record.get("token", "").strip()

        if not android_id or not user_agent or not device_id or not token_value:
            continue

        # Session state'i DB'den yükle
        try:
            from app_core.session_state import load_from_db
            load_from_db(username)
        except Exception:
            pass

        # Validate token before using (cached for 5 minutes to prevent spam)
        if not skip_validation:
            current_time = datetime.now().timestamp()
            last_val = _last_validation_times.get(username, 0)
            
            if current_time - last_val > 300: # 300 seconds = 5 minutes
                from app_core.instagram_api import validate_token
                is_valid = validate_token(token_record)
                if not is_valid:
                    # Token expired/invalid - mark as inactive
                    logger.info("Token expired/invalid: @%s", username)
                    deactivate_token(tokens, username, "Token sure doldu veya gecersiz")
                    save_tokens(tokens)
                    excluded_usernames.add(username)
                    continue
                _last_validation_times[username] = current_time

        return token_record

    return None


def fetch_comments_with_failover(media_id, progress_callback=None, token_record=None):
    max_retries = 10
    retry_count = 0
    tried_usernames = set()
    # usernames can be a set of strings or a list of tuples (username, text)
    comments_data = []
    
    if token_record is None:
        token_record = get_working_active_token()

    while retry_count < max_retries:
        if not token_record or not token_record.get("token"):
            return []

        current_username = token_record.get("username", "bilinmeyen")
        logger.info("Token kullaniliyor: @%s", current_username)

        try:
            result = fetch_comment_usernames(media_id, token_record, progress_callback=progress_callback)
        except Exception as error:
            logger.error("Yorum cekme hatasi: %s", error)
            result = {"ok": False, "status": 500, "comments": comments_data}

        comments_data = result.get("comments", [])

        if result.get("ok"):
            logger.info("Basari! Toplam %d yorum bulundu.", len(comments_data))
            return comments_data

        if result.get("rate_limited"):
            return {"rate_limited": True, "comments": comments_data}

        status_code = result.get("status")
        if status_code in [401, 403]:
            tokens = load_tokens()
            deactivate_token(tokens, current_username, "Token gecersiz veya cikis yapildi (Auth Hatasi)")
            save_tokens(tokens)
        else:
            logger.warning("Post veya API hatasi (%s). Token yanmadi, ancak islem sonlandiriliyor.", status_code)
            break

        retry_count += 1
        tried_usernames.add(current_username)
        token_record = get_working_active_token(tried_usernames)
        if not token_record:
            break

    return comments_data


def fetch_likers_with_failover(media_id, progress_callback=None, token_record=None):
    max_retries = 10
    retry_count = 0
    tried_usernames = set()
    usernames = set()
    if token_record is None:
        token_record = get_working_active_token()

    while retry_count < max_retries:
        if not token_record or not token_record.get("token"):
            return set()

        current_username = token_record.get("username", "bilinmeyen")
        logger.info("Token kullaniliyor (Begeni): @%s", current_username)

        try:
            from app_core.instagram_api import fetch_liker_usernames
            result = fetch_liker_usernames(media_id, token_record, progress_callback=progress_callback)
        except Exception as error:
            logger.error("Begeni cekme hatasi: %s", error)
            result = {"ok": False, "status": 500, "usernames": usernames}

        usernames = result.get("usernames", set())

        if result.get("ok"):
            logger.info("Basari! Toplam %d liker bulundu.", len(usernames))
            return usernames

        if result.get("rate_limited"):
            return {"rate_limited": True, "usernames": usernames}

        status_code = result.get("status")
        if status_code in [401, 403]:
            tokens = load_tokens()
            deactivate_token(tokens, current_username, "Token gecersiz veya cikis yapildi (Auth Hatasi)")
            save_tokens(tokens)
        else:
            logger.warning("Post veya API hatasi (%s). Token yanmadi, ancak islem sonlandiriliyor.", status_code)
            break

        retry_count += 1
        tried_usernames.add(current_username)
        token_record = get_working_active_token(tried_usernames)
        if not token_record:
            break

    return usernames


def resolve_current_user(token, user_agent, android_id, device_id):
    try:
        response = fetch_current_user(token, user_agent, android_id, device_id, timeout=5)
        if response.status_code != 200:
            return None
        return response.json().get("user", {})
    except Exception as error:
        logger.warning("Kullanici bilgisi alinamadi: %s", error)
        return None


def upsert_login_token(username, password, token, android_id, user_agent, device_id):
    tokens = load_tokens()
    existing = next((item for item in tokens if item.get("username") == username), None)

    # Once a new login happens, deactivate ALL old tokens for this username
    for t in tokens:
        if t.get("username") == username:
            t["is_active"] = False

    if existing:
        existing["password"] = password
        existing["token"] = token
        existing["android_id_yeni"] = android_id
        existing["user_agent"] = user_agent
        existing["device_id"] = device_id
        existing["is_active"] = True
        clear_logout_state(existing)
    else:
        user_data = resolve_current_user(token, user_agent, android_id, device_id) or {}
        tokens.append(
            {
                "username": username,
                "full_name": user_data.get("full_name", ""),
                "password": password,
                "token": token,
                "android_id_yeni": android_id,
                "user_agent": user_agent,
                "device_id": device_id,
                "is_active": True,
                "added_at": str(datetime.now()),
            }
        )

    save_tokens(tokens)
    logger.info("Token kaydedildi: @%s (eski tokenler pasif yapildi)", username)


def relogin_saved_user(username, password_override=None, device_id_override=None, user_agent_override=None, android_id_override=None):
    tokens = load_tokens()
    target = next((item for item in tokens if item.get("username") == username), None)
    if not target:
        return {"ok": False, "code": 404, "message": "Token bulunamadi"}

    stored_password = str(target.get("password", "")).strip()
    stored_android = str(target.get("android_id_yeni", "")).strip()
    stored_user_agent = str(target.get("user_agent", "")).strip()
    stored_device_id = str(target.get("device_id", "")).strip()

    password = (password_override or "").strip() or stored_password
    android_id = (android_id_override or "").strip() or stored_android
    user_agent = (user_agent_override or "").strip() or stored_user_agent
    device_id = (device_id_override or "").strip() or stored_device_id

    missing = []
    if not password:
        missing.append("password")
    if not android_id:
        missing.append("android_id")
    if not user_agent:
        missing.append("user_agent")
    if not device_id:
        missing.append("device_id")
    if missing:
        labels = {"password": "Sifre", "android_id": "Android ID", "user_agent": "User Agent", "device_id": "Device ID"}
        msg = "Eksik alanlar: " + ", ".join(labels.get(k, k) for k in missing) + ". Lutfen girin."
        return {"ok": False, "code": "FIELDS_REQUIRED", "missing": missing, "message": msg}

    try:
        new_token, new_android_id, new_user_agent, new_device_id = giris_yap(
            username,
            password,
            android_id,
            user_agent,
            device_id,
        )
    except LoginError as error:
        logger.error("Giriş hatası: %s | Tip: %s", error.message, error.error_type)
        return {
            "ok": False,
            "code": error.status_code or 400,
            "message": error.message,
            "error_type": error.error_type,
            "details": error.details,
        }

    if not new_token:
        return {"ok": False, "code": 400, "message": "Giris basarisiz - token alinamadi"}

    target["token"] = new_token
    target["android_id_yeni"] = new_android_id
    target["user_agent"] = new_user_agent
    target["device_id"] = new_device_id
    target["password"] = password
    target["is_active"] = True
    clear_logout_state(target)
    save_tokens(tokens)

    logger.info("Token yenilendi: @%s", username)
    return {"ok": True, "message": f"@{username} icin token basariyla yenilendi"}
