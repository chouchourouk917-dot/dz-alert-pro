import os
import time
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ لازم تحط TELEGRAM_TOKEN و CHAT_ID في Render")
else:
    send_telegram(f"🚀 *DZ ALERT PRO شغال* ✅\n\nID: {CHAT_ID}\nالبوت راه مربوط مع Render و خدام 100%")
    print("Bot started...")
    while True:
        time.sleep(60)
