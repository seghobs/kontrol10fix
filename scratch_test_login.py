import sys
import logging
from log_in import giris_yap

logging.basicConfig(level=logging.DEBUG)

def test_login():
    username = "kendin_yap332"
    password = "8136098ss"
    android_id = "8ea7f988cd1f3355"
    user_agent = "Instagram 422.0.0.44.64 Android (28/9; 240dpi; 720x1280; Asus; ASUS_I003DD; ASUS_I003DD; intel; tr_TR; 916494035)"
    device_id = "80536d23-8663-4731-bda8-0cdff0ad596d"
    
    try:
        bearer_token, android_id_yeni, selected_user_agent, selected_device_id = giris_yap(
            username, password, android_id, user_agent, device_id
        )
        print("\n--- BAŞARILI ---")
        print(f"Token: {bearer_token}")
    except Exception as e:
        print("\n--- HATA ---")
        print(f"Hata detayı: {e}")

if __name__ == "__main__":
    test_login()
