import json
import logging
import threading

logger = logging.getLogger(__name__)

# Her token için session state sakla (memory)
_store = {}
_lock = threading.Lock()

# Takip edilecek response header'lari
# Bloks endpoint'i bu degerleri HTTP header'lari yerine
# body'nin icindeki nested JSON'da gonderiyor.
# Tum varyantlari buraya ekliyoruz:
TRACKED_HEADERS = {
    # Standart HTTP header varyantlari
    "ig-set-ig-u-rur": "rur",
    "ig-set-ig-u-ds-user-id": "ds_user_id",
    "ig-set-ig-u-shbid": "shbid",
    "ig-set-ig-u-shbts": "shbts",
    "ig-set-ig-u-ig-direct-region-hint": "direct_region_hint",
    # Bloks body'sinden gelen kisa varyantlar
    "ig-u-rur": "rur",
    "ig-u-ds-user-id": "ds_user_id",
    "ig-u-shbid": "shbid",
    "ig-u-shbts": "shbts",
    "ig-u-ig-direct-region-hint": "direct_region_hint",
    # www-claim (x-ig-set-www-claim veya ig-set-www-claim)
    "x-ig-set-www-claim": "www_claim",
    "ig-set-www-claim": "www_claim",
}


def get_session(username):
    """Kullanıcının session state'ini döndürür."""
    with _lock:
        return dict(_store.get(username, {}))


def update_session(username, response_headers):
    """Response header'larindan session state'i gunceller.
    Hem HTTP response headers hem de bloks body header dict'lerini kabul eder."""
    if not username or not response_headers:
        return

    updated = False
    with _lock:
        state = _store.setdefault(username, {})
        for header_name, key in TRACKED_HEADERS.items():
            # Hem orijinal hem kucuk harf ile dene (case-insensitive)
            value = (
                response_headers.get(header_name)
                or response_headers.get(header_name.lower())
                or response_headers.get(header_name.upper())
            )
            # Bazi header'larda deger "" (bos string) veya None gelir; skip et
            if not value or str(value).strip() == "":
                continue
            value = str(value).strip()
            old = state.get(key)
            if old != value:
                state[key] = value
                updated = True

    if updated:
        logger.debug("Session state guncellendi: @%s -> %s", username,
                     {k: v for k, v in state.items() if k != "www_claim" or len(v) < 30})
        _save_to_db(username)


import re

def _search_headers_in_body(body):
    """
    Instagram Bloks JSON gövdelerinde çok katmanlı escaping ve hatalı parantez dizilimi (nested strings)
    olduğu için, json.loads ve recursive çözümler patlayabilir (örneğin X-IG-Reload-Proxy-Request-Info içinde).
    Bu yüzden en 'fail-proof' yöntem olan DOĞRUDAN REGEX DEĞER AYIKLAMA yöntemi kullanılır.
    """
    raw_text = json.dumps(body, ensure_ascii=False) if not isinstance(body, str) else body
    found_headers = {}

    # 1. Bearer Token (IG-Set-Authorization)
    # Token base64 chars icindedir, surpluslu tırnaklar hareket etmez.
    m_auth = re.search(r'(Bearer IGT:[a-zA-Z0-9:_\-=]+)', raw_text)
    if m_auth:
        found_headers["ig-set-authorization"] = m_auth.group(1)

    # 2. RUR - Degeri kisa bir bölge kodu (LDC, RVA, vb.) - tırnak/backslash kalabalığı arasından çıkar
    m_rur = re.search(r'ig-set-ig-u-rur[^A-Za-z]{1,40}([A-Z]{2,6})', raw_text, re.IGNORECASE)
    if m_rur:
        found_headers["ig-set-ig-u-rur"] = m_rur.group(1)

    # 3. DS_USER_ID - Sayısal değer, tırnak arasında gelemez zaten
    m_ds = re.search(r'ig-set-ig-u-ds-user-id[^\d]{1,30}(\d+)', raw_text, re.IGNORECASE)
    if m_ds:
        found_headers["ig-set-ig-u-ds-user-id"] = m_ds.group(1)

    # 4. WWW-CLAIM - "hmac." ile başlar, her zaman
    m_claim = re.search(r'x-ig-set-www-claim[^h]{1,30}(hmac\.[A-Za-z0-9_\-\.]+)', raw_text, re.IGNORECASE)
    if m_claim:
        found_headers["x-ig-set-www-claim"] = m_claim.group(1)

    return [found_headers] if found_headers else []


