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
LAST_ALERTS = {}

SCAN_INTERVAL = 120
MIN_VOLUME_USDT = 5000000
PUMP_THRESHOLD = 5.0
DUMP_THRESHOLD = -5.0
ALERT_COOLDOWN = 3600

def send_telegram(msg):
    global MESSAGE_COUNT
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.error("❌ ماكانش توكن")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        r = requests.post(url, data=data, timeout=15)
        if r.status_code == 200:
            MESSAGE_COUNT += 1
            return True
        else:
            logger.error(f"Telegram error {r.status_code}: {r.text[:100]}")
            return False
    except Exception as e:
        logger.error(f"Telegram exception: {e}")
        return False

def get_top_100_symbols():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=20)
        data = r.json()
        stable = ["USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP"]
        filtered = []
        for t in data:
            sym = t.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            base = sym.replace("USDT", "")
            if base in stable:
                continue
            if "UP" in sym or "DOWN" in sym or "BEAR" in sym or "BULL" in sym:
                continue
            try:
                vol = float(t.get("quoteVolume", 0))
                if vol < MIN_VOLUME_USDT:
                    continue
                filtered.append({
                    "symbol": sym,
                    "price": float(t.get("lastPrice", 0)),
                    "change": float(t.get("priceChangePercent", 0)),
                    "volume": vol,
                    "high": float(t.get("highPrice", 0)),
                    "low": float(t.get("lowPrice", 0))
                })
            except:
                continue
        filtered.sort(key=lambda x: x["volume"], reverse=True)
        top100 = filtered[:100]
        logger.info(f"✅ جاب {len(top100)} عملة - أكبر حجم: {top100[0]['symbol']} ${top100[0]['volume']/1e6:.1f}M")
        return top100
    except Exception as e:
        logger.error(f"❌ Error get_top_100: {e}")
        return []

def analyze_coin(coin):
    sym = coin["symbol"]
    change = coin["change"]
    price = coin["price"]
    vol = coin["volume"]
    high = coin["high"]
    low = coin["low"]
    now = time.time()
    if sym in LAST_ALERTS and now - LAST_ALERTS[sym] < ALERT_COOLDOWN:
        return None
    dist_from_low = ((price - low) / low * 100) if low > 0 else 0
    dist_from_high = ((high - price) / high * 100) if high > 0 else 0
    msg = None
    if change >= 8:
        msg = f"🚀 *PUMP قوي!* {sym}\n\n💰 السعر: `${price}`\n📈 24h: `+{change:.2f}%`\n📊 حجم: `${vol/1e6:.1f}M`\n🔼 من القاع: `+{dist_from_low:.1f}%`\n\n⚠️ صعود قوي - انتبه للتصحيح!"
    elif change <= -7:
        msg = f"📉 *DUMP - فرصة شراء؟* {sym}\n\n💰 السعر: `${price}`\n📉 24h: `{change:.2f}%`\n📊 حجم: `${vol/1e6:.1f}M`\n🔽 من القمة: `-{dist_from_high:.1f}%`\n\n💡 نازل بزاف - راقبو للارتداد!"
    elif change >= PUMP_THRESHOLD and dist_from_low >= 3 and dist_from_low <= 15:
        msg = f"⚡ *إشارة ارتداد* {sym}\n\n💰 `${price}` | 📈 `+{change:.2f}%`\n📊 حجم `${vol/1e6:.1f}M`\n📍 طالع `+{dist_from_low:.1f}%` من قاع اليوم\n\n👀 بداية حركة!"
    elif dist_from_low <= 2 and vol > 20000000 and change > -2:
        msg = f"🔵 *قرب القاع + حجم* {sym}\n\n💰 `${price}` | 24h: `{change:+.2f}%`\n📊 حجم عالي: `${vol/1e6:.1f}M`\n📍 قريب من قاع اليوم `({dist_from_low:.1f}%)`\n\n📌 تجميع محتمل"
    if msg:
        LAST_ALERTS[sym] = now
        tv_symbol = f"BINANCE:{sym}"
        msg += f"\n\n🔗 [TradingView](https://www.tradingview.com/chart/?symbol={tv_symbol}) | [Binance](https://www.binance.com/en/trade/{sym})"
        return msg
    return None

