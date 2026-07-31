import html
import logging
import random
import time
import datetime
import pytz
import threading
import json
from flask import Blueprint, jsonify, render_template, request, session, redirect, url_for
from donustur import donustur
from log_in import giris_yap, LoginError

from app_core.instagram_api import get_post_sender, get_media_taken_at, get_post_details
from app_core.storage import load_exemptions, save_exemptions, load_global_exemptions, add_audit_log, _connect
from app_core.token_service import (
    fetch_comments_with_failover,
    fetch_likers_with_failover,
    get_working_active_token,
    upsert_login_token,
    fetch_group_threads_with_failover,
    fetch_group_members_with_failover,
    fetch_group_media_with_failover
)

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)

def get_db_value(key):
    conn = _connect()
    try:
        row = conn.execute("SELECT value FROM key_value WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None
    except Exception as e:
        logger.error(f"get_db_value error for {key}: {e}")
        return None
    finally:
        conn.close()

def set_db_value(key, value):
    conn = _connect()
    try:
        conn.execute("INSERT OR REPLACE INTO key_value (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"set_db_value error for {key}: {e}")
        return False
    finally:
        conn.close()


@main_bp.route("/api/get_groups", methods=["GET"])
def get_groups():
    result = fetch_group_threads_with_failover()
    return jsonify(result)


@main_bp.route("/api/get_group_members/<thread_id>", methods=["GET"])
def get_group_members(thread_id):
    result = fetch_group_members_with_failover(thread_id)
    return jsonify(result)


@main_bp.route("/api/get_group_posts/<thread_id>", methods=["GET"])
def get_group_posts(thread_id):
    date_filter = request.args.get("date", "today")
    tz = pytz.timezone('Europe/Istanbul')
    now = datetime.datetime.now(tz)
    
    if date_filter == "yesterday":
        target_date = now - datetime.timedelta(days=1)
    else:
        target_date = now
    
    result = fetch_group_media_with_failover(thread_id, target_date)
    return jsonify(result)


def get_exempted_users(post_link):
    exemptions = load_exemptions()
    post_link_decoded = html.unescape(post_link)
    raw_usernames = exemptions.get(post_link_decoded, [])
    return {normalize_username(u) for u in raw_usernames}
def normalize_username(username):
    if not username:
        return ""
    import unicodedata
    username = username.strip().replace("İ", "i").replace("I", "i").replace("ı", "i")
    username = username.lower()
    username = unicodedata.normalize("NFKD", username)
    username = "".join([c for c in username if not unicodedata.combining(c)])
    username = username.replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
    return username.lstrip("@")

def get_global_exempted_users():
    exemptions = load_global_exemptions()
    return {normalize_username(e["username"]) for e in exemptions}


def has_emoji(text):
    if not text:
        return False
    for char in text:
        cp = ord(char)
        if (0x1F600 <= cp <= 0x1F64F) or \
           (0x1F300 <= cp <= 0x1F5FF) or \
           (0x1F680 <= cp <= 0x1F6FF) or \
           (0x1F1E0 <= cp <= 0x1F1FF) or \
           (0x2600 <= cp <= 0x27BF) or \
           (0x1F900 <= cp <= 0x1F9FF) or \
           (0x1FA70 <= cp <= 0x1FAFF):
            return True
    return False


def clean_word_count(text):
    if not text:
        return 0
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
    cleaned_text = "".join(cleaned_chars)
    words = [w for w in cleaned_text.split() if len(w) > 0]
    return len(words)


def run_manual_control(link, grup_uye, thread_id, post_senders_raw, check_likes, only_missing=False, prev_result=None, progress_callback=None):
    active_working_token = get_working_active_token()
    if not active_working_token:
        raise ValueError("Tum hesaplar cikis yapmis gorunuyor. Lutfen admin panelden gecerli bir token girin.")

    grup_uye_kullanicilar = {normalize_username(u) for u in grup_uye.split() if u.strip()}
    
    links_raw = [l.strip().rstrip('/') for l in link.split("\n") if l.strip()]
    all_commented = set()
    user_missing_posts = {}  # {username: [post_link1, post_link2, ...]}
    user_comments_map = {}  # {username: [comment_text1, comment_text2, ...]}
    link_results = []
    
    initial_token = get_working_active_token(skip_validation=True)
    if not initial_token:
        raise ValueError("Aktif token bulunamadi veya tum tokenler expired. Lutfen admin panelden yeni token ekleyin.")

    post_senders = {}
    for ps in post_senders_raw:
        if "|" in ps:
            url, sender = ps.rsplit("|", 1)
            url = url.strip().rstrip('/')  # Remove trailing slash for matching
            post_senders[url] = normalize_username(sender)
    
    link_count = 0
    for link_single in links_raw:
        # Eğer hızlı güncelleme aktifse ve bu linkin eksikleri önceden tamamlandıysa, sorguyu atla
        if only_missing and prev_result:
            prev_link_res = next((lr for lr in prev_result.get("links", []) if lr.get("post_link", "").strip().rstrip('/') == link_single), None)
            if prev_link_res and not prev_link_res.get("eksikler"):
                # Bu link zaten tamamlanmış, eski sonucu koru
                link_results.append(prev_link_res)
                link_count += 1
                if progress_callback:
                    progress_callback(link_count, len(links_raw), f"Gönderi {link_count}/{len(links_raw)} atlandı (Tamamlanmış)")
                continue

        link_count += 1
        if progress_callback:
            progress_callback(link_count, len(links_raw), f"Gönderi {link_count}/{len(links_raw)} sorgulanıyor...")
            
        # Her link arasinda random bekleme (insan davranisi)
        if link_count > 1:
            delay = round(random.uniform(4.0, 9.0) + random.random(), 2)
            if delay > 10.0:
                delay = round(delay - 1.0, 2)
            logger.info(f"Bekleme: {delay} saniye...")
            time.sleep(delay)
        
        working_token = get_working_active_token(skip_validation=True)
        if not working_token:
            raise ValueError("Aktif token bulunamadi veya tum tokenler expired. Lutfen admin panelden yeni token ekleyin.")
        
        media_id = donustur(link_single)
        if media_id is None:
            link_results.append({
                "post_link": link_single,
                "eksikler": list(grup_uye_kullanicilar),
                "commenters": [],
                "error": "Gecersiz link"
            })
            continue

        # Yüklenme tarihini ve göndericiyi kontrol et
        taken_at, sender = get_media_taken_at(media_id, working_token)
        if taken_at:
            gmt3 = pytz.timezone('Europe/Istanbul')
            today_date = datetime.datetime.now(gmt3).date()
            yesterday_date = today_date - datetime.timedelta(days=1)
            
            dt_taken = datetime.datetime.utcfromtimestamp(taken_at)
            dt_taken = pytz.utc.localize(dt_taken).astimezone(gmt3)
            
            # Akıllı Tarih Kontrolü:
            # 1. Takvim gününe göre bugün veya dün yüklenmişse doğrudan kabul et.
            # 2. VEYA gönderi son 36 saat içinde yüklenmişse (gece yarısı/saat dilimi sapmalarını tolere etmek için) kabul et.
            now_gmt3 = datetime.datetime.now(gmt3)
            diff_hours = (now_gmt3 - dt_taken).total_seconds() / 3600.0
            
            is_valid_date = (dt_taken.date() in (today_date, yesterday_date)) or (diff_hours <= 36.0)
            
            if not is_valid_date:
                link_results.append({
                    "post_link": link_single,
                    "sender": sender,
                    "eksikler": [],
                    "commenters": [],
                    "error": "Bu gönderi çok eski (yalnızca dün veya bugün yüklenen gönderiler denetlenebilir)."
                })
                continue
        else:
            logger.warning("Post yuklenme tarihi alinamadi: %s", link_single)
        # Post detaylarını API'den çek (Beğeni, Yorum sayısı, Gönderen adı vb.)
        post_details = get_post_details(media_id, working_token) or {}
        
        post_sender = post_senders.get(link_single)
        if not post_sender:
            post_sender = post_details.get("sender")
            if post_sender:
                post_sender = normalize_username(post_sender)
                
        # Get global + per-post exemptions
        global_exempted = get_global_exempted_users()
        izinli_uyeler = get_exempted_users(link_single)
        all_exempted_for_link = izinli_uyeler | global_exempted
        if post_sender:
            all_exempted_for_link.add(post_sender)

        commenters_normalized = set()
        
        if check_likes:
            like_count = post_details.get("like_count", 0)
            if like_count > 90:
                logger.info(f"Post {link_single} has {like_count} likes (> 90). Skipping check.")
                link_results.append({
                    "post_link": link_single,
                    "eksikler": [],
                    "commenters": [],
                    "sender": post_sender,
                    "owner_fullname": post_details.get("owner_fullname"),
                    "like_count": like_count,
                    "comment_count": post_details.get("comment_count", 0),
                    "caption": post_details.get("caption", ""),
                    "error": f"Bu gönderi 90'dan fazla beğeni aldığı için ({like_count} beğeni) kontrol edilmedi."
                })
                continue

        if check_likes:
            all_result = fetch_likers_with_failover(media_id, token_record=working_token)
            commenters_normalized = {normalize_username(u) for u in (all_result if isinstance(all_result, set) else all_result.get("usernames", set()))}
        else:
            all_result = fetch_comments_with_failover(media_id, token_record=working_token)
            comments_list = all_result if isinstance(all_result, list) else all_result.get("comments", [])
            from app_core.nlp_scorer import calculate_comment_spam_score
            from app_core.storage import save_comment_log
            import re
            
            match = re.search(r"https://www\.instagram\.com/(?:p|reel)/([^/]+)/?", link_single)
            post_code = match.group(1) if match else "unknown"
            
            for uname, text in comments_list:
                norm_uname = normalize_username(uname)
                commenters_normalized.add(norm_uname)
                if norm_uname not in user_comments_map:
                    user_comments_map[norm_uname] = []
                user_comments_map[norm_uname].append(text)
                
                if norm_uname in grup_uye_kullanicilar and thread_id:
                    is_valid = 1 if (has_emoji(text) and clean_word_count(text) >= 2) else 0
                    spam_score = calculate_comment_spam_score(norm_uname, text)
                    save_comment_log(thread_id, norm_uname, post_code, text, spam_score, is_valid)
        
        all_commented.update(commenters_normalized)
        
        eksikler = grup_uye_kullanicilar - all_exempted_for_link - commenters_normalized
        logger.info(f"DEBUG: grup_uye={grup_uye_kullanicilar}, exempted={all_exempted_for_link}, commenters={commenters_normalized}, eksikler={eksikler}")
        tamamlayanlar = grup_uye_kullanicilar - all_exempted_for_link - eksikler
        
        link_results.append({
            "post_link": link_single,
            "eksikler": list(eksikler),
            "commenters": list(tamamlayanlar),
            "sender": post_sender,
            "owner_fullname": post_details.get("owner_fullname"),
            "like_count": post_details.get("like_count", 0),
            "comment_count": post_details.get("comment_count", 0),
            "caption": post_details.get("caption", ""),
        })
        
        # Her eksik kullanıcının hangi linklerde eksik olduğunu kaydet
        for eksik in eksikler:
            if eksik not in user_missing_posts:
                user_missing_posts[eksik] = []
            user_missing_posts[eksik].append(link_single)
    
    if not link_results:
        raise ValueError("Gecerli link bulunamadi.")

    # Kopya yorum tespiti
    duplicate_comment_users = set()
    for user, comments in user_comments_map.items():
        if len(comments) > 1:
            seen = set()
            for c in comments:
                if not c: continue
                c_clean = c.strip().lower()
                if c_clean in seen:
                    duplicate_comment_users.add(user)
                    break
                seen.add(c_clean)

    # Yorum formatı/kuralı kontrolü (en az 2 kelime + emoji)
    invalid_comment_users = set()
    for user, comments in user_comments_map.items():
        has_any_valid = False
        for comment in comments:
            if has_emoji(comment) and clean_word_count(comment) >= 2:
                has_any_valid = True
                break
        if not has_any_valid:
            invalid_comment_users.add(user)

    # Collect all exempted users from all links + global exemptions
    global_exempted = get_global_exempted_users()
    all_exempted = global_exempted.copy()
    eksikler_all = set()
    for lr in link_results:
        all_exempted.update(get_exempted_users(lr["post_link"]))
        eksikler_all.update(lr.get("eksikler", []))
    
    tamamlayanlar_genel = grup_uye_kullanicilar - all_exempted - eksikler_all
    
    user_missing_formatted = {user: posts for user, posts in user_missing_posts.items()}
    
    # Audit log
    tz = pytz.timezone('Europe/Istanbul')
    now_dt = datetime.datetime.now(tz)
    now_str = now_dt.strftime('%H:%M:%S')
    for lr in link_results:
        post_link = lr["post_link"]
        eksik_sayisi = len(lr.get("eksikler", []))
        grup_sayisi = len(grup_uye_kullanicilar)
        kontrol_tipi = "Beğeni" if check_likes else "Yorum"
        add_audit_log(
            entity_type="manuel_kontrol",
            entity_id=post_link,
            action="kontrol_yapildi",
            details=f"Saat {now_str} - {kontrol_tipi} Kontrolü: {grup_sayisi} üyeden {eksik_sayisi} eksik tespit edildi."
        )

    # Cache run result in DB if thread_id
    if thread_id:
        today_str = now_dt.strftime('%Y-%m-%d')
        cache_data = {
            "links": link_results,
            "all_commented": list(tamamlayanlar_genel),
            "group": list(grup_uye_kullanicilar),
            "user_missing_posts": user_missing_formatted,
            "duplicate_comment_users": list(duplicate_comment_users),
            "invalid_comment_users": list(invalid_comment_users),
            "user_comments": user_comments_map,
            "check_likes": check_likes
        }
        from app_core.storage import set_cached_run_result
        set_cached_run_result(thread_id, today_str, cache_data)

    return {
        "links": link_results,
        "all_commented": list(tamamlayanlar_genel),
        "group": list(grup_uye_kullanicilar),
        "user_missing_posts": user_missing_formatted,
        "duplicate_comment_users": list(duplicate_comment_users),
        "invalid_comment_users": list(invalid_comment_users),
        "user_comments": user_comments_map,
        "thread_id": thread_id,
        "check_likes": check_likes
    }


def run_manual_control_async(post_code, only_missing=False):
    import json
    import traceback
    
    # 1. Girdileri veritabanından oku
    inputs_json = get_db_value(f"manual_run_inputs_{post_code}")
    if not inputs_json:
        set_db_value(f"task_status_{post_code}", json.dumps({
            "status": "failed",
            "progress": 100,
            "error": "Denetim girdileri veritabanında bulunamadı."
        }))
        return

    try:
        inputs = json.loads(inputs_json)
        link = inputs.get("link")
        grup_uye = inputs.get("grup_uye")
        thread_id = inputs.get("thread_id")
        post_senders_raw = inputs.get("post_senders_raw", [])
        check_likes = inputs.get("check_likes", False)
        
        # Hızlı güncelleme için önceki sonuçları yükle
        prev_result = None
        if only_missing:
            prev_result_json = get_db_value(f"manual_run_result_{post_code}")
            if prev_result_json:
                try:
                    prev_result = json.loads(prev_result_json)
                except Exception:
                    pass

        # İlerleme bildirim callback'i
        def progress_cb(current, total, msg):
            progress_percent = int((current / total) * 90) # Son %10'u tamamlama için ayır
            set_db_value(f"task_status_{post_code}", json.dumps({
                "status": "running",
                "progress": max(5, progress_percent),
                "message": msg,
                "error": None
            }))

        # Kontrolü çalıştır
        res_data = run_manual_control(
            link=link,
            grup_uye=grup_uye,
            thread_id=thread_id,
            post_senders_raw=post_senders_raw,
            check_likes=check_likes,
            only_missing=only_missing,
            prev_result=prev_result,
            progress_callback=progress_cb
        )
        
        # Sonucu veritabanına kaydet
        set_db_value(f"manual_run_result_{post_code}", json.dumps(res_data, ensure_ascii=False))
        
        # Görevi tamamlandı olarak işaretle
        set_db_value(f"task_status_{post_code}", json.dumps({
            "status": "completed",
            "progress": 100,
            "error": None
        }))
        
    except Exception as e:
        logger.exception("Arka planda manuel denetim hatası")
        set_db_value(f"task_status_{post_code}", json.dumps({
            "status": "failed",
            "progress": 100,
            "error": str(e)
        }))


@main_bp.route("/result/<post_code>", methods=["GET"])
def result_page_new(post_code):
    task_status_json = get_db_value(f"task_status_{post_code}")
    if not task_status_json:
        return redirect("/")
        
    try:
        task_status = json.loads(task_status_json)
    except Exception:
        return redirect("/")
        
    status = task_status.get("status")
    
    if status == "completed":
        result_json = get_db_value(f"manual_run_result_{post_code}")
        if not result_json:
            return redirect("/")
        try:
            result = json.loads(result_json)
        except Exception:
            return redirect("/")
            
        return render_template(
            "result.html",
            links=result.get("links"),
            all_commented=result.get("all_commented"),
            group=result.get("group"),
            user_missing_posts=result.get("user_missing_posts"),
            duplicate_comment_users=result.get("duplicate_comment_users"),
            invalid_comment_users=result.get("invalid_comment_users"),
            user_comments=result.get("user_comments"),
            thread_id=result.get("thread_id"),
            check_likes=result.get("check_likes", False),
            post_code=post_code,
            is_loading=False
        )
        
    elif status == "running":
        return render_template(
            "result.html",
            is_loading=True,
            progress=task_status.get("progress", 0),
            message=task_status.get("message", "İşlem başlatılıyor..."),
            post_code=post_code,
            links=[]
        )
        
    else: # failed
        return render_template(
            "result.html",
            is_loading=False,
            error_message=f"Hata oluştu: {task_status.get('error', 'Bilinmeyen hata')}",
            post_code=post_code,
            links=[]
        )


@main_bp.route("/api/task_status/<post_code>", methods=["GET"])
def task_status_route(post_code):
    task_status_json = get_db_value(f"task_status_{post_code}")
    if not task_status_json:
        return jsonify({"status": "not_found", "progress": 0, "error": "Görev bulunamadı"})
    try:
        data = json.loads(task_status_json)
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "failed", "progress": 100, "error": str(e)})


