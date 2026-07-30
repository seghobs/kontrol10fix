import sys
import logging
from datetime import datetime
from app_core.storage import upsert_token

logging.basicConfig(level=logging.DEBUG)

def add_token_to_db():
    token_dict = {
        "username": "kendin_yap332",
        "full_name": "kendin yap",
        "password": "8136098ss",
        "token": "Bearer IGT:2:eyJkc191c2VyX2lkIjoiNDgyNDExNjEzNTYiLCJzZXNzaW9uaWQiOiI0ODI0MTE2MTM1NiUzQWVwMkpTMzNyWGptRnExJTNBOSUzQUFZaEctLU1MY3FpeDhfNWNKQWdXZ3I4U21vNHByR0lxcmpHOFFXOVZqQSJ9",
        "android_id_yeni": "8ea7f988cd1f3355",
        "user_agent": "Instagram 422.0.0.44.64 Android (28/9; 240dpi; 720x1280; Asus; ASUS_I003DD; ASUS_I003DD; intel; tr_TR; 916494035)",
        "device_id": "80536d23-8663-4731-bda8-0cdff0ad596d",
        "is_active": True,
        "added_at": datetime.now().isoformat()
    }
    
    success = upsert_token(token_dict)
    if success:
        print("Token veritabanına başarıyla eklendi.")
    else:
        print("Token eklenirken bir hata oluştu.")

if __name__ == "__main__":
    add_token_to_db()
