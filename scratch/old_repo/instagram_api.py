import base64
import json
import logging

import requests

from app_core.config import IG_APP_ID

logger = logging.getLogger(__name__)

MAX_COMMENT_PAGES = 50


def get_post_sender(media_id, token_record):
    """Verilen media_id'nin göndericisini (owner) bulur."""
    username = _get_username(token_record)
    token = token_record.get("token", "")
    user_agent = token_record.get("user_agent", "")
    android_id = token_record.get("android_id_yeni", "")
    device_id = token_record.get("device_id", "")
    
    if not all([token, user_agent, android_id, device_id]):
        return None
    
    user_id = extract_user_id_from_token(token)
    if not user_id:
        return None
    
    headers = build_auth_headers(token, user_agent, android_id, device_id, username=username)
    headers.update({
        "x-ig-app-locale": "tr_TR",
        "x-ig-device-locale": "tr_TR",
        "x-ig-mapped-locale": "tr_TR",
        "x-ig-capabilities": "3brTv10=",
        "x-ig-connection-type": "WIFI",
        "x-fb-connection-type": "WIFI",
        "accept-language": "tr-TR, en-US",
    })
    
    # Önce /media/{id}/info/ dene
    try:
        response = requests.get(
            f"https://i.instagram.com/api/v1/media/{media_id}/info/",
            headers=headers,
            timeout=10,
        )
        _update_session_from_response(username, response)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if items:
                user = items[0].get("user", {})
                return user.get("username", "")
    except:
        pass
    
    # Alternatif: /media/infos/ endpoint
    try:
        response = requests.get(
            f"https://i.instagram.com/api/v1/media/infos/",
            params={"media_ids": f"[{media_id}]"},
            headers=headers,
            timeout=10,
        )
        _update_session_from_response(username, response)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if items:
                user = items[0].get("user", {})
                return user.get("username", "")
    except:
        pass
    
    # Son çare: Yorumlardan post sahibini bul
    try:
        response = requests.get(
            f"https://i.instagram.com/api/v1/media/{media_id}/comments/",
            params={"can_support_threading": "true"},
            headers=headers,
            timeout=10,
        )
        _update_session_from_response(username, response)
        if response.status_code == 200:
            data = response.json()
            comments = data.get("comments", [])
            if comments:
                # İlk yorum genelde post sahibindir
                user = comments[0].get("user", {})
                return user.get("username", "")
    except:
        pass
    
    logger.warning("Post gönderici bulunamadı: %s", media_id)
    return None


def extract_user_id_from_token(token):
    if not token or not token.startswith("Bearer IGT:2:"):
        return None
    try:
        token_data = token.replace("Bearer IGT:2:", "")
        # Padding ekle
        missing_padding = len(token_data) % 4
        if missing_padding:
            token_data += "=" * (4 - missing_padding)
        decoded = base64.b64decode(token_data)
        data = json.loads(decoded)
        return str(data.get("ds_user_id") or data.get("user_id") or "")
    except Exception as e:
        logger.warning("Token'dan user_id cikarma hatasi: %s", e)
        return None


def build_auth_headers(token, user_agent, android_id, device_id, username=None):
    from app_core.session_state import get_auth_headers
    if username:
        return get_auth_headers(username, token, user_agent, android_id, device_id)
    return {
        "authorization": token,
        "user-agent": user_agent,
        "x-ig-app-id": IG_APP_ID,
        "x-ig-android-id": f"android-{android_id}",
        "x-ig-device-id": device_id,
    }


def _update_session_from_response(username, response):
    """
    Response'dan session state'i gunceller.
    Iki kaynagi kontrol eder:
      1. HTTP response header'lari (normal API endpoint'leri)
      2. Response body icindeki nested 'headers' JSON string'i
         (Bloks endpoint'leri gercek degerleri buraya gomor)
    """
    if not username or not response:
        return
    try:
        from app_core.session_state import update_session, update_session_from_body
        # 1) HTTP response header'lari
        update_session(username, response.headers)
        # 2) Body icindeki gizli header'lar (JSON parse edilebiliyorsa)
        try:
            body = response.json()
            if isinstance(body, dict):
                update_session_from_body(username, body)
        except Exception:
            pass  # JSON degilse veya parse hatasi varsa sessizce gec
    except Exception:
        pass



