import html
import json
import logging

from flask import Blueprint, redirect, render_template, request, session, url_for

from app_core.api_response import api_response
from app_core.config import ADMIN_PASSWORD
from app_core.instagram_api import fetch_current_user, validate_token
from app_core.storage import (
    add_audit_log,
    count_tokens,
    get_audit_logs,
    get_audit_relogin_count,
    load_exemptions,
    load_exemptions_grouped,
    load_global_exemptions,
    add_global_exemption,
    remove_global_exemption,
    load_tokens,
    save_exemptions,
    save_tokens,
    hard_delete_token,
    restore_token,
)
from app_core.token_service import clear_logout_state, relogin_saved_user, get_working_active_token
from app_core.instagram_api import fetch_group_threads, fetch_own_thread_items, delete_thread_item
from app_core.automation import load_automations, save_automations
from app_core.validators import is_valid_android_id, is_valid_device_id, is_valid_post_link, is_valid_username

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _require_admin():
    if not session.get("admin_logged_in"):
        return api_response(False, "UNAUTHORIZED", "Yetkisiz erisim", http_status=401)
    return None


def _normalize_post_link(value):
    return html.unescape(str(value or "").strip())


@admin_bp.route("", methods=["GET"])
@admin_bp.route("/", methods=["GET"])
def panel():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))
    return render_template("admin.html")


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            logger.info("Admin girisi basarili.")
            return redirect(url_for("admin.panel"))
        logger.warning("Hatali admin giris denemesi.")
        return render_template("admin_login.html", error=True)
    return render_template("admin_login.html", error=False)


@admin_bp.route("/logout", methods=["GET"])
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/get_tokens", methods=["GET"])
def get_tokens_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    username = request.args.get("username", "").strip() or None
    if username:
        all_tokens = load_tokens(include_deleted=True)
        one = next((t for t in all_tokens if t.get("username") == username), None)
        if not one:
            return api_response(False, "NOT_FOUND", "Token bulunamadi", http_status=404)
        return api_response(True, "OK", "Basarili", extra={"tokens": [one], "total": 1, "page": 1, "page_size": 1})
    search = request.args.get("search", "").strip() or None
    page = request.args.get("page", type=int)
    page_size = request.args.get("page_size", type=int)
    include_deleted = request.args.get("include_deleted", "").lower() == "true"
    tokens = load_tokens(include_deleted=include_deleted, search=search, page=page, page_size=page_size)
    total = count_tokens(include_deleted=include_deleted, search=search)
    deleted_count = count_tokens(include_deleted=True, search=search) - count_tokens(include_deleted=False, search=search) if not include_deleted else 0
    return api_response(
        True,
        "OK",
        "Basarili",
        extra={
            "tokens": tokens,
            "total": total,
            "page": page or 1,
            "page_size": page_size or 0,
            "deleted_count": max(0, deleted_count),
        },
    )


