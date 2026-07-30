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
    try:
        from app_core.instagram_api import clear_http_session
        clear_http_session(username)
    except Exception as e:
        logger.warning("deactivate_token: HTTP session silinemedi: %s", e)

    try:
        from app_core.session_state import clear_session
        clear_session(username)
    except Exception as e:
        logger.warning("deactivate_token: DB session silinemedi: %s", e)

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

def handle_invalid_token(username, reason):
    tokens = load_tokens()
    target = next((item for item in tokens if item.get("username") == username), None)
    if not target:
        logger.warning("Self-healing: @%s bulunamadi.", username)
        return False

    # Otomatik giris (relogin) tamamen devre disi birakildi.
    # Token sadece pasife alinir, kullanici manuel olarak admin panelinden "Tekrar Giris Yap" butonuna basmalidir.
    target["is_active"] = False
    target["logout_reason"] = f"{reason} (Manuel giriş bekleniyor)"
    target["logout_time"] = str(datetime.now())
    save_tokens(tokens)
    logger.info("Self-healing: @%s otomatik giris engellendi ve token pasife alindi. Lutfen admin panelinden manuel tekrar giris yapin.", username)
    return False

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
                    logger.info("Token expired/invalid: @%s. Self-healing baslatiliyor...", username)
                    healed = handle_invalid_token(username, "Token sure doldu veya gecersiz")
                    if healed:
                        refreshed_tokens = load_tokens()
                        refreshed_record = next((t for t in refreshed_tokens if t.get("username") == username), None)
                        if refreshed_record and refreshed_record.get("is_active", False):
                            _last_validation_times[username] = datetime.now().timestamp()
                            return refreshed_record
                    
                    excluded_usernames.add(username)
                    continue
                _last_validation_times[username] = current_time

        return token_record

    return None
def fetch_comments_with_failover(media_id, progress_callback=None, token_record=None):
    max_retries = 10
    retry_count = 0
    tried_usernames = set()
    comments_data = []
    last_was_rate_limited = False
    
    if token_record is None:
        token_record = get_working_active_token()

    while retry_count < max_retries:
        if not token_record or not token_record.get("token"):
            break

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
            logger.warning("Token (@%s) rate limited oldu, diger tokenler denenecek.", current_username)
            last_was_rate_limited = True
            retry_count += 1
            tried_usernames.add(current_username)
            token_record = get_working_active_token(tried_usernames)
            continue
        status_code = result.get("status")
        if status_code in [401, 403]:
            tokens = load_tokens()
            deactivate_token(tokens, current_username, "Token gecersiz veya cikis yapildi (Auth Hatasi)")
            save_tokens(tokens)
        elif status_code == 400:
            logger.warning("Token (@%s) yorum listesi icin gecici engel (400) aldi. Token kapatilmiyor.", current_username)

        else:
            logger.warning("Post veya API hatasi (%s). Token yanmadi, ancak islem sonlandiriliyor.", status_code)
            break

        retry_count += 1
        tried_usernames.add(current_username)
        token_record = get_working_active_token(tried_usernames)
        if not token_record:
            break

    if last_was_rate_limited:
        return {"rate_limited": True, "comments": comments_data}
    return comments_data

def fetch_likers_with_failover(media_id, progress_callback=None, token_record=None):
    max_retries = 10
    retry_count = 0
    tried_usernames = set()
    usernames = set()
    last_was_rate_limited = False
    
    if token_record is None:
        token_record = get_working_active_token()

    while retry_count < max_retries:
        if not token_record or not token_record.get("token"):
            break

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
            logger.warning("Token (@%s) rate limited oldu (Begeni), diger tokenler denenecek.", current_username)
            last_was_rate_limited = True
            retry_count += 1
            tried_usernames.add(current_username)
            token_record = get_working_active_token(tried_usernames)
            continue
        status_code = result.get("status")
        if status_code in [401, 403]:
            tokens = load_tokens()
            deactivate_token(tokens, current_username, "Token gecersiz veya cikis yapildi (Auth Hatasi)")
            save_tokens(tokens)
        elif status_code == 400:
            logger.warning("Token (@%s) begeni listesi icin gecici engel (400) aldi. Token kapatilmiyor.", current_username)
        else:
            logger.warning("Post veya API hatasi (%s). Token yanmadi, ancak islem sonlandiriliyor.", status_code)
            break

        retry_count += 1
        tried_usernames.add(current_username)
        token_record = get_working_active_token(tried_usernames)
        if not token_record:
            break

    if last_was_rate_limited:
        return {"rate_limited": True, "usernames": usernames}
    return usernames