def _get_username(token_record):
    """Token record'dan username'i çıkarır."""
    return token_record.get("username", "") if token_record else ""


def fetch_current_user(token, user_agent, android_id, device_id, timeout=5):
    headers = build_auth_headers(token, user_agent, android_id, device_id)
    response = requests.get(
        "https://i.instagram.com/api/v1/accounts/current_user/?edit=true",
        headers=headers,
        timeout=timeout,
    )
    return response


def validate_token(token_record):
    username = _get_username(token_record)
    token = token_record.get("token", "")
    user_agent = token_record.get("user_agent", "")
    android_id = token_record.get("android_id_yeni", "")
    device_id = token_record.get("device_id", "")
    
    if not token or not user_agent or not android_id or not device_id:
        return False
    
    user_id = extract_user_id_from_token(token)
    if not user_id:
        return True
    
    # Birincil: GraphQL profile timeline (doğal görünür, inbox kadar sıklıkla kullanılmaz)
    try:
        from urllib.parse import quote as _urlquote
        headers = {
            "authorization": token,
            "user-agent": user_agent,
            "x-ig-app-id": IG_APP_ID,
            "x-ig-android-id": f"android-{android_id}",
            "x-ig-device-id": device_id,
            "x-fb-friendly-name": "IGProfileTimelineQuery",
            "x-ig-bloks-serialize-payload": "true",
            "x-ig-validate-null-in-legacy-dict": "true",
            "content-type": "application/x-www-form-urlencoded",
        }
        variables = json.dumps({"user_id": user_id, "count": 1}, separators=(",", ":"))
        data = (
            "method=post&pretty=false&format=json&server_timestamps=true"
            "&locale=user&purpose=refresh"
            "&fb_api_req_friendly_name=IGProfileTimelineQuery"
            "&client_doc_id=56030350817877850088506871007"
            "&enable_canonical_naming=true"
            f"&variables={_urlquote(variables)}"
        )
        response = requests.post(
            "https://i.instagram.com/graphql/query",
            headers=headers,
            data=data,
            timeout=10,
        )
        _update_session_from_response(username, response)
        if response.status_code == 200:
            logger.info("Token dogrulandi (graphql): %s", device_id[:8])
            return True
        if response.status_code in [401, 403]:
            logger.warning("Token reddedildi (graphql): %d", response.status_code)
            return False
    except Exception as error:
        logger.warning("Token dogrulama hatasi (graphql): %s", error)
    
    # Fallback: inbox
    try:
        headers = build_auth_headers(token, user_agent, android_id, device_id, username=username)
        response = requests.get(
            "https://i.instagram.com/api/v1/direct_v2/inbox/",
            headers=headers,
            timeout=10,
        )
        _update_session_from_response(username, response)
        if response.status_code == 200:
            logger.info("Token dogrulandi (inbox fallback): %s", device_id[:8])
            return True
        if response.status_code in [401, 403]:
            logger.warning("Token reddedildi (inbox fallback): %d", response.status_code)
            return False
    except Exception as error:
        logger.warning("Token dogrulama hatasi (inbox fallback): %s", error)
    
    return True


