import html
import logging
import random
import time

from flask import Blueprint, jsonify, render_template, request

from donustur import donustur
from log_in import giris_yap, LoginError

from app_core.instagram_api import fetch_group_members, fetch_group_threads, fetch_group_media, get_post_sender
from app_core.storage import load_exemptions, save_exemptions, load_global_exemptions
from app_core.token_service import fetch_comments_with_failover, fetch_likers_with_failover, get_working_active_token, upsert_login_token

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)


@main_bp.route("/api/get_groups", methods=["GET"])
def get_groups():
    token = get_working_active_token()
    if not token:
        return jsonify({"ok": False, "error": "Aktif token bulunamadi"})
    
    result = fetch_group_threads(token)
    return jsonify(result)


@main_bp.route("/api/get_group_members/<thread_id>", methods=["GET"])
def get_group_members(thread_id):
    token = get_working_active_token()
    if not token:
        return jsonify({"ok": False, "error": "Aktif token bulunamadi"})
    
    result = fetch_group_members(token, thread_id)
    return jsonify(result)


@main_bp.route("/api/get_group_posts/<thread_id>", methods=["GET"])
def get_group_posts(thread_id):
    date_filter = request.args.get("date", "today")
    
    import datetime
    import pytz
    tz = pytz.timezone('Europe/Istanbul')
    now = datetime.datetime.now(tz)
    
    if date_filter == "yesterday":
        target_date = now - datetime.timedelta(days=1)
    else:
        target_date = now
    
    token = get_working_active_token()
    if not token:
        return jsonify({"ok": False, "error": "Aktif token bulunamadi"})
    
    result = fetch_group_media(token, thread_id, target_date)
    return jsonify(result)


def get_exempted_users(post_link):
    exemptions = load_exemptions()
    post_link_decoded = html.unescape(post_link)
    raw_usernames = exemptions.get(post_link_decoded, [])
    return {normalize_username(u) for u in raw_usernames}


def normalize_username(username):
    if not username:
        return ""
    username = username.strip().lower()
    return username.lstrip("@")


def get_global_exempted_users():
    exemptions = load_global_exemptions()
    return {normalize_username(e["username"]) for e in exemptions}


@main_bp.route("/result")
def result_page():
    return render_template("form.html")


@main_bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        active_working_token = get_working_active_token()
        if not active_working_token:
            return render_template(
                "form.html",
                token_error_message="Tum hesaplar cikis yapmis gorunuyor. Lutfen admin panelden gecerli bir token girin.",
            )

        link = request.form.get("post_link", "").strip()
        if not link:
            return render_template("form.html", token_error_message="Paylasim linki zorunludur.")

        # Birden fazla link desteği
        links_raw = link.split("\n")
        all_commented = set()
        user_missing_posts = {}  # {username: [post_link1, post_link2, ...]}
        user_comments_map = {}  # {username: [comment_text1, comment_text2, ...]}
        grup_uye = request.form.get("grup_uye", "")
        grup_uye_kullanicilar = {normalize_username(u) for u in grup_uye.split() if u.strip()}
        link_results = []
        
        # Token'i once al ve tum linklerde ayni tokeni kullan
        working_token = get_working_active_token(skip_validation=True)
        if not working_token:
            return render_template(
                "form.html",
                token_error_message="Aktif token bulunamadi veya tum tokenler expired. Lutfen admin panelden yeni token ekleyin.",
            )
        
        # post_senders: "url|sender" formatında
        post_senders_raw = request.form.getlist("post_senders")
        check_likes = request.form.get("check_likes") == "on"
        post_senders = {}
        for ps in post_senders_raw:
            if "|" in ps:
                url, sender = ps.rsplit("|", 1)
                url = url.strip().rstrip('/')  # Remove trailing slash for matching
                post_senders[url] = normalize_username(sender)
        logger.info(f"DEBUG: post_senders parsed: {post_senders}")
        
        link_count = 0
        for link_raw in links_raw:
            link_single = link_raw.strip().rstrip('/')
            if not link_single:
                continue
            
            # Her link arasinda random bekleme (insan davranisi)
            if link_count > 0:
                delay = round(random.uniform(4.0, 9.0) + random.random(), 2)
                if delay > 10.0:
                    delay = round(delay - 1.0, 2)
                logger.info(f"Bekleme: {delay} saniye...")
                time.sleep(delay)
            
            link_count += 1
            
            media_id = donustur(link_single)
            if media_id is None:
                link_results.append({
                    "post_link": link_single,
                    "eksikler": list(grup_uye_kullanicilar),
                    "commenters": [],
                    "error": "Gecersiz link"
                })
                continue

            if check_likes:
                all_result = fetch_likers_with_failover(media_id, token_record=working_token)
            else:
                all_result = fetch_comments_with_failover(media_id, token_record=working_token)
            
            if isinstance(all_result, dict) and all_result.get("rate_limited"):
                return render_template(
                    "form.html",
                    token_error_message="Cok fazla istek; Instagram gecici olarak sinir koydu. Lutfen bir sure bekleyin.",
                )
            
            # Likers result is a set of usernames, Comments result is a list of tuples (username, text)
            if check_likes:
                commenters_normalized = {normalize_username(u) for u in (all_result if isinstance(all_result, set) else all_result.get("usernames", set()))}
            else:
                comments_list = all_result if isinstance(all_result, list) else all_result.get("comments", [])
                commenters_normalized = set()
                for uname, text in comments_list:
                    norm_uname = normalize_username(uname)
                    commenters_normalized.add(norm_uname)
                    if norm_uname not in user_comments_map:
                        user_comments_map[norm_uname] = []
                    user_comments_map[norm_uname].append(text)
            
            all_commented.update(commenters_normalized)
            
            # Get global + per-post exemptions
            global_exempted = get_global_exempted_users()
            izinli_uyeler = get_exempted_users(link_single)
            all_exempted_for_link = izinli_uyeler | global_exempted
            
            # Postun göndericisini frontend'den al, yoksa API'den dene
            post_sender = post_senders.get(link_single)
            logger.info(f"DEBUG: link={link_single}, post_sender from form={post_sender}")
            if not post_sender:
                post_sender = get_post_sender(media_id, active_working_token)
                if post_sender:
                    post_sender = normalize_username(post_sender)
            
            if post_sender:
                all_exempted_for_link.add(post_sender)
            
            eksikler = grup_uye_kullanicilar - all_exempted_for_link - commenters_normalized
            logger.info(f"DEBUG: grup_uye={grup_uye_kullanicilar}, exempted={all_exempted_for_link}, commenters={commenters_normalized}, eksikler={eksikler}")
            tamamlayanlar = grup_uye_kullanicilar - all_exempted_for_link - eksikler
            
            link_results.append({
                "post_link": link_single,
                "eksikler": list(eksikler),
                "commenters": list(tamamlayanlar),
                "sender": post_sender,
            })
            
            # Her eksik kullanıcının hangi linklerde eksik olduğunu kaydet
            for eksik in eksikler:
                if eksik not in user_missing_posts:
                    user_missing_posts[eksik] = []
                user_missing_posts[eksik].append(link_single)
        
        if not link_results:
            return render_template("form.html", token_error_message="Gecerli link bulunamadi.")

        # Kopya yorum tespiti
        duplicate_comment_users = set()
        for user, comments in user_comments_map.items():
            if len(comments) > 1:
                # Eger ayni yorum metni birden fazla kez kullanilmissa
                seen = set()
                for c in comments:
                    if not c: continue
                    c_clean = c.strip().lower()
                    if c_clean in seen:
                        duplicate_comment_users.add(user)
                        break
                    seen.add(c_clean)

        # Collect all exempted users from all links + global exemptions
        global_exempted = get_global_exempted_users()
        all_exempted = global_exempted.copy()
        eksikler_all = set()
        for lr in link_results:
            all_exempted.update(get_exempted_users(lr["post_link"]))
            eksikler_all.update(lr.get("eksikler", []))
        
        # tamamlayanlar_genel = people who have commented on any of the links
        tamamlayanlar_genel = grup_uye_kullanicilar - all_exempted - eksikler_all
        
        # Format user_missing_posts for template
        user_missing_formatted = {user: posts for user, posts in user_missing_posts.items()}
        
        return render_template("result.html", 
            links=link_results,
            all_commented=list(tamamlayanlar_genel),
            group=list(grup_uye_kullanicilar),
            user_missing_posts=user_missing_formatted,
            duplicate_comment_users=list(duplicate_comment_users),
            check_likes=check_likes)

    refresh = request.args.get("refresh") == "1"
    link_param = request.args.get("link", "")
    group_param = request.args.get("group", "")
    return render_template("form.html", refresh=refresh, link_param=link_param, group_param=group_param)


