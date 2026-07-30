import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_core.storage import init_storage, load_tokens, get_audit_logs

init_storage()
tokens = load_tokens(include_deleted=True)
for t in tokens:
    print(f"Token Username: {t.get('username')}, is_active: {t.get('is_active')}, relogin_attempts: {t.get('relogin_attempts')}, logout_reason: {t.get('logout_reason')}")

print("\n--- Recent Audit Logs ---")
logs = get_audit_logs(limit=10)
for log in logs:
    print(f"Action: {log.get('action')}, entity_id: {log.get('entity_id')}, details: {log.get('details')}, created_at: {log.get('created_at')}")
