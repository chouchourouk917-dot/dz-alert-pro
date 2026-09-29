import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

@app.route('/')
def home():
    return "DZ ALERT PRO is running ✅"

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ ماكانش توكن")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data, timeout=10)
        print(f"Sent: {msg[:50]}")
    except Exception as e:
        print(f"Telegram error: {e}")

def bot_loop():
    time.sleep(5)
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ لازم تحط TELEGRAM_TOKEN و CHAT_ID في Render")
        return
    
    send_telegram(f"🚀 *DZ ALERT PRO شغال (FREE)* ✅\n\nID: {CHAT_ID}\nالبوت راه خدام باطل 100% على Render!")
    print("Bot started in FREE mode...")
    
    while True:
        print("Scanning market...")
        time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