def fetch_comment_usernames(media_id, token_record, min_id=None, progress_callback=None):
    username = _get_username(token_record)
    token = token_record.get("token", "")
    user_agent = token_record.get("user_agent", "")
    android_id = token_record.get("android_id_yeni", "")
    device_id = token_record.get("device_id", "")

    headers = build_auth_headers(token, user_agent, android_id, device_id, username=username)
    headers.update({
        "x-ig-app-locale": "tr_TR",
        "x-ig-device-locale": "tr_TR",
        "x-ig-mapped-locale": "tr_TR",
        "x-ig-capabilities": "3brTv10=",
        "x-ig-connection-type": "WIFI",
        "x-fb-connection-type": "WIFI",
        "accept-language": "tr-TR, en-US",
        "x-fb-http-engine": "Liger",
        "x-fb-client-ip": "True",
        "x-fb-server-cluster": "True",
    })

    params = {
        "min_id": min_id,
        "sort_order": "popular",
        "analytics_module": "comments_v2_feed_contextual_profile",
        "can_support_threading": "true",
        "is_carousel_bumped_post": "false",
        "feed_position": "0",
    }

    usernames = set()
    page_count = 0

    while page_count < MAX_COMMENT_PAGES:
        page_count += 1

        try:
            response = requests.get(
                f"https://i.instagram.com/api/v1/media/{media_id}/stream_comments/",
                params=params,
                headers=headers,
                timeout=10,
            )
            _update_session_from_response(username, response)
        except Exception as error:
            logger.error("Yorum API istegi basarisiz (sayfa %d): %s", page_count, error)
            break

        if response.status_code in [401, 403]:
            return {"ok": False, "status": response.status_code, "usernames": usernames}

        if response.status_code == 429:
            return {"ok": False, "status": 429, "rate_limited": True, "usernames": usernames}

        if response.status_code != 200:
            return {"ok": False, "status": response.status_code, "usernames": usernames}

        json_data = None
        for line in response.text.splitlines():
            try:
                json_data = json.loads(line)
                for comment in json_data.get("comments", []):
                    uname = comment.get("user", {}).get("username")
                    text = comment.get("text", "")
                    if uname:
                        usernames.add((uname, text))
            except json.JSONDecodeError:
                continue

        if progress_callback:
            try:
                progress_callback(page_count, MAX_COMMENT_PAGES)
            except Exception:
                pass

        if not json_data:
            break

        next_min_id = json_data.get("next_min_id")
        if not next_min_id:
            break
        params["min_id"] = next_min_id

    if page_count >= MAX_COMMENT_PAGES:
        logger.warning("Maksimum sayfa limitine ulasildi (%d)", MAX_COMMENT_PAGES)

    return {"ok": True, "status": 200, "comments": list(usernames)}


def fetch_liker_usernames(media_id, token_record, progress_callback=None):
    username = _get_username(token_record)
    token = token_record.get("token", "")
    user_agent = token_record.get("user_agent", "")
    android_id = token_record.get("android_id_yeni", "")
    device_id = token_record.get("device_id", "")

    headers = build_auth_headers(token, user_agent, android_id, device_id, username=username)
    headers.update({
        "x-ig-app-locale": "tr_TR",
        "x-ig-device-locale": "tr_TR",
        "x-ig-mapped-locale": "tr_TR",
        "x-ig-capabilities": "3brTv10=",
        "x-ig-connection-type": "WIFI",
        "x-fb-connection-type": "WIFI",
        "accept-language": "tr-TR, en-US",
        "x-fb-http-engine": "Liger",
        "x-fb-client-ip": "True",
        "x-fb-server-cluster": "True",
    })

    usernames = set()
    try:
        response = requests.get(
            f"https://i.instagram.com/api/v1/media/{media_id}/likers/",
            headers=headers,
            timeout=15,
        )
        _update_session_from_response(username, response)
        if response.status_code in [401, 403]:
            return {"ok": False, "status": response.status_code, "usernames": usernames}

        if response.status_code == 429:
            return {"ok": False, "status": 429, "rate_limited": True, "usernames": usernames}

        if response.status_code != 200:
            return {"ok": False, "status": response.status_code, "usernames": usernames}

        json_data = response.json()
        for user in json_data.get("users", []):
            uname = user.get("username")
            if uname:
                usernames.add(uname)
                
    except Exception as error:
        logger.error("Begeni API istegi basarisiz: %s", error)

    return {"ok": True, "status": 200, "usernames": usernames}


