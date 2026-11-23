#!/usr/bin/env python3
"""
AKSS Voice — Rasmiy Telegram Boti (Mini App & Student Council Hub)
Muhammad al-Xorazmiy nomidagi ixtisoslashtirilgan maktab (Andijon)
"""
import os
import sys
import json
import time
import sqlite3
import urllib.request
import urllib.parse

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
DB_PATH = os.path.join(os.path.dirname(__file__), "voice.db")

def load_config():
    config = {
        "bot_token": os.getenv("9273166206:AAGjhSkH1qoWIrBBIA1xhtDLFJfMyrACAFc", "").strip(),
        "web_app_url": os.getenv("WEB_APP_URL", "http://localhost:3000/voice.html").strip()
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if saved.get("bot_token"):
                    config["bot_token"] = saved["bot_token"].strip()
                if saved.get("web_app_url"):
                    config["web_app_url"] = saved["web_app_url"].strip()
        except Exception as e:
            print(f"[Ogohlantirish] config.json o'qishda xatolik: {e}")
    return config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Ogohlantirish] config.json saqlashda xatolik: {e}")

CONFIG = load_config()
BOT_TOKEN = CONFIG["bot_token"]
WEB_APP_URL = CONFIG["web_app_url"]

def api_call(method, payload=None):
    global BOT_TOKEN
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=35) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else str(e)
        print(f"[Telegram API Xatolik] {method} ({e.code}): {err_body}")
        return None
    except Exception as e:
        if "timed out" in str(e).lower():
            return None
        print(f"[Tarmoq Xatoligi] {method}: {e}")
        return None

def get_db_stats():
    """SQLite bazasidan jonli maktab statistikasini oladi"""
    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM proposals")
        total_props = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM proposals WHERE status = 'resolved'")
        resolved_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM proposals WHERE status = 'council' OR vote_count >= 50")
        council_count = cur.fetchone()[0]
        
        cur.execute("SELECT SUM(vote_count) FROM proposals")
        sum_votes = cur.fetchone()[0] or 0
        
        cur.execute("SELECT title, vote_count FROM proposals ORDER BY vote_count DESC LIMIT 1")
        top_row = cur.fetchone()
        top_title = top_row[0] if top_row else "Hozircha yo'q"
        top_votes = top_row[1] if top_row else 0
        
        conn.close()
        return {
            "total_props": total_props,
            "resolved_count": resolved_count,
            "council_count": council_count,
            "total_votes": sum_votes,
            "top_title": top_title,
            "top_votes": top_votes
        }
    except Exception as e:
        print(f"[Baza xatoligi] {e}")
        return None

def setup_bot_profile(bot_info):
    """
    Bot Telegramda ochilganda chiroyli va rasmiy ko'rinishi uchun
    Tavsif, Buyruqlar va Menyu tugmasini avtomatik sozlaydi.
    """
    bot_name = bot_info.get("first_name", "AKSS Voice")
    username = bot_info.get("username", "bot")
    print(f"⚙️ @{username} profilini avtomatik sozlash...")

    # 1. Chat ochilganda (Start bosishdan oldin) chiqadigan matn
    description_text = (
        "🏛 Muhammad al-Xorazmiy nomidagi ixtisoslashtirilgan maktab (Andijon)\n"
        "O'quvchilar Kengashi (Student Council) rasmiy anonim takliflar va muammolar platformasi.\n\n"
        "📌 Maktabdagi har qanday kamchilik yoki yangi g'oyani 100% anonim qoldiring va ovoz bering.\n\n"
        "⚡ 50 ta haqiqiy ovoz to'plagan har bir masala dushanba kuni direktor stoliga taqdim etiladi!\n\n"
        "Boshlash uchun quyidagi «Start» tugmasini bosing 👇"
    )
    api_call("setMyDescription", {"description": description_text})

    # 2. Qisqa tavsif (Profil oynasida ko'rinadi)
    api_call("setMyShortDescription", {
        "short_description": "AKSS rasmiy anonim takliflar va Student Council portali."
    })

    # 3. Buyruqlar menyusi
    commands = [
        {"command": "start", "description": "Botni ishga tushirish va portal havolasi"},
        {"command": "portal", "description": "AKSS Voice WebApp portalini ochish"},
        {"command": "stats", "description": "Jonli maktab takliflari statistikasi"},
        {"command": "help", "description": "Platforma qoidalari va yordam"}
    ]
    api_call("setMyCommands", {"commands": commands})

    # 4. Doimiy WebApp Menyu tugmasi (Chatning chap pastki burchagidagi tugma)
    api_call("setChatMenuButton", {
        "menu_button": {
            "type": "web_app",
            "text": "📢 AKSS Voice",
            "web_app": {"url": WEB_APP_URL}
        }
    })
    print("✅ Bot profili, tavsifi va Menyu tugmasi muvaffaqiyatli sozlandi!")

