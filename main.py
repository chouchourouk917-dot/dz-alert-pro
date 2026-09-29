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
PREV_DATA = {}
RECENT_SCANS = []

SCAN_INTERVAL = 60
MIN_VOLUME_USDT = 2000000
ALERT_COOLDOWN = 900

def send_telegram(msg):
    global MESSAGE_COUNT
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        r = requests.post(url, data=data, timeout=15)
        if r.status_code == 200:
            MESSAGE_COUNT += 1
            return True
        return False
    except Exception as e:
        logger.error(f"Telegram: {e}")
        return False

def get_top_100_symbols():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=20)
        data = r.json()
        stable = ["USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "EUR", "USDD"]
        filtered = []
        for t in data:
            sym = t.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            base = sym.replace("USDT", "")
            if base in stable:
                continue
            if any(x in sym for x in ["UP", "DOWN", "BEAR", "BULL"]):
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
        return filtered[:100]
    except Exception as e:
        logger.error(f"Error get_top_100: {e}")
        return []

def analyze_coin_pre_pump(coin):
    sym = coin["symbol"]
    price = coin["price"]
    vol = coin["volume"]
    change = coin["change"]
    high = coin["high"]
    low = coin["low"]
    now = time.time()

    if sym in LAST_ALERTS and now - LAST_ALERTS[sym] < ALERT_COOLDOWN:
        return None

    dist_from_low = ((price - low) / low * 100) if low > 0 else 0
    dist_from_high = ((high - price) / high * 100) if high > 0 else 0

    short_change = 0
    vol_2min = 0
    if sym in PREV_DATA:
        prev = PREV_DATA[sym]
        prev_price = prev["price"]
        if prev_price > 0:
            short_change = (price - prev_price) / prev_price * 100
        vol_2min = vol - prev["volume"]
        if vol_2min < 0:
            vol_2min = 0

    PREV_DATA[sym] = {"price": price, "volume": vol, "time": now}

    msg = None

    if short_change >= 0.8 and vol_2min > 300000 and dist_from_low < 12 and change > -3:
        msg = f"🚀 *رايحة تضخ! PRE-PUMP* {sym}\n\n💰 `${price}`\n⚡ طلعت `+{short_change:.2f}%` في دقيقة!\n📊 حجم دقيقة: `${vol_2min/1000:.0f}K`\n📈 24h: `{change:+.2f}%`\n📍 من القاع: `+{dist_from_low:.1f}%`\n\n🔥 *ادخل درك قبل ما تطير!*"
    elif vol_2min > 2000000:
        msg = f"💥 *انفجار حجم!* {sym}\n\n💰 `${price}` | `{change:+.2f}%`\n📊 `${vol_2min/1e6:.2f}M` في دقيقة!\n⚡ تغير: `{short_change:+.2f}%`\n\n👀 حيتان دخلو!"
    elif dist_from_low < 4 and short_change > 0.3 and vol > 10000000:
        msg = f"🔵 *تجميع + بداية ضخ* {sym}\n\n💰 `${price}`\n📍 قريبة من القاع `{dist_from_low:.1f}%`\n⚡ `+{short_change:.2f}%` في دقيقة\n📊 حجم 24h: `${vol/1e6:.1f}M`\n\n📌 راقبها درك!"
    elif short_change >= 0.5 and change > 2 and vol > 5000000:
        msg = f"⚡ *صعود متواصل* {sym}\n\n💰 `${price}`\n📈 `+{short_change:.2f}%` /دقيقة\n📈 24h: `+{change:.2f}%`\n📊 `${vol/1e6:.1f}M`\n\n🚀 مستمرة!"
    elif change >= 5:
        msg = f"🚀 *PUMP!* {sym}\n\n💰 `${price}`\n📈 `+{change:.2f}%`\n📊 `${vol/1e6:.1f}M`\n\n⚠️ طارت!"
    elif change <= -5 and dist_from_high < 15:
        msg = f"📉 *نزول قوي - فرصة؟* {sym}\n\n💰 `${price}` | `{change:.2f}%`\n🔽 من القمة: `{dist_from_high:.1f}%`\n📊 `${vol/1e6:.1f}M`"

    if msg:
        LAST_ALERTS[sym] = now
        msg += f"\n\n🔗 [TradingView](https://www.tradingview.com/chart/?symbol=BINANCE:{sym}) | [Binance](https://www.binance.com/en/trade/{sym})"
        return msg
    return None

@app.route('/')
def home():
    uptime = datetime.now() - BOT_START_TIME
    return f"""
    <html><head><meta http-equiv="refresh" content="30"><title>DZ Alert Pro</title></head>
    <body style="font-family:Arial;background:#0a0a0a;color:#00ff88;padding:20px">
    <h1>🚀 DZ CRYPTO ALERT - PRE-PUMP HUNTER ✅</h1>
    <p><b>Status:</b> يصيد العملات قبل ما تضخ!</p>
    <p><b>Uptime:</b> {str(uptime).split('.')[0]}</p>
    <p><b>Messages:</b> {MESSAGE_COUNT}</p>
    <p><b>Scan:</b> كل 1 دقيقة - 100 عملة</p>
    <p><b>Mode:</b> PRE-PUMP DETECTOR 🔥</p>
    <p><a href='/health' style="color:#0ff">/health</a> | <a href='/top100' style="color:#0ff">/top100</a> | <a href='/live' style="color:#ff0">/live LIVE</a></p>
    <hr><p>آخر سكان: {RECENT_SCANS[-1] if RECENT_SCANS else '...'} </p>
    </body></html>
    """

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "mode": "PRE_PUMP_HUNTER",
        "uptime": int((datetime.now() - BOT_START_TIME).total_seconds()),
        "messages_sent": MESSAGE_COUNT,
        "scanning": 100,
        "interval_sec": SCAN_INTERVAL,
        "tracked": len(PREV_DATA)
    })

