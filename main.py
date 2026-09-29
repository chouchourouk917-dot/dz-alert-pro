import os
import time
import threading
import logging
import requests
from flask import Flask, jsonify
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BOT_START_TIME = datetime.now()
MESSAGE_COUNT = 0

def send_telegram(msg):
    global MESSAGE_COUNT
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.error("❌ ماكانش توكن - لازم تحطو في Render > Environment")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=data, timeout=15)
        if r.status_code == 200:
            MESSAGE_COUNT += 1
            logger.info(f"✅ Telegram sent ({MESSAGE_COUNT})")
            return True
        else:
            logger.error(f"❌ Telegram error {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"❌ Telegram exception: {e}")
        return False

@app.route('/')
def home():
    uptime = datetime.now() - BOT_START_TIME
    return f"""
    <h1>DZ ALERT PRO ✅</h1>
    <p><b>Status:</b> Running FREE MODE - PRO</p>
    <p><b>Uptime:</b> {str(uptime).split('.')[0]}</p>
    <p><b>Messages sent:</b> {MESSAGE_COUNT}</p>
    <p><b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <hr>
    <p>Bot is alive and scanning...</p>
    <p><a href='/health'>/health</a> | <a href='/ping'>/ping</a></p>
    """

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "mode": "FREE_PRO",
        "uptime_seconds": int((datetime.now() - BOT_START_TIME).total_seconds()),
        "messages_sent": MESSAGE_COUNT,
        "telegram_configured": bool(TELEGRAM_TOKEN and CHAT_ID)
    })

@app.route('/ping')
def ping():
    return "pong"

def scan_dz_tenders():
    logger.info("🔍 Scanning DZ tenders... (placeholder - ready for real scraper)")
    return []

def bot_loop():
    logger.info("⏳ Bot loop starting in 5 sec...")
    time.sleep(5)
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.error("❌ لازم تحط TELEGRAM_TOKEN و CHAT_ID في Render > Environment")
        return
    uptime_str = BOT_START_TIME.strftime('%H:%M:%S')
    send_telegram(
        f"🚀 *DZ ALERT PRO شغال (FREE) ✅*\n\n"
        f"🕐 Started: {uptime_str}\n"
        f"🆔 ID: {CHAT_ID}\n\n"
        f"✅ البوت راه خدام باطل 100% على Render!\n"
        f"🔧 Mode: PRO + gunicorn\n"
        f"💓 Health: /health"
    )
    logger.info("✅ Bot started in PRO mode with gunicorn!")
    heartbeat_counter = 0
    while True:
        try:
            heartbeat_counter += 1
            logger.info(f"💓 Bot alive - scan #{heartbeat_counter} | Uptime: {str(datetime.now() - BOT_START_TIME).split('.')[0]}")
            tenders = scan_dz_tenders()
            if tenders:
                for tender in tenders:
                    send_telegram(tender)
            time.sleep(60)
        except Exception as e:
            logger.error(f"❌ Error in bot_loop: {e}")
            time.sleep(30)

if not hasattr(app, 'bot_thread_started'):
    thread = threading.Thread(target=bot_loop, daemon=True)
    thread.start()
    app.bot_thread_started = True
    logger.info("🧵 Bot thread started")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