@main_bp.route("/add_exemption", methods=["POST"])
def add_exemption():
    try:
        data = request.get_json() or {}
        post_link = data.get("post_link")
        username = data.get("username")

        if not post_link or not username:
            return jsonify({"success": False, "message": "Paylasim linki ve kullanici adi gerekli"}), 400

        post_link_decoded = html.unescape(post_link)
        exemptions = load_exemptions()

        if post_link_decoded not in exemptions:
            exemptions[post_link_decoded] = []

        if username not in exemptions[post_link_decoded]:
            exemptions[post_link_decoded].append(username)
            save_exemptions(exemptions)

        return jsonify({"success": True, "message": f"@{username} izinli kullanicilar listesine eklendi"})
    except Exception as error:
        logger.error("Izinli ekleme hatasi: %s", error)
        return jsonify({"success": False, "message": f"Hata: {error}"}), 500


@main_bp.route("/token_al")
def token_page():
    return render_template("token.html")


@main_bp.route("/giris_yaps", methods=["POST"])
def login_and_get_token():
    username = request.form.get("kullanici_adi", "").strip()
    password = request.form.get("sifre", "").strip()
    android_id = request.form.get("android_id", "").strip()
    user_agent = request.form.get("user_agent", "").strip()
    device_id = request.form.get("device_id", "").strip()

    if not username or not password or not android_id or not user_agent or not device_id:
        return jsonify({"token": None, "message": "kullanici_adi, sifre, android_id, user_agent ve device_id zorunludur"}), 400

    try:
        token_value, android_id, user_agent, device_id = giris_yap(
            username, password, android_id, user_agent, device_id
        )
    except LoginError as error:
        logger.error("Login hatasi: @%s | %s | Tip: %s", username, error.message, error.error_type)
        return jsonify({
            "token": None,
            "message": error.message,
            "error_type": error.error_type,
        }), 400
    except Exception as error:
        logger.error("Beklenmeyen login hatasi: @%s | %s", username, error)
        return jsonify({
            "token": None,
            "message": f"Giris sirasinda hata olustu: {error}",
            "error_type": "UNKNOWN",
        }), 500

    if token_value:
        upsert_login_token(username, password, token_value, android_id, user_agent, device_id)

    return jsonify(
        {
            "token": token_value,
            "android_id_yeni": android_id,
            "user_agent": user_agent,
            "device_id": device_id,
        }
    )