def get_keyboards():
    """Asosiy Inline va Reply klaviaturalar"""
    inline_kb = {
        "inline_keyboard": [
            [
                {
                    "text": "🚀 AKSS Voice Portalini Ochish",
                    "web_app": {"url": WEB_APP_URL}
                }
            ],
            [
                {"text": "📊 Jonli Statistika", "callback_data": "btn_stats"},
                {"text": "ℹ️ Qoidalar", "callback_data": "btn_rules"}
            ]
        ]
    }

    reply_kb = {
        "keyboard": [
            [
                {
                    "text": "🚀 AKSS Voice Portalini Ochish",
                    "web_app": {"url": WEB_APP_URL}
                }
            ],
            [
                {"text": "📊 Jonli Statistika"},
                {"text": "ℹ️ Yordam & Qoidalar"}
            ]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

    return inline_kb, reply_kb

def send_welcome(chat_id, first_name):
    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>! 👋\n\n"
        "🏛 <b>AKSS Voice — Muhammad al-Xorazmiy nomidagi ixtisoslashtirilgan maktabi</b>\n"
        "<b>Student Council (O'quvchilar Kengashi)</b> rasmiy anonim takliflar va muammolar platformasiga xush kelibsiz!\n\n"
        "📌 <b>Platforma nima uchun kerak?</b>\n"
        "• <b>100% Anonimlik:</b> Wi-Fi, sinfxona sharoitlari, oshxona yoki darslar bo'yicha hech kimdan cho'chimasdan taklif yozing.\n"
        "• <b>Adolatli Ovoz:</b> Boshqa o'quvchilar ko'tarayotgan takliflarni qo'llab-quvvatlang.\n"
        "• <b>So'rovnomalar:</b> Maktab ma'muriyati va Kengash e'lon qilgan rasmiy so'rovnomalarda ovoz bering.\n\n"
        "⚡ <b>50 ta ovoz yig'ilgan har bir masala</b> dushanba kuni Student Council orqali "
        "<b>to'g'ridan-to'g'ri maktab direktoriga</b> taqdim etiladi.\n\n"
        "Quyidagi tugmani bosing va platformani oching 👇"
    )

    inline_kb, reply_kb = get_keyboards()

    payload = {
        "chat_id": chat_id,
        "text": welcome_text,
        "parse_mode": "HTML",
        "reply_markup": reply_kb
    }
    api_call("sendMessage", payload)

    # Shuningdek to'g'ridan-to'g'ri xabarning ostiga ham yorqin Inline tugma chiqaramiz
    api_call("sendMessage", {
        "chat_id": chat_id,
        "text": "👇 <b>Platformaga o'tish uchun quyidagi tugmani bosing:</b>",
        "parse_mode": "HTML",
        "reply_markup": inline_kb
    })

def send_stats(chat_id):
    stats = get_db_stats()
    if not stats:
        api_call("sendMessage", {
            "chat_id": chat_id,
            "text": "📊 Statistika ma'lumotlari hozircha yuklanmadi.",
            "parse_mode": "HTML"
        })
        return

    text = (
        "📊 <b>AKSS Voice — Jonli Maktab Statistikasi:</b>\n\n"
        f"💡 Jami anonim takliflar: <b>{stats['total_props']} ta</b>\n"
        f"🔥 Direktor stolida (50+ ovoz): <b>{stats['council_count']} ta</b>\n"
        f"🟢 Hal etilgan / Bajarilgan: <b>{stats['resolved_count']} ta</b>\n"
        f"🗳 O'quvchilar bergan ovozlari: <b>{stats['total_votes']} ta</b>\n\n"
        f"🏆 <b>Eng trenddagi taklif:</b>\n"
        f"«<i>{stats['top_title']}</i>» (<b>{stats['top_votes']} ta ovoz</b>)\n\n"
        "Siz ham o'z taklifingizni kiritish uchun portalni oching!"
    )
    inline_kb, _ = get_keyboards()
    api_call("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": inline_kb
    })

def send_help(chat_id):
    help_text = (
        "ℹ️ <b>AKSS Voice Platformasi Qoidalari:</b>\n\n"
        "1. <b>Haqiqiy anonimlik:</b> Ism-familiyangiz, profilingiz yoki telefon raqamingiz hech kimga ko'rinmaydi.\n"
        "2. <b>Odob-axloq:</b> Haqoratli, tuhmat yoki nojo'ya so'zlar avtomatik AI-filtr orqali bloklanadi.\n"
        "3. <b>50 ta Ovoz me'yori:</b> Jiddiy muammolar 50 ta ovoz yig'gach, «Direktor stolida» maqomini oladi va Student Council raisi uni shaxsan direktorga kiritadi.\n"
        "4. <b>Rasmiy javob:</b> Muammo hal etilgach, platformada uning holati «🟢 Hal etildi» deb belgilanadi.\n\n"
        "Savol yoki takliflar uchun Student Council Kengashiga murojaat qilishingiz mumkin."
    )
    inline_kb, _ = get_keyboards()
    api_call("sendMessage", {
        "chat_id": chat_id,
        "text": help_text,
        "parse_mode": "HTML",
        "reply_markup": inline_kb
    })

