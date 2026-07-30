import logging
import os
import time
import pytz
from datetime import datetime
import flask.cli

# Tumuyle GMT+3 (Turkiye) saat dilimi kullanmasi icin zorlama
os.environ['TZ'] = 'Europe/Istanbul'
if hasattr(time, 'tzset'):
    time.tzset()

# Log basliklarinin da GMT+3'e donusmesi icin converter degisimi
def gmt3_time(*args):
    return datetime.now(pytz.timezone('Europe/Istanbul')).timetuple()

logging.Formatter.converter = gmt3_time

from app_core import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = create_app()

from app_core.storage import init_storage
init_storage()

from app_core.automation import start_automation
start_automation()


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 3434

    flask.cli.show_server_banner = lambda *args, **kwargs: None
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    print(f"Sunucu adresi: http://{host}:{port}")
    app.run(host=host, port=port, debug=True, use_reloader=True)