def fetch_group_threads(token_record):
    username = _get_username(token_record)
    token = token_record.get("token", "")
    user_agent = token_record.get("user_agent", "")
    android_id = token_record.get("android_id_yeni", "")
    device_id = token_record.get("device_id", "")
    
    if not all([token, user_agent, android_id, device_id]):
        return {"ok": False, "error": "Eksik token bilgileri"}
    
    headers = build_auth_headers(token, user_agent, android_id, device_id, username=username)
    headers.update({
        "x-ig-app-locale": "tr_TR",
        "x-ig-device-locale": "tr_TR",
        "x-ig-mapped-locale": "tr_TR",
        "x-ig-capabilities": "3brTv10=",
        "x-ig-connection-type": "WIFI",
        "x-fb-connection-type": "WIFI",
        "accept-language": "tr-TR, en-US",
    })
    
    try:
        response = requests.get(
            "https://i.instagram.com/api/v1/direct_v2/inbox/",
            headers=headers,
            timeout=15,
        )
        _update_session_from_response(username, response)
        if response.status_code != 200:
            return {"ok": False, "error": f"HTTP {response.status_code}"}
        
        data = response.json()
        threads = data.get("inbox", {}).get("threads", [])
        
        groups = []
        for thread in threads:
            thread_id = thread.get("thread_id")
            thread_title = thread.get("thread_title", "")
            users = thread.get("users", [])
            
            if thread_title:
                group_name = thread_title.encode('utf-8', errors='replace').decode('utf-8')
            else:
                usernames = [u.get("username", "") for u in users if u.get("username")]
                group_name = ", ".join(usernames[:3]) + ("..." if len(usernames) > 3 else "")
            
            if group_name and len(users) > 1:
                groups.append({
                    "id": thread_id,
                    "name": group_name,
                    "member_count": len(users),
                })
        
        logger.info(f"Bulunan grup sayisi: {len(groups)}")
        return {"ok": True, "groups": groups}
    except Exception as e:
        logger.error("Grup cekme hatasi: %s", e)
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


def fetch_group_members(token_record, thread_id):
    username = _get_username(token_record)
    token = token_record.get("token", "")
    user_agent = token_record.get("user_agent", "")
    android_id = token_record.get("android_id_yeni", "")
    device_id = token_record.get("device_id", "")
    
    if not all([token, user_agent, android_id, device_id]):
        return {"ok": False, "error": "Eksik token bilgileri"}
    
    headers = build_auth_headers(token, user_agent, android_id, device_id, username=username)
    headers.update({
        "x-ig-app-locale": "tr_TR",
        "x-ig-device-locale": "tr_TR",
        "x-ig-mapped-locale": "tr_TR",
        "x-ig-capabilities": "3brTv10=",
        "x-ig-connection-type": "WIFI",
        "x-fb-connection-type": "WIFI",
        "accept-language": "tr-TR, en-US",
    })
    
    try:
        response = requests.get(
            f"https://i.instagram.com/api/v1/direct_v2/threads/{thread_id}/",
            headers=headers,
            timeout=15,
        )
        _update_session_from_response(username, response)
        if response.status_code != 200:
            return {"ok": False, "error": f"HTTP {response.status_code}"}
        
        data = response.json()
        thread = data.get("thread", {})
        users = thread.get("users", [])
        admin_user_ids = set(str(uid) for uid in thread.get("admin_user_ids", []))
        
        usernames = []
        for user in users:
            user_id = str(user.get("pk", ""))
            username = user.get("username", "")
            if username and user_id not in admin_user_ids:
                usernames.append(username)
        
        return {"ok": True, "usernames": usernames}
    except Exception as e:
        logger.error("Grup uyeleri cekme hatasi: %s", e)
        return {"ok": False, "error": str(e)}