@admin_bp.route("/add_token", methods=["POST"])
def add_token():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    try:
        data = request.get_json() or {}
        required_fields = ["token", "android_id", "user_agent", "device_id", "password"]
        if not all(str(data.get(field, "")).strip() for field in required_fields):
            return api_response(False, "MISSING_FIELDS", "Tum alanlar zorunlu")

        if not is_valid_android_id(data["android_id"]):
            return api_response(False, "INVALID_ANDROID_ID", "Gecersiz Android ID formati (16 haneli hex bekleniyor)")

        if not is_valid_device_id(data["device_id"]):
            return api_response(False, "INVALID_DEVICE_ID", "Gecersiz Device ID formati")

        response = fetch_current_user(
            token=data["token"],
            user_agent=data["user_agent"],
            android_id=data["android_id"],
            device_id=data["device_id"],
            timeout=5,
        )
        if response.status_code != 200:
            return api_response(False, "INVALID_TOKEN", "Token gecersiz")

        user_data = response.json().get("user", {})
        username = user_data.get("username")
        full_name = user_data.get("full_name", "")
        if not username:
            return api_response(False, "NO_USERNAME", "Kullanici adi alinamadi")

        from datetime import datetime

        tokens = load_tokens()
        
        # Once a new token is added, deactivate ALL old tokens for this username
        for t in tokens:
            if t.get("username") == username:
                t["is_active"] = False
        
        new_token = {
            "username": username,
            "full_name": full_name,
            "password": data["password"].strip(),
            "token": data["token"],
            "android_id_yeni": data["android_id"],
            "user_agent": data["user_agent"],
            "device_id": data["device_id"],
            "is_active": data.get("is_active", True),
            "added_at": data.get("added_at", str(datetime.now())),
            "relogin_attempts": 0,
        }

        replaced = False
        for idx, token in enumerate(tokens):
            if token.get("username") == username:
                tokens[idx] = new_token
                replaced = True
                break
        if not replaced:
            tokens.append(new_token)

        save_tokens(tokens)
        action = "guncellendi" if replaced else "eklendi"
        add_audit_log("token", username, f"token_{action}", f"@{username} icin token {action}")
        logger.info("Token %s: @%s", action, username)

        return api_response(
            True,
            "TOKEN_ADDED",
            f"@{username} ({full_name}) icin token {action}",
            extra={"username": username, "full_name": full_name},
        )
    except Exception as error:
        logger.error("Token ekleme hatasi: %s", error)
        return api_response(False, "ERROR", f"Token eklenemedi: {error}", http_status=500)


@admin_bp.route("/delete_token", methods=["POST"])
def delete_token():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    username = data.get("username", "").strip()
    if not username:
        return api_response(False, "MISSING_USERNAME", "Kullanici adi belirtilmedi")

    if not hard_delete_token(username):
        return api_response(False, "ERROR", "Silme islemi basarisiz", http_status=500)
    add_audit_log("token", username, "token_silindi")
    return api_response(True, "DELETED", f"{username} sistemden tamamen silindi")


@admin_bp.route("/restore_token", methods=["POST"])
def restore_token_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    username = data.get("username", "").strip()
    if not username:
        return api_response(False, "MISSING_USERNAME", "Kullanici adi belirtilmedi")

    if not restore_token(username):
        return api_response(False, "ERROR", "Geri alma islemi basarisiz", http_status=500)
    add_audit_log("token", username, "token_geri_alindi")
    return api_response(True, "RESTORED", f"@{username} geri alindi")


@admin_bp.route("/toggle_token", methods=["POST"])
def toggle_token():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    username = data.get("username", "").strip()
    if not username:
        return api_response(False, "MISSING_USERNAME", "Kullanici adi belirtilmedi")

    tokens = load_tokens()
    for token in tokens:
        if token.get("username") == username:
            token["is_active"] = not token.get("is_active", False)
            if token["is_active"]:
                clear_logout_state(token)
            save_tokens(tokens)
            status = "aktif" if token["is_active"] else "pasif"
            return api_response(
                True,
                "TOGGLED",
                f"{username} icin token {status} yapildi",
                extra={"is_active": token["is_active"]},
            )

    return api_response(False, "NOT_FOUND", "Token bulunamadi", http_status=404)


