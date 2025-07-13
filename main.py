from flask import Flask
import threading
import requests
import traceback
import time
import os
import base64
import json

from dotenv import load_dotenv

load_dotenv()

if os.getenv("GOOGLE_CREDENTIALS_B64"):
    try:
        creds_path = "credentials.json"
        with open(creds_path, "wb") as f:
            f.write(base64.b64decode(os.getenv("GOOGLE_CREDENTIALS_B64")))

        # ✅ Add check: try loading the JSON
        with open(creds_path, "r") as f:
            data = json.load(f)
            print("✅ credentials.json loaded successfully")
    except Exception as e:
        print("❌ Failed to decode/write credentials.json:", e)

from sheet_logger import log_signal

# === Configuration ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID", "0"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "0"))

API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'
LAST_UPDATE_ID = None

# Storage of sent signals awaiting confirmation
pending_signals = []

# === Flask Setup ===
app = Flask(__name__)


@app.route('/')
def home():
    return "✅ Signal Splitter Bot is running!"


# === Message Splitter ===
def split_message(msg):
    blocks = msg.split("#Symbol:")
    return [f"#Symbol:{b.strip()}" for b in blocks if b.strip()]


# === Telegram Poller ===
def poll_telegram():
    global LAST_UPDATE_ID
    global pending_signals

    print("🟢 Bot started polling...")

    while True:
        try:
            res = requests.get(f'{API_URL}/getUpdates',
                               params={
                                   'timeout':
                                   30,
                                   'offset':
                                   LAST_UPDATE_ID +
                                   1 if LAST_UPDATE_ID else None
                               })
            res.raise_for_status()

            data = res.json()
            if not data.get("ok"):
                print("❌ API Error:", data)
                continue

            for result in data['result']:
                LAST_UPDATE_ID = result['update_id']
                message = result.get('message') or result.get('channel_post')
                if not message:
                    print("⚠️ Skipped: No message or channel_post.")
                    continue

                chat_id = message.get('chat', {}).get('id')
                msg_text = message.get('text')

                if not msg_text:
                    print("⚠️ Skipped: No text.")
                    continue

                # ✅ MT4 Confirmation
                if chat_id == TARGET_CHAT_ID and "Order Success" in msg_text:
                    print("📩 MT4 success confirmation received!")
                    if pending_signals:
                        confirmed = pending_signals.pop(0)
                        try:
                            log_signal(confirmed['text'], chat_id,
                                       "Order Confirmed")
                            print("✅ Logged signal to Google Sheets.")
                        except Exception as log_err:
                            print("❌ Logging error:", log_err)
                    else:
                        print("⚠️ No pending signal to confirm.")
                    continue

                # ✅ Source Signal
                if chat_id != SOURCE_CHAT_ID:
                    print(f"⚠️ Skipped: Message from unknown chat ({chat_id})")
                    continue

                print(f"\n📥 New signal received:\n{msg_text}")
                blocks = split_message(msg_text)
                print(f"✂️ Signal split into {len(blocks)} parts.")

                for i, block in enumerate(blocks):
                    try:
                        resp = requests.post(f'{API_URL}/sendMessage',
                                             json={
                                                 'chat_id': TARGET_CHAT_ID,
                                                 'text': block
                                             })
                        resp.raise_for_status()
                        pending_signals.append({
                            'text': block,
                            'sent_at': time.time()
                        })
                        print(f"✅ Sent part {i+1}: {block[:40]}...")
                    except Exception as send_err:
                        print(f"❌ Failed to send part {i+1}")
                        print("⛔ Error:", send_err)

        except Exception:
            print("🚨 Polling error:\n", traceback.format_exc())
            now = time.time()
            pending_signals = [
                s for s in pending_signals if now - s['sent_at'] < 600
            ]
            time.sleep(10)


# === Launch Bot + Web Server ===
if __name__ == "__main__":
    threading.Thread(target=poll_telegram, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