def fetch_group_media(token_record, thread_id, target_date=None):
    import datetime
    import pytz
    
    class GMT3(datetime.tzinfo):
        def utcoffset(self, _):
            return datetime.timedelta(hours=3)
        def tzname(self, _):
            return "GMT+3"
        def dst(self, _):
            return datetime.timedelta(0)
    
    gmt3 = GMT3()
    utc = pytz.UTC
    
    if target_date is None:
        target_date = datetime.datetime.now(gmt3)
    
    username = _get_username(token_record)
    token = token_record.get("token", "")
    user_agent = token_record.get("user_agent", "")
    android_id = token_record.get("android_id_yeni", "")
    device_id = token_record.get("device_id", "")
    
    user_id = extract_user_id_from_token(token)
    if not user_id:
        return {"ok": False, "error": "Token'dan user_id alinamadi"}
    
    if not all([token, user_agent, android_id, device_id]):
        return {"ok": False, "error": "Eksik token bilgileri"}
    
    headers = build_auth_headers(token, user_agent, android_id, device_id, username=username)
    headers.update({
        "x-ig-app-locale": "tr_TR",
        "x-ig-device-locale": "tr_TR",
        "x-ig-mapped-locale": "tr_TR",
        "x-ig-capabilities": "3brTv10=",
        "x-ig-connection-type": "WIFI",
        "x-fb-connection-type": "WIFI",
        "accept-language": "tr-TR, en-US",
        "ig-intended-user-id": user_id,
        "ig-u-ds-user-id": user_id,
        "priority": "u=3",
        "x-fb-friendly-name": "IgApi: direct_v2_threads_media",
    })
    
    target_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=gmt3)
    target_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=gmt3)
    
    max_ts = int(target_end.timestamp() * 1000000)
    min_ts = int(target_start.timestamp() * 1000000)
    
    try:
        # Ekstra: Gruptaki kullanicilari onceden alalim ki, post atani isimle eslestirebilelim
        thread_users_map = {}
        try:
            t_resp = requests.get(
                f"https://i.instagram.com/api/v1/direct_v2/threads/{thread_id}/",
                headers=headers,
                timeout=10,
            )
            if t_resp.status_code == 200:
                t_data = t_resp.json()
                for u in t_data.get("thread", {}).get("users", []):
                    thread_users_map[str(u.get("pk", ""))] = u.get("username", "")
                inviter = t_data.get("thread", {}).get("inviter", {})
                if inviter:
                    thread_users_map[str(inviter.get("pk", ""))] = inviter.get("username", "")
        except Exception:
            pass

        response = requests.get(
            f"https://i.instagram.com/api/v1/direct_v2/threads/{thread_id}/media/",
            params={
                "max_timestamp": max_ts,
                "limit": "50",
                "media_type": "media_shares",
            },
            headers=headers,
            timeout=15,
        )
        _update_session_from_response(username, response)
        if response.status_code != 200:
            return {"ok": False, "error": f"HTTP {response.status_code}"}
        
        data = response.json()
        items = data.get("items", [])
        
        posts = []
        for item in items:
            media = item.get("media", {})
            code = media.get("code")
            if not code:
                continue
            
            timestamp = item.get("timestamp", 0)
            
            if timestamp < min_ts or timestamp > max_ts:
                continue
            
            timestamp_sec = int(timestamp / 1000000)
            dt_utc = datetime.datetime.utcfromtimestamp(timestamp_sec)
            dt_utc = utc.localize(dt_utc)
            dt = dt_utc.astimezone(gmt3)
            
            turkish_months = {
                1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
                5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
                9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
            }
            
            taken_at = media.get("taken_at", 0)
            if taken_at:
                dt_taken = datetime.datetime.utcfromtimestamp(taken_at)
                dt_taken = utc.localize(dt_taken)
                dt_taken = dt_taken.astimezone(gmt3)
                upload_date = f"{dt_taken.day} {turkish_months[dt_taken.month]} Yüklendi"
            else:
                upload_date = f"{dt.day} {turkish_months[dt.month]} Yüklendi"
            
            date = f"{dt.day} {turkish_months[dt.month]} {dt.strftime('%H:%M')} ({upload_date})"
            
            sender_pk = str(item.get("user_id", "") or item.get("sender_id", ""))
            post_owner_pk = str(media.get("user", {}).get("pk", "") or media.get("user", {}).get("id", ""))
            post_owner_username = media.get("user", {}).get("username", "") or item.get("media_share", {}).get("user", {}).get("username", "")
            
            final_sender = post_owner_username
            
            # Postun sahibiyle posta atan ayni degilse, atan kisinin kullanici adini bulalim
            if sender_pk and post_owner_pk and sender_pk != post_owner_pk:
                if sender_pk in thread_users_map:
                    final_sender = thread_users_map[sender_pk]
                else:
                    # Eger thread icinde user objesi olarak gelmisse (nadir)
                    alt_user = item.get("user", {}).get("username", "")
                    if alt_user:
                        final_sender = alt_user
            
            sender_username = final_sender
            
            like_count = media.get("like_count", -1)
            
            posts.append({
                "id": media.get("id"),
                "code": code,
                "url": f"https://www.instagram.com/p/{code}/",
                "date": date,
                "username": sender_username,
                "like_count": like_count,
                "media_type": "video" if media.get("media_type") == 2 else "image",
            })
        
        return {"ok": True, "posts": posts}
    except Exception as e:
        logger.error("Grup paylasimlari cekme hatasi: %s", e)
        return {"ok": False, "error": str(e)}


