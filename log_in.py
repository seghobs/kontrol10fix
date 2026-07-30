import json
import logging
import re
import time
import random

import requests as curl_requests
logger = logging.getLogger(__name__)


class LoginError(Exception):
    def __init__(self, message, error_type="UNKNOWN", status_code=None, details=None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self):
        return {
            "message": self.message,
            "error_type": self.error_type,
            "status_code": self.status_code,
            "details": self.details,
        }


def _parse_instagram_error(response_data):
    if not isinstance(response_data, dict):
        return None
    
    message = response_data.get("message", "")
    error_data = response_data.get("data", {})
    
    if isinstance(error_data, dict):
        for key, value in error_data.items():
            if isinstance(value, dict):
                message = value.get("message", message)
                break
    
    return message if message else None


def _extract_login_failure_reason(response_data):
    if not isinstance(response_data, dict):
        return None
    
    message = _parse_instagram_error(response_data)
    if message:
        return message
    
    if "data" in response_data:
        data = response_data.get("data", {})
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and any(word in value.lower() for word in ["error", "fail", "invalid", "wrong"]):
                    return value
                if isinstance(value, dict):
                    error_msg = value.get("message") or value.get("error")
                    if error_msg:
                        return error_msg
    
    if "message" in response_data:
        return response_data.get("message")
    
    return None


def _handle_http_error(status_code, response_text):
    error_type = "UNKNOWN"
    message = "Bilinmeyen hata"
    details = {"status_code": status_code}

    if status_code == 400:
        error_type = "BAD_REQUEST"
        message = "Girdi parametreleri hatalı veya eksik"
        try:
            data = json.loads(response_text)
            parsed_msg = _parse_instagram_error(data)
            if parsed_msg:
                message = parsed_msg
                details["instagram_message"] = parsed_msg
        except Exception:
            pass
    elif status_code == 401:
        error_type = "UNAUTHORIZED"
        message = "Kullanıcı adı veya şifre hatalı"
    elif status_code == 403:
        error_type = "FORBIDDEN"
        message = "Hesaba erişim engellendi. IP veya hesap engellenmiş olabilir."
    elif status_code == 429:
        error_type = "RATE_LIMITED"
        message = "Çok fazla istek. Lütfen 15-30 dakika bekleyin."
    elif status_code == 500:
        error_type = "SERVER_ERROR"
        message = "Instagram sunucu hatası. Lütfen daha sonra tekrar deneyin."
    elif status_code == 502 or status_code == 503:
        error_type = "SERVICE_UNAVAILABLE"
        message = "Instagram hizmeti geçici olarak kullanılamıyor."
    else:
        message = f"HTTP Hatası: {status_code} - {response_text}"

    return LoginError(message, error_type, status_code, details)