def main():
    global BOT_TOKEN, WEB_APP_URL

    print("=" * 65)
    print("🤖 AKSS Voice — Telegram Bot Ishga Tushirilmoqda")
    print("=" * 65)

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n⚠️ TELEGRAM_BOT_TOKEN topilmadi!")
        print("1. Telegramda @BotFather ga boring")
        print("2. /newbot buyrug'ini bering va yangi bot oching")
        print("3. Olingan tokenni kiriting (masalan: 7492819482:AAHjK...)")
        try:
            token_input = input("\n👉 Bot Tokenini kiriting: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBekor qilindi.")
            sys.exit(0)

        if not token_input:
            print("❌ Token kiritilmadi. Dastur to'xtatildi.")
            sys.exit(1)

        BOT_TOKEN = token_input
        CONFIG["bot_token"] = BOT_TOKEN
        save_config(CONFIG)
        print("💾 Token config.json fayliga muvaffaqiyatli saqlandi!")

    # Botni tekshirish (getMe)
    bot_info = api_call("getMe")
    if not bot_info or not bot_info.get("ok"):
        print(f"\n❌ Xatolik: Token yaroqsiz yoki Telegram bilan aloqa yo'q!")
        print("Iltimos, tokenni tekshirib qayta urinib ko'ring.")
        sys.exit(1)

    me = bot_info["result"]
    bot_name = me.get("first_name", "Bot")
    username = me.get("username", "bot")
    print(f"\n✅ Bot muvaffaqiyatli ulandi: {bot_name} (@{username})")
    print(f"🌐 WebApp manzili: {WEB_APP_URL}")

    # Bot profili va tavsiflarini sozlash
    setup_bot_profile(me)

    print("\n🚀 Bot ishga tushdi va xabarlarni kutmoqda...")
    print("👉 Telegramda botingizga kiring va «Start» (Boshlash) tugmasini bosing!")
    print("-----------------------------------------------------------------")

    offset = 0
    while True:
        try:
            updates = api_call("getUpdates", {"offset": offset, "timeout": 20})
            if updates and updates.get("ok"):
                for item in updates.get("result", []):
                    offset = item["update_id"] + 1

                    # 1. Oddiy xabarlar
                    msg = item.get("message")
                    if msg:
                        text = msg.get("text", "")
                        chat_id = msg["chat"]["id"]
                        first_name = msg["from"].get("first_name", "O'quvchi")

                        print(f"📩 Yangi xabar: {first_name} ({chat_id}) -> {text}")

                        if text.startswith("/start"):
                            send_welcome(chat_id, first_name)
                        elif text.startswith("/portal") or "portal" in text.lower():
                            inline_kb, _ = get_keyboards()
                            api_call("sendMessage", {
                                "chat_id": chat_id,
                                "text": "🚀 <b>AKSS Voice Portalini ochish uchun quyidagi tugmani bosing:</b>",
                                "parse_mode": "HTML",
                                "reply_markup": inline_kb
                            })
                        elif text.startswith("/stats") or "statistika" in text.lower():
                            send_stats(chat_id)
                        elif text.startswith("/help") or "yordam" in text.lower() or "qoida" in text.lower():
                            send_help(chat_id)
                        else:
                            # Har qanday boshqa xabar kelganda
                            inline_kb, _ = get_keyboards()
                            api_call("sendMessage", {
                                "chat_id": chat_id,
                                "text": (
                                    f"Assalomu alaykum, <b>{first_name}</b>!\n\n"
                                    "Maktab takliflari bilan tanishish yoki yangi taklif qoldirish uchun "
                                    "quyidagi tugmani bosib portalni oching 👇"
                                ),
                                "parse_mode": "HTML",
                                "reply_markup": inline_kb
                            })

                    # 2. Inline tugmalar (Callbacks)
                    cb = item.get("callback_query")
                    if cb:
                        cb_id = cb["id"]
                        cb_data = cb.get("data")
                        cb_chat = cb["message"]["chat"]["id"]
                        api_call("answerCallbackQuery", {"callback_query_id": cb_id})

                        if cb_data == "btn_stats":
                            send_stats(cb_chat)
                        elif cb_data == "btn_rules":
                            send_help(cb_chat)
                        elif cb_data == "btn_about":
                            api_call("sendMessage", {
                                "chat_id": cb_chat,
                                "text": (
                                    "🏛 <b>Muhammad al-Xorazmiy nomidagi AKSS Student Council</b>\n\n"
                                    "O'quvchilar Kengashining maqsadi — har bir o'quvchining fikri inobatga olinadigan, "
                                    "zamonaviy va qulay ta'lim muhitini birgalikda yaratishdir."
                                ),
                                "parse_mode": "HTML"
                            })

            time.sleep(0.3)
        except KeyboardInterrupt:
            print("\n🛑 Bot to'xtatildi.")
            break
        except Exception as e:
            print(f"[Loop xatosi]: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
