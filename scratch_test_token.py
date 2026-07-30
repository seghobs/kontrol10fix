import sqlite3
from app_core.instagram_api import fetch_current_user
conn = sqlite3.connect('app.db')
cursor = conn.cursor()
cursor.execute("SELECT username, token, user_agent, android_id_yeni, device_id FROM tokens WHERE username='kendin_yap332'")
row = cursor.fetchone()
if row:
    print('Token bulundu, test ediliyor...')
    try:
        res = fetch_current_user(row[1], row[2], row[3], row[4])
        print('Sonuc:', res)
    except Exception as e:
        print('Hata:', e)
else:
    print('Token DBde yok!')