@app.route('/top100')
def top100():
    coins = get_top_100_symbols()
    return jsonify(coins[:20])

@app.route('/live')
def live():
    coins = get_top_100_symbols()
    html = "<html><head><meta http-equiv='refresh' content='15'><title>LIVE</title></head><body style='background:#111;color:#fff;font-family:monospace;padding:10px'>"
    html += "<h2>🔴 LIVE - يراقب الضخ لحظيا (يتحدث كل 15 ثا)</h2>"
    html += f"<p>Messages: {MESSAGE_COUNT} | Tracked: {len(PREV_DATA)} | Uptime: {str(datetime.now()-BOT_START_TIME).split('.')[0]}</p><table border=1 style='border-collapse:collapse;width:100%'>"
    html += "<tr><th>Symbol</th><th>Price</th><th>24h%</th><th>1m%</th><th>Vol 1m</th><th>From Low</th><th>Status</th></tr>"
    for c in coins[:50]:
        sym = c["symbol"]
        short = 0
        vol1 = 0
        if sym in PREV_DATA:
            prev = PREV_DATA[sym]
            if prev["price"]>0:
                short = (c["price"]-prev["price"])/prev["price"]*100
            vol1 = c["volume"]-prev["volume"]
            if vol1<0: vol1=0
        dist_low = ((c["price"]-c["low"])/c["low"]*100) if c["low"]>0 else 0
        status = "💤"
        if short >= 0.8 and dist_low<12:
            status = "🚀 رايحة تضخ!"
        elif vol1>2000000:
            status = "💥 انفجار حجم"
        elif short>=0.5:
            status="⚡ صعود"
        html += f"<tr><td>{sym}</td><td>${c['price']}</td><td>{c['change']:+.2f}%</td><td>{short:+.2f}%</td><td>${vol1/1000:.0f}K</td><td>{dist_low:.1f}%</td><td>{status}</td></tr>"
    html += "</table><p><a href='/' style='color:#0ff'>Back</a></p></body></html>"
    return html

def bot_loop():
    logger.info("⏳ PRE-PUMP Hunter starting...")
    time.sleep(8)
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.error("❌ لازم التوكن")
        return
    send_telegram(
        f"🎯 *DZ PRE-PUMP HUNTER شغال!* 🔥\n\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}\n"
        f"🪙 يراقب: *100 عملة* كل *1 دقيقة*\n"
        f"🧠 يصيد:\n"
        f"• 🚀 عملة رايحة تضخ (طلعت +0.8% في دقيقة + حجم)\n"
        f"• 💥 انفجار حجم فجأة\n"
        f"• 🔵 تجميع قرب القاع\n"
        f"• ⚡ صعود متواصل\n\n"
        f"📡 تابع LIVE: /live\n"
        f"✅ راه يتعلم أسعار العملات درك - أول إشارة بعد دقيقتين!"
    )
    scan_count = 0
    while True:
        try:
            scan_count += 1
            coins = get_top_100_symbols()
            if not coins:
                time.sleep(10)
                continue
            if scan_count == 1:
                for c in coins:
                    PREV_DATA[c["symbol"]] = {"price": c["price"], "volume": c["volume"], "time": time.time()}
                logger.info("📊 أول سكان - خزن الأسعار")
                RECENT_SCANS.append(f"Scan {scan_count}: Init {len(coins)} coins")
                time.sleep(SCAN_INTERVAL)
                continue
            alerts = 0
            for coin in coins:
                signal = analyze_coin_pre_pump(coin)
                if signal:
                    send_telegram(signal)
                    alerts += 1
                    time.sleep(1.2)
            msg_scan = f"Scan {scan_count}: {len(coins)} coins, {alerts} alerts - {datetime.now().strftime('%H:%M:%S')}"
            RECENT_SCANS.append(msg_scan)
            if len(RECENT_SCANS) > 20:
                RECENT_SCANS.pop(0)
            logger.info(f"✅ {msg_scan}")
            time.sleep(SCAN_INTERVAL)
        except Exception as e:
            logger.error(f"❌ Loop error: {e}")
            time.sleep(15)

if not hasattr(app, 'bot_thread_started'):
    thread = threading.Thread(target=bot_loop, daemon=True)
    thread.start()
    app.bot_thread_started = True
    logger.info("🧵 PRE-PUMP Hunter thread started")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