def update_session_from_body(username, response_body):
    """
    Response body icerisindeki gizli headers JSON stringlerini tarar.
    Bloks endpointlerinde gercek session degerleri body icindedir.
    """
    if not username or not response_body or not isinstance(response_body, dict):
        logger.debug("update_session_from_body: Gecersiz input")
        return

    found_headers_list = _search_headers_in_body(response_body)
    if not found_headers_list:
        logger.debug("update_session_from_body: HICBİR HEADER BULUNAMADI")
        return

    # Birden fazla bulunduysa hepsini sirali isle (ilk login_response > diger)
    for header_dict in found_headers_list:
        update_session(username, header_dict)

    logger.debug("Body'den session header'lari islendi: @%s (%d blok)", username, len(found_headers_list))


    logger.debug("Body'den session header'lari islendi: @%s (%d blok)", username, len(found_headers_list))




def get_auth_headers(username, token, user_agent, android_id, device_id):
    """Guncel session state ile auth header'lari olusturur.
    Orijinal Instagram mobil uygulamasinin gonderdigi tum kritik header'lar dahildir.
    """
    from app_core.config import IG_APP_ID

    state = get_session(username)

    # Kullanici ID'sini token veya session'dan cek
    ds_user_id = state.get("ds_user_id")
    if not ds_user_id or ds_user_id == "0":
        try:
            from app_core.instagram_api import extract_user_id_from_token
            ds_user_id = extract_user_id_from_token(token) or "0"
        except Exception:
            ds_user_id = "0"


    headers = {
        "authorization": token,
        "user-agent": user_agent,
        "x-ig-app-id": IG_APP_ID,
        "x-ig-android-id": f"android-{android_id}",
        "x-ig-device-id": device_id,
        # Orijinal mobil uygulamayla eslesen kritik header'lar:
        "ig-intended-user-id": ds_user_id,
        "x-ig-capabilities": "3brTv10=",
        "x-ig-connection-type": "WIFI",
        "x-fb-connection-type": "WIFI",
        "x-ig-app-locale": "tr_TR",
        "x-ig-device-locale": "tr_TR",
        "x-ig-mapped-locale": "tr_TR",
        "x-ig-device-languages": '{"system_languages":"tr-TR"}',
        "x-ig-timezone-offset": "10800",   # UTC+3 (Turkiye)
        "x-ig-is-foldable": "false",
        "x-ig-transfer-encoding": "chunked",
        "accept-language": "tr-TR, en-US",
        # Bloks version + prism UI flags
        "x-bloks-version-id": "cde38ed121b450d263742dc90efbd3d862247135473330574c1e5f63a6afd97d",
        "x-bloks-is-layout-rtl": "false",
        "x-bloks-prism-button-version": "INDIGO_PRIMARY_BORDERED_SECONDARY",
        "x-bloks-prism-colors-enabled": "true",
        "x-bloks-prism-extended-palette-gray": "false",
        "x-bloks-prism-extended-palette-indigo": "true",
        "x-bloks-prism-extended-palette-polish-enabled": "false",
        "x-bloks-prism-extended-palette-red": "true",
        "x-bloks-prism-extended-palette-rest-of-colors": "true",
        "x-bloks-prism-font-enabled": "true",
        "x-bloks-prism-indigo-link-version": "1",
    }

    # Session'dan gelen dinamik degerler
    if state.get("rur"):
        headers["ig-u-rur"] = state["rur"]
    if state.get("ds_user_id"):
        headers["ig-u-ds-user-id"] = state["ds_user_id"]
    if state.get("shbid"):
        headers["ig-u-shbid"] = state["shbid"]
    if state.get("shbts"):
        headers["ig-u-shbts"] = state["shbts"]
    if state.get("direct_region_hint"):
        headers["ig-set-ig-u-ig-direct-region-hint"] = state["direct_region_hint"]
    if state.get("www_claim"):
        headers["x-ig-www-claim"] = state["www_claim"]

    return headers


def load_from_db(username):
    """DB'den session state'i yükler."""
    try:
        from app_core.storage import _connect
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT value FROM key_value WHERE key=?",
                (f"session_state_{username}",),
            ).fetchone()
            if row:
                with _lock:
                    _store[username] = json.loads(row["value"])
                logger.debug("Session state DB'den yüklendi: @%s", username)
        finally:
            conn.close()
    except Exception as error:
        logger.warning("Session state yükleme hatasi: %s", error)


def _save_to_db(username):
    """Session state'i DB'ye kaydeder."""
    try:
        from app_core.storage import _connect
        state = get_session(username)
        if not state:
            return
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO key_value (key, value) VALUES (?, ?)",
                (f"session_state_{username}", json.dumps(state, ensure_ascii=False)),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as error:
        logger.warning("Session state kaydetme hatasi: %s", error)