@admin_bp.route("/update_token", methods=["POST"])
def update_token():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    try:
        data = request.get_json() or {}
        required_fields = ["username", "token", "android_id", "user_agent", "device_id", "password"]
        if not all(str(data.get(field, "")).strip() for field in required_fields):
            return api_response(False, "MISSING_FIELDS", "Tum alanlar zorunlu")

        if not is_valid_android_id(data["android_id"]):
            return api_response(False, "INVALID_ANDROID_ID", "Gecersiz Android ID formati")

        if not is_valid_device_id(data["device_id"]):
            return api_response(False, "INVALID_DEVICE_ID", "Gecersiz Device ID formati")

        # Yeni token'la sorgu yapmadan önce mevcut oturumu sıfırlıyoruz ki eski çerezlerle karışmasın
        try:
            from app_core.instagram_api import clear_http_session
            clear_http_session(data["username"])
        except Exception:
            pass
        try:
            from app_core.session_state import clear_session
            clear_session(data["username"])
        except Exception:
            pass

        validate_response = fetch_current_user(
            token=data["token"],
            user_agent=data["user_agent"],
            android_id=data["android_id"],
            device_id=data["device_id"],
            username=data["username"],
            timeout=5,
        )
        if validate_response.status_code != 200:
            return api_response(False, "INVALID_TOKEN", "Yeni token gecersiz")


        tokens = load_tokens()
        for token in tokens:
            if token.get("username") == data["username"]:
                token["token"] = data["token"]
                token["android_id_yeni"] = data["android_id"]
                token["user_agent"] = data["user_agent"]
                token["device_id"] = data["device_id"]
                token["password"] = data["password"]
                token["is_active"] = True
                token["relogin_attempts"] = 0
                clear_logout_state(token)
                save_tokens(tokens)
                add_audit_log("token", data["username"], "token_guncellendi")
                return api_response(True, "UPDATED", f"@{data['username']} icin token basariyla guncellendi")

        return api_response(False, "NOT_FOUND", "Token bulunamadi", http_status=404)
    except Exception as error:
        logger.error("Token guncelleme hatasi: %s", error)
        return api_response(False, "ERROR", f"Token guncellenemedi: {error}", http_status=500)


@admin_bp.route("/relogin_token", methods=["POST"])
def relogin_token():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    username = data.get("username", "").strip()
    if not username:
        return api_response(False, "MISSING_USERNAME", "Kullanici adi belirtilmedi")

    password_override = (data.get("password") or "").strip() or None
    device_id_override = (data.get("device_id") or "").strip() or None
    user_agent_override = (data.get("user_agent") or "").strip() or None
    android_id_override = (data.get("android_id") or "").strip() or None
    result = relogin_saved_user(
        username,
        password_override=password_override,
        device_id_override=device_id_override,
        user_agent_override=user_agent_override,
        android_id_override=android_id_override,
    )
    if not result.get("ok"):
        code = result.get("code", 400)
        if code == "FIELDS_REQUIRED":
            return api_response(False, "FIELDS_REQUIRED", result.get("message"), extra={"missing": result.get("missing", [])}, http_status=200)
        if code == "COOLDOWN_ACTIVE":
            return api_response(False, "COOLDOWN_ACTIVE", result.get("message"), extra={"remaining_seconds": result.get("remaining_seconds")}, http_status=200)
        return api_response(False, "RELOGIN_FAILED", result.get("message"), http_status=code if isinstance(code, int) else 400)

    add_audit_log("token", username, "relogin_basarili")
    return api_response(True, "RELOGIN_OK", result.get("message"))


@admin_bp.route("/validate_token", methods=["POST"])
def validate_token_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    username = data.get("username", "").strip()
    if not username:
        return api_response(False, "MISSING_USERNAME", "Kullanici adi belirtilmedi")

    tokens = load_tokens()
    for token in tokens:
        if token.get("username") == username:
            is_valid = validate_token(token)
            if not is_valid:
                if token.get("is_active", False):
                    from datetime import datetime

                    token["is_active"] = False
                    token["logout_reason"] = "Bu hesabın oturumu Instagram'dan çıkış yapıldı veya doğrulamaya düştü."
                    token["logout_time"] = str(datetime.now())
                    save_tokens(tokens)
            else:
                if not token.get("is_active", False):
                    token["is_active"] = True
                    if "logout_reason" in token:
                        del token["logout_reason"]
                    if "logout_time" in token:
                        del token["logout_time"]
                    save_tokens(tokens)
            return api_response(
                True,
                "VALIDATED",
                "Token dogrulandi",
                extra={"is_valid": is_valid, "is_active": token.get("is_active", False)},
            )

    return api_response(False, "NOT_FOUND", "Token bulunamadi", http_status=404)


