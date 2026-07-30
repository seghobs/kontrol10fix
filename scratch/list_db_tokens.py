import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app_core.storage import load_tokens

tokens = load_tokens()
print(f"Total tokens in DB: {len(tokens)}")
for t in tokens:
    print(f"Username: {t.get('username')}, Is Active: {t.get('is_active')}, Status: {t.get('status')}, Logout Reason: {t.get('logout_reason')}")