def fetch_own_thread_items(token_record, thread_id, limit=20):
    """Thread'deki son mesajları çeker, yalnızca bot'un attıklarını döndürür."""
    token = token_record.get("token", "")
    user_agent = token_record.get("user_agent", "")
    android_id = token_record.get("android_id_yeni", "")
    device_id = token_record.get("device_id", "")

    my_user_id = extract_user_id_from_token(token)
    if not my_user_id:
        return {"ok": False, "error": "Token'dan user_id alinamadi"}

    headers = {
        "authorization": token,
        "user-agent": user_agent,
        "x-ig-app-id": IG_APP_ID,
        "x-ig-android-id": f"android-{android_id}",
        "x-ig-device-id": device_id,
        "x-ig-capabilities": "3brTv10=",
        "x-ig-connection-type": "WIFI",
        "accept-language": "tr-TR, en-US",
    }

    try:
        resp = requests.get(
            f"https://i.instagram.com/api/v1/direct_v2/threads/{thread_id}/",
            headers=headers,
            params={"limit": limit},
            timeout=15,
        )
        if resp.status_code != 200:
            return {"ok": False, "error": f"HTTP {resp.status_code}"}

        data = resp.json()
        items = data.get("thread", {}).get("items", [])

        own_items = []
        for item in items:
            sender_id = str(item.get("user_id", ""))
            if sender_id == str(my_user_id):
                item_id = item.get("item_id")
                item_type = item.get("item_type", "")
                text = ""
                if item_type == "text":
                    text = item.get("text", "")
                own_items.append({
                    "item_id": item_id,
                    "item_type": item_type,
                    "text": text,
                })

        return {"ok": True, "items": own_items, "my_user_id": my_user_id}
    except Exception as e:
        logger.error("Thread item cekme hatasi: %s", e)
        return {"ok": False, "error": str(e)}


def delete_thread_item(token_record, thread_id, item_id):
    """Bir DM mesajını geri alır (siler)."""
    token = token_record.get("token", "")
    user_agent = token_record.get("user_agent", "")
    android_id = token_record.get("android_id_yeni", "")
    device_id = token_record.get("device_id", "")

    headers = {
        "authorization": token,
        "user-agent": user_agent,
        "x-ig-app-id": IG_APP_ID,
        "x-ig-android-id": f"android-{android_id}",
        "x-ig-device-id": device_id,
        "x-ig-capabilities": "3brTv10=",
        "content-type": "application/x-www-form-urlencoded",
    }

    try:
        resp = requests.post(
            f"https://i.instagram.com/api/v1/direct_v2/threads/{thread_id}/items/{item_id}/delete/",
            headers=headers,
            timeout=10,
        )
        ok = resp.status_code == 200
        if not ok:
            logger.warning("Mesaj silinemedi item=%s status=%s", item_id, resp.status_code)
        return {"ok": ok, "status": resp.status_code}
    except Exception as e:
        logger.error("Mesaj silme hatasi: %s", e)
        return {"ok": False, "error": str(e)}
