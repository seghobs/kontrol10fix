import os
import secrets
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, "app.db")

# Legacy JSON paths (one-time migration only)
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
TOKENS_FILE = os.path.join(BASE_DIR, "tokens.json")
EXEMPTIONS_FILE = os.path.join(BASE_DIR, "exemptions.json")

# Kalıcı ve rastgele SECRET_KEY üretimi
secret_key_file = os.path.join(BASE_DIR, "secret.key")
if os.path.exists(secret_key_file):
    try:
        with open(secret_key_file, "r") as f:
            generated_secret_key = f.read().strip()
    except Exception:
        generated_secret_key = secrets.token_hex(32)
else:
    generated_secret_key = secrets.token_hex(32)
    try:
        with open(secret_key_file, "w") as f:
            f.write(generated_secret_key)
    except Exception:
        pass

# Admin şifresinin belirlenmesi
active_admin_password = os.getenv("ADMIN_PASSWORD", "seho").strip()

env_secret_key = os.getenv("SECRET_KEY", "").strip()
if not env_secret_key or env_secret_key == "sbt_seghob_gizli_anahtar_12345":
    active_secret_key = generated_secret_key
else:
    active_secret_key = env_secret_key

IG_APP_ID = "567067343352427"


class BaseConfig:
    import datetime
    APP_ENV = os.getenv("APP_ENV", "dev")
    ADMIN_PASSWORD = active_admin_password
    SECRET_KEY = active_secret_key
    HEALTH_CHECK_ENABLED = os.getenv("HEALTH_CHECK_ENABLED", "1") == "1"
    HEALTH_CHECK_INTERVAL_SECONDS = int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "180"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=365)


class DevConfig(BaseConfig):
    DEBUG = True


class StageConfig(BaseConfig):
    DEBUG = False


class ProdConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


def get_config():
    env = os.getenv("APP_ENV", "dev").lower().strip()
    if env == "prod":
        return ProdConfig
    if env == "stage":
        return StageConfig
    return DevConfig


_active_config = get_config()
ADMIN_PASSWORD = _active_config.ADMIN_PASSWORD
SECRET_KEY = _active_config.SECRET_KEY