@admin_bp.route("/get_exemptions", methods=["GET"])
def get_exemptions():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    search = request.args.get("search", "").strip() or None
    page = request.args.get("page", type=int)
    page_size = request.args.get("page_size", type=int)
    grouped, total_groups, total_users = load_exemptions_grouped(
        search=search, page=page, page_size=page_size
    )
    return api_response(
        True,
        "OK",
        "Basarili",
        extra={
            "groups": grouped,
            "total": total_users,
            "total_groups": total_groups,
            "page": page or 1,
            "page_size": page_size or 0,
        },
    )


@admin_bp.route("/add_exemption", methods=["POST"])
def add_exemption_admin():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    post_link = _normalize_post_link(data.get("post_link"))
    username = str(data.get("username", "")).strip().lstrip("@")

    if not post_link or not username:
        return api_response(False, "MISSING_FIELDS", "post_link ve username zorunlu")

    if not is_valid_post_link(post_link):
        return api_response(False, "INVALID_LINK", "Gecersiz paylasim linki")

    exemptions = load_exemptions()
    current_users = set(exemptions.get(post_link, []))
    already_exists = username in current_users
    current_users.add(username)
    exemptions[post_link] = sorted(current_users)
    save_exemptions(exemptions)

    message = f"@{username} zaten izinli" if already_exists else f"@{username} izinli listesine eklendi"
    return api_response(True, "OK", message)


@admin_bp.route("/delete_exemption", methods=["POST"])
def delete_exemption_admin():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    post_link = _normalize_post_link(data.get("post_link"))
    username = str(data.get("username", "")).strip().lstrip("@")

    if not post_link or not username:
        return api_response(False, "MISSING_FIELDS", "post_link ve username zorunlu")

    exemptions = load_exemptions()
    users = exemptions.get(post_link, [])
    updated_users = [user for user in users if user != username]

    if len(updated_users) == len(users):
        return api_response(False, "NOT_FOUND", "Kayit bulunamadi", http_status=404)

    if updated_users:
        exemptions[post_link] = updated_users
    else:
        exemptions.pop(post_link, None)

    save_exemptions(exemptions)
    return api_response(True, "DELETED", f"@{username} izinli listesinden kaldirildi")


@admin_bp.route("/delete_exemptions_by_link", methods=["POST"])
def delete_exemptions_by_link_admin():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    post_link = _normalize_post_link(data.get("post_link"))
    if not post_link:
        return api_response(False, "MISSING_LINK", "post_link zorunlu")

    exemptions = load_exemptions()
    if post_link not in exemptions:
        return api_response(False, "NOT_FOUND", "Link kaydi bulunamadi", http_status=404)

    removed_count = len(exemptions.get(post_link, []))
    exemptions.pop(post_link, None)
    save_exemptions(exemptions)
    return api_response(True, "DELETED", f"{removed_count} izinli kullanici kaldirildi")


@admin_bp.route("/get_global_exemptions", methods=["GET"])
def get_global_exemptions():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    exemptions = load_global_exemptions()
    return api_response(True, "OK", "Basarili", extra={"exemptions": exemptions})


@admin_bp.route("/add_global_exemption", methods=["POST"])
def add_global_exemption_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    if not username:
        return api_response(False, "INVALID", "Kullanici adi gerekli")
    success = add_global_exemption(username)
    if success:
        return api_response(True, "ADDED", f"@{username} muaf listeye eklendi")
    return api_response(False, "ERROR", "Muaf kullanici eklenemedi")