@main_bp.route("/api/recheck/<post_code>", methods=["POST"])
def recheck_post(post_code):
    data = request.get_json() or {}
    only_missing = data.get("only_missing", False)
    
    # Girdilerin varlığını doğrula
    inputs_json = get_db_value(f"manual_run_inputs_{post_code}")
    if not inputs_json:
        return jsonify({"success": False, "message": "Girdiler bulunamadı. Lütfen ana sayfadan tekrar gönderin."}), 400
        
    # Görevin zaten çalışıp çalışmadığını kontrol et
    task_status_json = get_db_value(f"task_status_{post_code}")
    if task_status_json:
        try:
            status_data = json.loads(task_status_json)
            if status_data.get("status") == "running":
                return jsonify({"success": False, "message": "Görev zaten çalışıyor."}), 400
        except Exception:
            pass
            
    # Durumu güncelle
    set_db_value(f"task_status_{post_code}", json.dumps({
        "status": "running",
        "progress": 0,
        "message": "Güncelleme başlatılıyor...",
        "error": None
    }))
    
    # Thread başlat
    t = threading.Thread(target=run_manual_control_async, args=(post_code, only_missing), daemon=True)
    t.start()
    
    return jsonify({"success": True})


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

        grup_uye = request.form.get("grup_uye", "")
        thread_id = request.form.get("thread_id", "").strip()
        post_senders_raw = request.form.getlist("post_senders")
        check_likes = request.form.get("check_likes") == "on"

        # Post kodunu ayıkla
        import re
        match = re.search(r"instagram\.com/(?:p|reel|tv)/([a-zA-Z0-9\-_]+)", link)
        if not match:
            return render_template("form.html", token_error_message="Geçersiz Instagram linki formatı.")
        post_code = match.group(1)

        # Girdileri kaydet
        inputs = {
            "link": link,
            "grup_uye": grup_uye,
            "thread_id": thread_id,
            "post_senders_raw": post_senders_raw,
            "check_likes": check_likes
        }
        set_db_value(f"manual_run_inputs_{post_code}", json.dumps(inputs))
        
        # Görev zaten çalışıyor mu?
        is_running = False
        task_status_json = get_db_value(f"task_status_{post_code}")
        if task_status_json:
            try:
                status_data = json.loads(task_status_json)
                if status_data.get("status") == "running":
                    is_running = True
            except Exception:
                pass
                
        if not is_running:
            # Thread başlat
            set_db_value(f"task_status_{post_code}", json.dumps({
                "status": "running",
                "progress": 0,
                "message": "Denetim başlatılıyor...",
                "error": None
            }))
            t = threading.Thread(target=run_manual_control_async, args=(post_code, False), daemon=True)
            t.start()

        return redirect(url_for("main.result_page_new", post_code=post_code))

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