@app.route('/')
def home():
    uptime = datetime.now() - BOT_START_TIME
    return f"""
    <h1>🚀 DZ CRYPTO ALERT - 100 COINS ✅</h1>
    <p><b>Status:</b> Scanning 100 coins</p>
    <p><b>Uptime:</b> {str(uptime).split('.')[0]}</p>
    <p><b>Messages:</b> {MESSAGE_COUNT}</p>
    <p><b>Mode:</b> PUMP/DUMP + Bottom Reversal</p>
    <p><a href='/health'>/health</a> | <a href='/top100'>/top100</a></p>
    """

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "mode": "CRYPTO_100",
        "uptime": int((datetime.now() - BOT_START_TIME).total_seconds()),
        "messages_sent": MESSAGE_COUNT,
        "scanning": 100,
        "telegram": bool(TELEGRAM_TOKEN and CHAT_ID)
    })

@app.route('/top100')
def top100():
    coins = get_top_100_symbols()
    return jsonify(coins[:20])

def bot_loop():
    logger.info("⏳ Crypto Bot 100 coins starting in 10s...")
    time.sleep(10)
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.error("❌ لازم TELEGRAM_TOKEN و CHAT_ID")
        return
    send_telegram(
        f"🚀 *DZ CRYPTO ALERT - 100 عملة شغال ✅*\n\n"
        f"🕐 Started: {datetime.now().strftime('%H:%M:%S')}\n"
        f"🪙 يراقب: *أقوى 100 عملة USDT* حسب الحجم\n"
        f"⏱️ كل: {SCAN_INTERVAL//60} دقايق\n"
        f"📊 الإشارات:\n"
        f"• 🚀 PUMP > +8%\n"
        f"• 📉 DUMP < -7% (فرصة)\n"
        f"• ⚡ ارتداد من القاع\n"
        f"• 🔵 تجميع قرب القاع\n\n"
        f"✅ البوت راه يسكاني درك!"
    )
    scan_count = 0
    while True:
        try:
            scan_count += 1
            logger.info(f"🔍 Scan #{scan_count} - جلب 100 عملة...")
            coins = get_top_100_symbols()
            if not coins:
                logger.warning("⚠️ ما جابش عملات، يعاود بعد 30ثا")
                time.sleep(30)
                continue
            alerts = 0
            for coin in coins:
                signal = analyze_coin(coin)
                if signal:
                    send_telegram(signal)
                    alerts += 1
                    time.sleep(1.5)
            logger.info(f"✅ Scan #{scan_count} كمل - {len(coins)} عملة، {alerts} إشارة")
            if scan_count % 10 == 0:
                top_movers = sorted(coins, key=lambda x: x["change"], reverse=True)[:3]
                worst = sorted(coins, key=lambda x: x["change"])[:3]
                summary = f"📊 *ملخص كل {scan_count} سكانات - Top 100*\n\n"
                summary += "🔥 الأكثر صعود:\n"
                for c in top_movers:
                    summary += f"• {c['symbol']}: `+{c['change']:.1f}%`\n"
                summary += "\n❄️ الأكثر نزول:\n"
                for c in worst:
                    summary += f"• {c['symbol']}: `{c['change']:.1f}%`\n"
                summary += f"\n⏱️ Uptime: {str(datetime.now() - BOT_START_TIME).split('.')[0]}"
                send_telegram(summary)
            time.sleep(SCAN_INTERVAL)
        except Exception as e:
            logger.error(f"❌ Error in loop: {e}")
            time.sleep(30)

if not hasattr(app, 'bot_thread_started'):
    thread = threading.Thread(target=bot_loop, daemon=True)
    thread.start()
    app.bot_thread_started = True
    logger.info("🧵 Crypto 100 bot thread started")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