def giris_yap(username, password, android_id, user_agent, device_id):
    android_id_yeni = android_id.strip()
    selected_user_agent = user_agent.strip()
    selected_device_id = device_id.strip()
    current_timestamp = time.time()

    logger.info("Giris denemesi: @%s", username)

    nav_chain = (
        f"SelfFragment:self_profile:2:main_profile:{current_timestamp:.3f}::,"
        f"ProfileMediaTabFragment:self_profile:3:button:{current_timestamp + 0.287:.3f}::,"
        f"SettingsScreenFragment:ig_settings:4:button:{current_timestamp + 2.284:.3f}::,"
        f"com.bloks.www.caa.login.aymh_single_profile_screen_entry:"
        f"com.bloks.www.caa.login.aymh_single_profile_screen_entry:6:button:{current_timestamp + 0.308:.3f}::"
    )

    headers = {
        "x-ig-app-locale": "tr_TR",
        "x-ig-device-locale": "tr_TR",
        "x-ig-mapped-locale": "tr_TR",
        "x-bloks-version-id": "dd9727564fa874f2ebf47e9eca5d00c86c1bf1eef22fcba4fd1e05edab8ec6e0",
        "x-bloks-is-prism-enabled": "true",
        "x-bloks-prism-button-version": "PROPOSAL_A",
        "x-bloks-prism-colors-enabled": "false",
        "x-bloks-prism-font-enabled": "false",
        "x-ig-attest-params": '{"attestation":[{"version":2,"type":"keystore","errors":[],"challenge_nonce":"","signed_nonce":"","key_hash":""}]}',
        "x-bloks-is-layout-rtl": "false",
        "x-ig-device-id": selected_device_id,
        "x-ig-android-id": f"android-{android_id_yeni}",
        "x-ig-timezone-offset": "10800",
        "x-ig-nav-chain": nav_chain,
        "x-fb-connection-type": "WIFI",
        "x-ig-connection-type": "WIFI",
        "x-ig-capabilities": "3brTv10=",
        "x-ig-app-id": "567067343352427",
        "priority": "u=3",
        "user-agent": selected_user_agent,
        "accept-language": "tr-TR, en-US",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "x-fb-http-engine": "Tigon/MNS/TCP",
        "x-fb-client-ip": "True",
        "x-fb-server-cluster": "True",
        "x-meta-zca": "eyJhbmRyb2lkIjp7ImFrYSI6eyJkYXRhVG9TaWduIjoie1widGltZVwiOlwiMTc3ODg0MzI1NzEwOVwiLFwiaGFzaFwiOlwiLVRXQThMbDdiZHYwMVF5cGVaUmJ3ZVRHSGMxRDZqNlZRUnlVUld5d05yb1wifSIsInNpZ25lZERhdGEiOiJNRVVDSVFDSTVzaWdhWXVDSXhvdFZtSmVGVTVlSWM1N0FBRWUxZV9PeUsxdVo4M2swQUlnUF9sekpuRjFOTi1sX2VFNkJadTBITnllN1ZhaUpmNFFGUWxwaHQ1R0tGbyIsImtleUhhc2giOiI2YjAxYWE5YmUyYjgzODg0YTEzNGI3MjUwNmEwMmM3ZjU5OTdiNmRiNWZhMTU3YzFjZDE1NGYwNzA2ZDZlMzQwIiwibGFzdFVwbG9hZGVkS2V5VGltZU1zIjoxNzc2MTY5Mzc3NTYwfSwiZ3BpYSI6eyJ0b2tlbiI6IiJ9LCJwYXlsb2FkIjp7InBsdWdpbnMiOnsiYmF0Ijp7InN0YSI6IkNoYXJnaW5nIiwibHZsIjoxMDB9LCJzY3QiOnt9LCJhZGIiOnsidXNiIjotMSwiYWRiIjotMSwidXNiX2FkYiI6LTF9fX19fQ",
        "x-meta-usdid": "c65b79b4-6b65-4106-92e1-df65f35f9447.1778846861.MEUCIQDfiXClmM9c5V4jYODm7ahsBjyMfK9ahEfd5OdWEpIpPwIgfnwS1VHy7xG_RAIHkRH5qzM_pUmOc2P-z1V8K6J44cY",
        "x-ig-client-endpoint": "IgCdsScreenNavigationLoggerModule:com.bloks.www.caa.assistive_login_confirmation",
    }

    params_dict = {
        "client_input_params": {
            "blocked_uids": [],
            "sim_phones": [],
            "secure_family_device_id": "",
            "has_granted_read_contacts_permissions": 0,
            "auth_secure_device_id": "",
            "has_whatsapp_installed": 0,
            "password": f"#PWD_INSTAGRAM:0:0:{password}",
            "block_store_machine_id": "",
            "ig_vetted_device_nonces": "{}",
            "cloud_trust_token": None,
            "event_flow": "login_manual",
            "password_contains_non_ascii": "false",
            "sso_accounts_auth_data": [],
            "encrypted_msisdn": "",
            "has_granted_read_phone_permissions": 0,
            "app_manager_id": "",
            "device_id": f"android-{android_id_yeni}",
            "zero_balance_state": "",
            "login_attempt_count": 1,
            "machine_id": selected_device_id,
            "accounts_list": [],
            "gms_incoming_call_retriever_eligibility": "not_eligible",
            "family_device_id": selected_device_id,
            "device_emails": [],
            "lois_settings": {"lois_token": ""},
            "event_step": "assistive_id_dbl_page",
            "headers_infra_flow_id": "",
            "contact_point": username
        },
        "server_params": {
            "should_trigger_override_login_2fa_action": 0,
            "is_from_logged_out": 0,
            "should_trigger_override_login_success_action": 0,
            "login_credential_type": "none",
            "server_login_source": "device_based_login",
            "waterfall_id": selected_device_id,
            "two_step_login_type": "one_step_login",
            "login_source": "Login",
            "is_platform_login": 0,
            "login_entry_point": "switcher",
            "INTERNAL__latency_qpl_marker_id": 36707139,
            "is_from_aymh": 0,
            "offline_experiment_group": "caa_iteration_v3_perf_ig_4",
            "is_from_landing_page": 0,
            "left_nav_button_action": "NONE",
            "password_text_input_id": "te4fqm:60",
            "is_from_empty_password": 0,
            "is_from_msplit_fallback": 0,
            "ar_event_source": "login_home_page",
            "qe_device_id": selected_device_id,
            "layered_homepage_experiment_group": "control",
            "should_show_nested_nta_from_aymh": 1,
            "device_id": f"android-{android_id_yeni}",
            "login_surface": "aymh_manual_login",
            "is_caa_perf_enabled": 0,
            "credential_type": "assistive_login",
            "is_from_password_entry_page": 1,
            "caller": "gslr",
            "family_device_id": selected_device_id,
            "is_from_assistive_id": 1,
            "access_flow_version": "pre_mt_behavior",
            "account_type_shown": "PRE_META",
            "access_flow_version_state": "pre_mt_behavior",
            "is_from_logged_in_switcher": 1
        }
    }

    bk_client_context = {
        "bloks_version": "dd9727564fa874f2ebf47e9eca5d00c86c1bf1eef22fcba4fd1e05edab8ec6e0",
        "styles_id": "instagram",
        "theme_params": [
            {"value": ["three_neutral_gray"], "design_system_name": "XMDS"}
        ]
    }

    data = {
        "params": json.dumps(params_dict, separators=(",", ":")),
        "bk_client_context": json.dumps(bk_client_context, separators=(",", ":")),
        "bloks_versioning_id": "dd9727564fa874f2ebf47e9eca5d00c86c1bf1eef22fcba4fd1e05edab8ec6e0",
    }

    response = None
    try:
        response = curl_requests.post(
            "https://i.instagram.com/api/v1/bloks/apps/com.bloks.www.bloks.caa.login.async.send_login_request/",
            headers=headers,
            data=data,
            timeout=15,
        )
    except (ConnectionError, TimeoutError) as error:
        logger.error("Ağ bağlantısı hatası: %s", str(error))
        raise LoginError(
            "İnternet bağlantısı sağlanamadı veya istek zaman aşımına uğradı. Bağlantınızı kontrol edin.",
            "NETWORK_ERROR",
            details={"original_error": str(error), "error_type": type(error).__name__}
        )
    except Exception as error:
        error_type = type(error).__name__
        logger.error("Beklenmeyen hata: %s | Tip: %s", str(error), error_type)
        
        if "Connection" in error_type:
            raise LoginError(
                "Instagram sunucusuna bağlanılamadı.",
                "CONNECTION_ERROR",
                details={"original_error": str(error)}
            )
        elif "Timeout" in error_type:
            raise LoginError(
                "İstek zaman aşımına uğradı.",
                "TIMEOUT",
                details={"original_error": str(error)}
            )
        else:
            raise LoginError(
                f"Beklenmeyen hata: {str(error)}",
                "UNKNOWN",
                details={"error_type": error_type, "original_error": str(error)}
            )

    if response is None:
        logger.error("Response nesnesi oluşturulamadı")
        raise LoginError("Sunucudan yanıt alınamadı", "NO_RESPONSE")

    logger.info("Response Status Code: %d", response.status_code)

    if response.status_code >= 400:
        error = _handle_http_error(response.status_code, response.text)
        logger.error("HTTP hatası: %s | Durum kodu: %d", error.message, response.status_code)
        raise error

    yeni = None
    try:
        yeni = response.json()
        logger.debug("Response JSON: %s", json.dumps(yeni, indent=2, ensure_ascii=False))
    except json.JSONDecodeError as parse_error:
        logger.error("JSON Parse Hatası: %s | Response: %s", parse_error, response.text[:500])
        raise LoginError(
            "Instagram yanıtı okunamadı.",
            "JSON_PARSE_ERROR",
            details={"parse_error": str(parse_error), "response_preview": response.text[:200]}
        )
    except Exception as parse_error:
        logger.error("Beklenmeyen parse hatası: %s", str(parse_error))
        raise LoginError(
            f"Yanıt işlenirken hata: {str(parse_error)}",
            "PARSE_ERROR",
            details={"original_error": str(parse_error)}
        )

    def find_bearer_token(payload):
        token_pattern = re.compile(r"Bearer IGT:[a-zA-Z0-9:_\-]+")

        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, str):
                    match = token_pattern.search(value)
                    if match:
                        return match.group(0)
                elif isinstance(value, (dict, list)):
                    result = find_bearer_token(value)
                    if result:
                        return result
        elif isinstance(payload, list):
            for item in payload:
                result = find_bearer_token(item)
                if result:
                    return result
        return None

    bearer_token = find_bearer_token(yeni)

    if bearer_token:
        logger.info("Token bulundu: @%s", username)
        time.sleep(random.uniform(0.5, 1.5))
    else:
        logger.warning("Token bulunamadi: @%s", username)

        error_message = _extract_login_failure_reason(yeni)
        if error_message:
            logger.error("Giriş başarısız nedeni: %s", error_message)
            raise LoginError(
                error_message,
                "LOGIN_FAILED",
                details={"response": str(yeni)[:500]}
            )

        raise LoginError(
            "Token alınamadı. Kullanıcı adı veya şifre hatalı olabilir.",
            "TOKEN_NOT_FOUND",
            details={"response": str(yeni)[:500]}
        )

    # Session state güncelle:
    # 1) Once HTTP response header'lari (Bloks'ta bos gelir ama normal API'lerde doludur)
    # 2) Body'den alinan bloks header'lari (asil session degerleri burada olabilir)
    try:
        from app_core.session_state import update_session, update_session_from_body
        update_session(username, response.headers)
        update_session_from_body(username, yeni)
        logger.info("Session state login'den guncellendi: @%s", username)
    except Exception as e:
        logger.warning("Session state güncelleme hatasi: %s", e)

    from app_core.storage import save_token_data
    save_token_data(
        {
            "token": bearer_token,
            "android_id_yeni": android_id_yeni,
            "user_agent": selected_user_agent,
            "device_id": selected_device_id,
        }
    )

    return bearer_token, android_id_yeni, selected_user_agent, selected_device_id