@main_bp.route("/api/relogin_active", methods=["POST"])
def relogin_active():
    from app_core.storage import load_tokens
    from app_core.token_service import relogin_saved_user
    tokens = load_tokens(include_deleted=False)
    if not tokens:
        return jsonify({"ok": False, "message": "Sistemde kayitli token bulunamadi."})
    
    # Ilk aktif olani veya ilk tokeni sec
    target_token = next((t for t in tokens if t.get("status") == "active"), None)
    if not target_token:
        target_token = tokens[0]
        
    username = target_token.get("username")
    if not username:
        return jsonify({"ok": False, "message": "Gecerli bir kullanici adi bulunamadi."})
        
    result = relogin_saved_user(username)
    return jsonify({
        "ok": result.get("ok", False),
        "message": result.get("message", "Bilinmeyen hata")
    })


@main_bp.route("/api/get_selected_post", methods=["GET"])
def get_selected_post():
    thread_id = request.args.get("thread_id", "").strip()
    date_str = request.args.get("date", "").strip()
    if not thread_id or not date_str:
        return jsonify({"success": False, "message": "thread_id ve date parametreleri zorunludur"}), 400
    
    from app_core.storage import get_selected_post_for_group
    post_url = get_selected_post_for_group(thread_id, date_str)
    return jsonify({"success": True, "post_url": post_url})


