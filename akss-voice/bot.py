#!/usr/bin/env python3
"""
AKSS Voice — Rasmiy Telegram Boti
Muhammad al-Xorazmiy nomidagi ixtisoslashtirilgan maktab (Andijon)
"""
import os
import sys
import json
import time
import urllib.request
import urllib.parse

# Bot tokenini o'rnating (yoki .env / atrof-muhit o'zgaruvchisidan olinadi)
# Telegramda @BotFather ga borib /newbot buyrug'i orqali olingan token
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://your-domain.uz/voice.html")

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

def api_call(method, payload=None):
    url = f"{API_BASE}/{method}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception as e:
        print(f"[Xatolik] {method}: {e}")
        return None

def send_welcome(chat_id, first_name):
    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>!\n\n"
        "🏛 <b>AKSS Voice</b> — Muhammad al-Xorazmiy nomidagi ixtisoslashtirilgan maktabining "
        "<b>O'quvchilar Kengashi (Student Council)</b> rasmiy anonim takliflar va muammolar platformasiga xush kelibsiz!\n\n"
        "📌 <b>Bu yerda siz:</b>\n"
        "• Maktabdagi har qanday kamchilik (Wi-Fi, oshxona, sharoit) bo'yicha anonim taklif qoldirishingiz;\n"
        "• Boshqa o'quvchilar takliflariga ovoz berishingiz mumkin.\n\n"
        "⚡ <b>50 ta ovoz</b> to'plagan har bir taklif Student Council tomonidan dushanba kuni "
        "<b>to'g'ridan-to'g'ri maktab direktoriga</b> rasmiy hisobot sifatida taqdim etiladi.\n\n"
        "Quyidagi tugmani bosing va platformani oching 👇"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📢 AKSS Voice Portalini Ochish",
                    "web_app": {"url": WEB_APP_URL}
                }
            ],
            [
                {
                    "text": "ℹ️ Student Council Haqida",
                    "callback_data": "about_council"
                }
            ]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": welcome_text,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    }
    api_call("sendMessage", payload)

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("=" * 60)
        print("⚠️ DIQQAT: TELEGRAM_BOT_TOKEN o'rnatilmagan!")
        print("1. Telegramda @BotFather ga boring")
        print("2. /newbot buyrug'ini bering va yangi bot oching")
        print("3. Olingan tokenni quyidagicha o'rnating:")
        print("   export TELEGRAM_BOT_TOKEN='sizning_tokeningiz'")
        print("   python3 bot.py")
        print("=" * 60)
        sys.exit(1)

    print(f"🤖 AKSS Voice Telegram Boti ishga tushmoqda...")
    offset = 0

    while True:
        try:
            updates = api_call("getUpdates", {"offset": offset, "timeout": 20})
            if updates and updates.get("ok"):
                for item in updates.get("result", []):
                    offset = item["update_id"] + 1
                    msg = item.get("message")
                    if msg:
                        text = msg.get("text", "")
                        chat_id = msg["chat"]["id"]
                        first_name = msg["from"].get("first_name", "O'quvchi")

                        if text.startswith("/start"):
                            send_welcome(chat_id, first_name)
                    
                    # Callbacks
                    cb = item.get("callback_query")
                    if cb:
                        cb_id = cb["id"]
                        cb_data = cb.get("data")
                        cb_chat = cb["message"]["chat"]["id"]
                        if cb_data == "about_council":
                            api_call("answerCallbackQuery", {"callback_query_id": cb_id})
                            api_call("sendMessage", {
                                "chat_id": cb_chat,
                                "text": "🏛 <b>Muhammad al-Xorazmiy AKSS O'quvchilar Kengashi</b>\n\nBizning maqsadimiz — har bir iqtidorli o'quvchining fikri inobatga olinadigan, qulay va ilg'or ta'lim muhitini birgalikda yaratishdir.",
                                "parse_mode": "HTML"
                            })
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nTo'xtatildi.")
            break
        except Exception as e:
            print(f"Loop xatoligi: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