def resolve_current_user(token, user_agent, android_id, device_id, username=None):
    try:
        response = fetch_current_user(token, user_agent, android_id, device_id, username=username, timeout=5)
        if response.status_code != 200:
            return None
        return response.json().get("user", {})
    except Exception as error:
        logger.warning("Kullanici bilgisi alinamadi: %s", error)
        return None


def upsert_login_token(username, password, token, android_id, user_agent, device_id):
    try:
        from app_core.instagram_api import clear_http_session
        clear_http_session(username)
    except Exception as e:
        logger.warning("upsert_login_token: HTTP session silinemedi: %s", e)

    try:
        from app_core.session_state import clear_session
        clear_session(username)
    except Exception as e:
        logger.warning("upsert_login_token: DB session silinemedi: %s", e)

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
        existing["relogin_attempts"] = 0
        clear_logout_state(existing)
    else:
        user_data = resolve_current_user(token, user_agent, android_id, device_id, username=username) or {}
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
                "relogin_attempts": 0,
            }
        )

    save_tokens(tokens)
    logger.info("Token kaydedildi: @%s (eski tokenler pasif yapildi)", username)

def relogin_saved_user(username, password_override=None, device_id_override=None, user_agent_override=None, android_id_override=None):
    try:
        from app_core.instagram_api import clear_http_session
        clear_http_session(username)
    except Exception as e:
        logger.warning("relogin_saved_user: HTTP session silinemedi: %s", e)

    try:
        from app_core.session_state import clear_session
        clear_session(username)
    except Exception as e:
        logger.warning("relogin_saved_user: DB session silinemedi: %s", e)

    tokens = load_tokens()
    target = next((item for item in tokens if item.get("username") == username), None)
    if not target:
        return {"ok": False, "code": 404, "message": "Token bulunamadi"}

    # Cooldown kontrolü (DB seviyesinde)
    last_fail = target.get("last_relogin_failed_at", "")
    if last_fail:
        try:
            last_fail_ts = float(last_fail)
            now_ts = datetime.now().timestamp()
            elapsed = now_ts - last_fail_ts
            if elapsed < 180: # 3 dakika
                remaining = int(180 - elapsed)
                return {
                    "ok": False,
                    "code": "COOLDOWN_ACTIVE",
                    "remaining_seconds": remaining,
                    "message": f"Son giriş denemesi başarısız oldu. Lütfen Instagram mobil uygulamasından doğrulama adımını manuel çözün. Tekrar denemek için {remaining} saniye beklemelisiniz."
                }
        except Exception as e:
            logger.warning("Cooldown parse hatasi: %s", e)

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
        # Giriş başarısız olduğunda cooldown zamanını kaydet (DB'ye yaz)
        target["last_relogin_failed_at"] = str(datetime.now().timestamp())
        save_tokens(tokens)
        return {
            "ok": False,
            "code": error.status_code or 400,
            "message": error.message,
            "error_type": error.error_type,
            "details": error.details,
        }

    if not new_token:
        target["last_relogin_failed_at"] = str(datetime.now().timestamp())
        save_tokens(tokens)
        return {"ok": False, "code": 400, "message": "Giris basarisiz - token alinamadi"}

    target["token"] = new_token
    target["android_id_yeni"] = new_android_id
    target["user_agent"] = new_user_agent
    target["device_id"] = new_device_id
    target["password"] = password
    target["is_active"] = True
    target["relogin_attempts"] = 0
    target["last_relogin_failed_at"] = "" # Başarılı girişte temizle
    clear_logout_state(target)
    save_tokens(tokens)

    logger.info("Token yenilendi: @%s", username)
    return {"ok": True, "message": f"@{username} icin token basariyla yenilendi"}