@admin_bp.route("/remove_global_exemption", methods=["POST"])
def remove_global_exemption_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    if not username:
        return api_response(False, "INVALID", "Kullanici adi gerekli")
    success = remove_global_exemption(username)
    if success:
        return api_response(True, "REMOVED", f"@{username} muaf listeden kaldirildi")
    return api_response(False, "ERROR", "Muaf kullanici kaldirilamadi")


@admin_bp.route("/get_audit_logs", methods=["GET"])
def get_audit_logs_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    limit = request.args.get("limit", type=int) or 100
    limit = min(max(1, limit), 500)
    logs = get_audit_logs(limit=limit)
    return api_response(True, "OK", "Basarili", extra={"logs": logs})


@admin_bp.route("/get_stats", methods=["GET"])
def get_stats():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    all_tokens = load_tokens(include_deleted=False)
    total = len(all_tokens)
    active = sum(1 for t in all_tokens if t.get("is_active"))
    deleted_count = count_tokens(include_deleted=True) - total
    relogin_7d = get_audit_relogin_count(days=7)
    return api_response(
        True,
        "OK",
        "Basarili",
        extra={
            "total_tokens": total,
            "active_tokens": active,
            "inactive_tokens": total - active,
            "deleted_tokens": deleted_count,
            "relogin_last_7_days": relogin_7d,
        },
    )


@admin_bp.route("/import_tokens", methods=["POST"])
def import_tokens_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    if "file" not in request.files:
        return api_response(False, "NO_FILE", "Dosya bulunamadı")
    file = request.files["file"]
    if file.filename == "":
        return api_response(False, "NO_FILE", "Dosya seçilmedi")
    if not file.filename.endswith(".json"):
        return api_response(False, "INVALID_FORMAT", "Sadece JSON dosyaları desteklenir")
    try:
        content = file.read().decode("utf-8")
        data = json.loads(content)
        new_tokens = data.get("tokens", [])
        if not new_tokens:
            return api_response(False, "NO_TOKENS", "JSON içinde geçerli 'tokens' listesi bulunamadı")
            
        current_tokens = load_tokens(include_deleted=True)
        added_count = 0
        updated_count = 0
        
        for new_t in new_tokens:
            username = new_t.get("username")
            if not username:
                continue
            
            # İçeri aktarılan tokeni her zaman zorla "Aktif" yap ve varsa çıkış hatalarını temizle
            new_t["is_active"] = True
            new_t.pop("logout_reason", None)
            new_t.pop("logout_time", None)
            new_t.pop("deleted_at", None)
                
            replaced = False
            for idx, existing_t in enumerate(current_tokens):
                if existing_t.get("username") == username:
                    current_tokens[idx] = new_t
                    replaced = True
                    updated_count += 1
                    break
            if not replaced:
                current_tokens.append(new_t)
                added_count += 1
                
        save_tokens(current_tokens)
        return api_response(True, "IMPORTED", f"{added_count} yeni eklendi, {updated_count} güncellendi")
    except Exception as e:
        logger.error("Token import hatası: %s", e)
        return api_response(False, "ERROR", f"İçeri aktarma hatası: {e}", http_status=500)