@main_bp.route("/api/save_selected_post", methods=["POST"])
def save_selected_post():
    data = request.get_json() or {}
    thread_id = data.get("thread_id", "").strip()
    date_str = data.get("date", "").strip()
    post_url = data.get("post_url", "").strip()
    
    if not thread_id or not date_str:
        return jsonify({"success": False, "message": "thread_id ve date zorunludur"}), 400
        
    from app_core.storage import set_selected_post_for_group
    success = set_selected_post_for_group(thread_id, date_str, post_url)
    return jsonify({"success": success})


@main_bp.route("/api/check_cached_result", methods=["GET"])
def check_cached_result():
    thread_id = request.args.get("thread_id", "").strip()
    date_str = request.args.get("date", "").strip()
    if not thread_id or not date_str:
        return jsonify({"success": False, "message": "thread_id ve date parametreleri zorunludur"}), 400
    
    from app_core.storage import get_cached_run_result
    result = get_cached_run_result(thread_id, date_str)
    return jsonify({"success": True, "has_cache": result is not None})


@main_bp.route("/result/cached", methods=["GET"])
def cached_result():
    thread_id = request.args.get("thread_id", "").strip()
    date_str = request.args.get("date", "").strip()
    if not thread_id or not date_str:
        return redirect("/")
    
    from app_core.storage import get_cached_run_result
    result = get_cached_run_result(thread_id, date_str)
    if not result:
        return redirect("/")
        
    return render_template(
        "result.html",
        links=result.get("links"),
        all_commented=result.get("all_commented"),
        group=result.get("group"),
        user_missing_posts=result.get("user_missing_posts"),
        duplicate_comment_users=result.get("duplicate_comment_users"),
        invalid_comment_users=result.get("invalid_comment_users"),
        user_comments=result.get("user_comments"),
        thread_id=thread_id,
        check_likes=result.get("check_likes", False),
    )


@main_bp.route("/debug_logs")
def debug_logs():
    import os
    try:
        log_path = "/var/log/kontrolyeni.pythonanywhere.com.error.log"
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return "<pre>" + "".join(lines[-150:]) + "</pre>"
        else:
            return f"Log file not found at {log_path}"
    except Exception as e:
        return "Error reading log: " + str(e)


@main_bp.route("/debug_db/<post_code>")
def debug_db(post_code):
    try:
        status_val = get_db_value(f"task_status_{post_code}")
        result_val = get_db_value(f"manual_run_result_{post_code}")
        inputs_val = get_db_value(f"manual_run_inputs_{post_code}")
        return jsonify({
            "post_code": post_code,
            "task_status": json.loads(status_val) if status_val else None,
            "manual_run_result_length": len(result_val) if result_val else 0,
            "manual_run_result": json.loads(result_val) if result_val else None,
            "manual_run_inputs": json.loads(inputs_val) if inputs_val else None
        })
    except Exception as e:
        return jsonify({"error": str(e)})