def fetch_group_threads_with_failover(token_record=None):
    max_retries = 3
    retry_count = 0
    tried_usernames = set()
    
    if token_record is None:
        token_record = get_working_active_token()

    while retry_count < max_retries:
        if not token_record or not token_record.get("token"):
            return {"ok": False, "error": "Aktif token bulunamadi"}

        current_username = token_record.get("username", "bilinmeyen")
        from app_core.instagram_api import fetch_group_threads
        result = fetch_group_threads(token_record)

        if result.get("ok"):
            return result

        error_msg = str(result.get("error", ""))
        is_auth_error = any(code in error_msg for code in ["HTTP 400", "HTTP 401", "HTTP 403"])
        
        if is_auth_error:
            logger.info("Direct Inbox (@%s) Auth Hatası aldı. Self-healing baslatiliyor...", current_username)
            healed = handle_invalid_token(current_username, f"Inbox Auth Hatasi: {error_msg}")
            if healed:
                refreshed_tokens = load_tokens()
                refreshed_record = next((t for t in refreshed_tokens if t.get("username") == current_username), None)
                if refreshed_record and refreshed_record.get("is_active", False):
                    token_record = refreshed_record
                    _last_validation_times[current_username] = datetime.now().timestamp()
                    retry_count += 1
                    continue
        else:
            break

        retry_count += 1
        tried_usernames.add(current_username)
        token_record = get_working_active_token(tried_usernames)
        if not token_record:
            break

    return result


def fetch_group_members_with_failover(thread_id, token_record=None):
    max_retries = 3
    retry_count = 0
    tried_usernames = set()
    
    if token_record is None:
        token_record = get_working_active_token()

    while retry_count < max_retries:
        if not token_record or not token_record.get("token"):
            return {"ok": False, "error": "Aktif token bulunamadi"}

        current_username = token_record.get("username", "bilinmeyen")
        from app_core.instagram_api import fetch_group_members
        result = fetch_group_members(token_record, thread_id)

        if result.get("ok"):
            return result

        error_msg = str(result.get("error", ""))
        is_auth_error = any(code in error_msg for code in ["HTTP 400", "HTTP 401", "HTTP 403"])
        
        if is_auth_error:
            logger.info("Direct Members (@%s) Auth Hatası aldı. Self-healing baslatiliyor...", current_username)
            healed = handle_invalid_token(current_username, f"Members Auth Hatasi: {error_msg}")
            if healed:
                refreshed_tokens = load_tokens()
                refreshed_record = next((t for t in refreshed_tokens if t.get("username") == current_username), None)
                if refreshed_record and refreshed_record.get("is_active", False):
                    token_record = refreshed_record
                    _last_validation_times[current_username] = datetime.now().timestamp()
                    retry_count += 1
                    continue
        else:
            break

        retry_count += 1
        tried_usernames.add(current_username)
        token_record = get_working_active_token(tried_usernames)
        if not token_record:
            break

    return result


def fetch_group_media_with_failover(thread_id, target_date, token_record=None):
    max_retries = 3
    retry_count = 0
    tried_usernames = set()
    
    if token_record is None:
        token_record = get_working_active_token()

    while retry_count < max_retries:
        if not token_record or not token_record.get("token"):
            return {"ok": False, "error": "Aktif token bulunamadi"}

        current_username = token_record.get("username", "bilinmeyen")
        from app_core.instagram_api import fetch_group_media
        result = fetch_group_media(token_record, thread_id, target_date)

        if result.get("ok"):
            return result

        error_msg = str(result.get("error", ""))
        is_auth_error = any(code in error_msg for code in ["HTTP 400", "HTTP 401", "HTTP 403"])
        
        if is_auth_error:
            logger.info("Direct Media (@%s) Auth Hatası aldı. Self-healing baslatiliyor...", current_username)
            healed = handle_invalid_token(current_username, f"Media Auth Hatasi: {error_msg}")
            if healed:
                refreshed_tokens = load_tokens()
                refreshed_record = next((t for t in refreshed_tokens if t.get("username") == current_username), None)
                if refreshed_record and refreshed_record.get("is_active", False):
                    token_record = refreshed_record
                    _last_validation_times[current_username] = datetime.now().timestamp()
                    retry_count += 1
                    continue
        else:
            break

        retry_count += 1
        tried_usernames.add(current_username)
        token_record = get_working_active_token(tried_usernames)
        if not token_record:
            break

    return result