@admin_bp.route("/export_tokens", methods=["GET"])
def export_tokens_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    from flask import Response
    import csv
    import io
    fmt = request.args.get("format", "json").lower()
    include_deleted = request.args.get("include_deleted", "").lower() == "true"
    tokens = load_tokens(include_deleted=include_deleted)
    
    if fmt == "csv":
        if not tokens:
            output = io.StringIO()
            w = csv.writer(output)
            w.writerow(["username", "full_name", "is_active", "added_at"])
            body = output.getvalue()
        else:
            output = io.StringIO()
            w = csv.DictWriter(output, fieldnames=tokens[0].keys())
            w.writeheader()
            w.writerows(tokens)
            body = output.getvalue()
        return Response(body, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=tokens.csv"})
    body = json.dumps({"tokens": tokens}, ensure_ascii=False, indent=2)
    return Response(body, mimetype="application/json", headers={"Content-Disposition": "attachment; filename=tokens.json"})


@admin_bp.route("/export_exemptions", methods=["GET"])
def export_exemptions_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    from flask import Response
    import csv
    import io
    fmt = request.args.get("format", "json").lower()
    exemptions = load_exemptions()
    if fmt == "csv":
        output = io.StringIO()
        w = csv.writer(output)
        w.writerow(["post_link", "username"])
        for post_link, usernames in exemptions.items():
            for u in usernames:
                w.writerow([post_link, u])
        body = output.getvalue()
        return Response(body, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=exemptions.csv"})
    list_export = [{"post_link": k, "usernames": v} for k, v in exemptions.items()]
    body = json.dumps({"exemptions": list_export}, ensure_ascii=False, indent=2)
    return Response(body, mimetype="application/json", headers={"Content-Disposition": "attachment; filename=exemptions.json"})


@admin_bp.route("/get_groups", methods=["GET"])
def get_groups_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
        
    token_record = get_working_active_token()
    if not token_record:
        return api_response(False, "ERROR", "Aktif token bulunamadi.")
        
    res = fetch_group_threads(token_record)
    if not res.get("ok"):
        return api_response(False, "ERROR", "Gruplar cekilemedi.")
        
    return api_response(True, "OK", "Gruplar cekildi.", extra={"groups": res.get("groups", [])})


@admin_bp.route("/get_automations", methods=["GET"])
def get_automations_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
        
    automations = load_automations()
    return api_response(True, "OK", "Otomasyonlar", extra={"automations": automations})


@admin_bp.route("/save_automation", methods=["POST"])
def save_automation_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
        
    data = request.get_json() or {}
    thread_id = data.get("thread_id")
    is_active = data.get("is_active", False)
    group_name = data.get("group_name", "Bilinmeyen Grup")
    notify_username = data.get("notify_username", "seghob").strip().lstrip("@")
    control_method = data.get("control_method", "all_members")
    
    if not thread_id:
        return api_response(False, "ERROR", "Thread ID zorunlu.")
        
    automations = load_automations()
    automations[str(thread_id)] = {
        "is_active": is_active,
        "group_name": group_name,
        "notify_username": notify_username,
        "control_method": control_method,
    }
    save_automations(automations)
    return api_response(True, "OK", "Otomasyon ayarlari kaydedildi.")


@admin_bp.route("/trigger_automation", methods=["POST"])
def trigger_automation_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    thread_id = data.get("thread_id")
    if not thread_id:
        return api_response(False, "ERROR", "Thread ID zorunlu.")

    import threading
    from app_core.automation import run_automation_for_thread
    t = threading.Thread(target=run_automation_for_thread, args=(str(thread_id),), daemon=True)
    t.start()
    return api_response(True, "OK", f"Otomasyon tetiklendi (arka planda calisuyor): {thread_id}")


@admin_bp.route("/test_admin_notification", methods=["POST"])
def test_admin_notification_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    group_name = data.get("group_name", "Test Grubu")
    notify_username = data.get("notify_username", "seghob")

    if not notify_username:
        return api_response(False, "ERROR", "Bildirim gonderilecek kullanici adi yok.")

    token_record = get_working_active_token()
    if not token_record:
        return api_response(False, "ERROR", "Aktif token bulunamadi.")

    import datetime, pytz
    from app_core.storage import get_global_automation_settings
    from app_core.automation import _get_user_id_by_username, _send_dm_to_user

    global_settings = get_global_automation_settings()
    admin_notify_template = global_settings.get("admin_notify_template", "✅ Otomasyon tamamlandı!\n\n📌 Grup: {grup_ismi}\n🔗 Post: {post_url}\n\n👥 Toplam üye: {toplam_uye}\n❌ Eksik: {eksik_sayisi}\n⏰ Saat: {saat}")
    
    post_url = "https://www.instagram.com/p/TEST_POST/"
    toplam_uye_str = "150"
    eksik_sayisi_str = "5"
    saat_str = datetime.datetime.now(pytz.timezone('Europe/Istanbul')).strftime('%H:%M')
    post_tarihi_str = f"{datetime.datetime.now(pytz.timezone('Europe/Istanbul')).strftime('%d %B %H:%M')}"
    eksik_listesi_str = "@kullanici1\n@kullanici2\n@kullanici3\n@kullanici4\n@kullanici5"

    notify_text = admin_notify_template.replace("{grup_ismi}", str(group_name)) \
        .replace("[Grubun İsmi]", str(group_name)) \
        .replace("{post_url}", str(post_url)) \
        .replace("{toplam_uye}", toplam_uye_str) \
        .replace("{eksik_sayisi}", eksik_sayisi_str) \
        .replace("{saat}", saat_str) \
        .replace("{post_tarihi}", post_tarihi_str) \
        .replace("{eksik_listesi}", eksik_listesi_str)
        
    template_raw = global_settings.get(
        "template",
        "@everyone merhaba arkadaşlar eksik listesindeki tüm arkadaşlarımıza dm yazdık dönüş yapmayanları aramızdan çıkarmak durumunda kalacağız."
    )
    # _format_template logic replicated here for the template:
    template_formatted = template_raw.replace("{grup_ismi}", str(group_name)) \
        .replace("[Grubun İsmi]", str(group_name)) \
        .replace("{post_url}", str(post_url)) \
        .replace("{toplam_uye}", toplam_uye_str) \
        .replace("{eksik_sayisi}", eksik_sayisi_str) \
        .replace("{saat}", saat_str) \
        .replace("{post_tarihi}", post_tarihi_str)
        
    combined_msg = f"{eksik_listesi_str}\n\neksikler\n\n{template_formatted}"
        
    user_id = _get_user_id_by_username(notify_username, token_record)
    if not user_id:
        return api_response(False, "ERROR", f"@{notify_username} kullanici adi bulunamadi veya erisilemiyor.")
        
    _send_dm_to_user(user_id, combined_msg, token_record)
    import time
    time.sleep(3)
    _send_dm_to_user(user_id, notify_text, token_record)
    return api_response(True, "OK", "Test bildirimi ve ayri kopyalanabilir grup mesaji gonderildi.")

@admin_bp.route("/live_test_automation", methods=["POST"])
def live_test_automation_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
        
    from app_core.automation import load_automations, run_automation_for_thread
    import threading
    
    autos = load_automations()
    active_threads = [tid for tid, cfg in autos.items() if cfg.get("is_active")]
    
    if not active_threads:
        return api_response(False, "ERROR", "Sistemde aktif edilmiş hiçbir otomasyon grubu bulunamadı.")
        
    for tid in active_threads:
        t = threading.Thread(target=run_automation_for_thread, args=(str(tid), True), daemon=True)
        t.start()
        
    return api_response(True, "OK", f"{len(active_threads)} aktif grup için CANLI TEST başlatıldı. Gruplara veya üyelere mesaj gitmeyecek, sadece admine eksik raporu iletilecek.")
@admin_bp.route("/unsend_messages", methods=["POST"])
def unsend_messages_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    thread_id = data.get("thread_id")
    if not thread_id:
        return api_response(False, "ERROR", "Thread ID zorunlu.")

    token_record = get_working_active_token()
    if not token_record:
        return api_response(False, "ERROR", "Aktif token bulunamadi.")

    # Bot'un kendi mesajlarını çek
    items_res = fetch_own_thread_items(token_record, thread_id, limit=30)
    if not items_res.get("ok"):
        return api_response(False, "ERROR", f"Mesajlar cekilemedi: {items_res.get('error')}")

    items = items_res.get("items", [])
    if not items:
        return api_response(True, "OK", "Geri alinacak mesaj bulunamadi.", extra={"deleted": 0})

    import time
    deleted = 0
    failed = 0
    for item in items:
        item_id = item.get("item_id")
        if not item_id:
            continue
        res = delete_thread_item(token_record, thread_id, item_id)
        if res.get("ok"):
            deleted += 1
        else:
            failed += 1
        time.sleep(0.8)  # rate limit

    return api_response(
        True, "OK",
        f"{deleted} mesaj geri alindi, {failed} basarisiz.",
        extra={"deleted": deleted, "failed": failed}
    )


@admin_bp.route("/get_global_automation_status", methods=["GET"])
def get_global_automation_status_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    from app_core.storage import get_global_automation_status
    status = get_global_automation_status()
    return api_response(True, "OK", "Basarili", extra={"is_active": status})


@admin_bp.route("/toggle_global_automation", methods=["POST"])
def toggle_global_automation_route():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    from app_core.storage import get_global_automation_status, set_global_automation_status
    current = get_global_automation_status()
    new_status = not current
    set_global_automation_status(new_status)
    
    if new_status:
        from app_core.automation import start_automation
        start_automation()
        
    status_str = "aktif" if new_status else "pasif"
    return api_response(True, "OK", f"Global otomasyon {status_str} yapildi.", extra={"is_active": new_status})


@admin_bp.route("/get_global_automation_settings", methods=["GET"])
def get_global_automation_settings_route():
    auth_error = _require_admin()
    if auth_error: return auth_error
    from app_core.storage import get_global_automation_settings
    settings = get_global_automation_settings()
    return api_response(True, "OK", "Ayarlar", extra={"settings": settings})


@admin_bp.route("/save_global_automation_settings", methods=["POST"])
def save_global_automation_settings_route():
    auth_error = _require_admin()
    if auth_error: return auth_error
    data = request.get_json() or {}
    from app_core.storage import set_global_automation_settings
    settings = {
        "times": data.get("times", "23:59"),
        "send_to_group": data.get("send_to_group", True),
        "template": data.get("template", ""),
        "send_dm_to_missing": data.get("send_dm_to_missing", True),
        "dm_template": data.get("dm_template", ""),
        "admin_notify_template": data.get("admin_notify_template", "")
    }
    set_global_automation_settings(settings)
    return api_response(True, "OK", "Global otomasyon ayarlari kaydedildi.")


@admin_bp.route("/spam_report/<thread_id>", methods=["GET"])
def get_spam_report_route(thread_id):
    auth_error = _require_admin()
    if auth_error: return auth_error
    from app_core.storage import get_group_spam_report
    report = get_group_spam_report(thread_id)
    return api_response(True, "OK", "Spam raporu", extra={"report": report})


@admin_bp.route("/user_comments/<thread_id>/<username>", methods=["GET"])
def get_user_comments_route(thread_id, username):
    auth_error = _require_admin()
    if auth_error: return auth_error
    from app_core.storage import get_user_comment_details
    comments = get_user_comment_details(thread_id, username)
    return api_response(True, "OK", "Kullanici yorum detaylari", extra={"comments": comments})


@admin_bp.route("/get_post_details", methods=["GET"])
def get_post_details_route():
    auth_error = _require_admin()
    if auth_error: return auth_error
    
    post_link = request.args.get("post_link", "").strip()
    if not post_link:
        return api_response(False, "Link eksik")
        
    try:
        from donustur import donustur
        from app_core.instagram_api import get_post_details
        media_id = donustur(post_link)
        if not media_id:
            return api_response(False, "Geçersiz link")
            
        token_record = get_working_active_token()
        if not token_record:
            return api_response(False, "Aktif token bulunamadı")
            
        post_details = get_post_details(media_id, token_record)
        if not post_details:
            return api_response(False, "Post detayları alınamadı")
            
        return api_response(True, "OK", "Post detayları", extra={"details": post_details})
    except Exception as e:
        return api_response(False, str(e))


