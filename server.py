import json
import sqlite3
import hashlib
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
import urllib.request
import threading
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voice.db')
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS proposals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            category_name TEXT NOT NULL,
            author_alias TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL,
            vote_count INTEGER DEFAULT 1
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            proposal_id TEXT NOT NULL,
            user_hash TEXT NOT NULL,
            created_at REAL NOT NULL,
            PRIMARY KEY (proposal_id, user_hash)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            organizer TEXT NOT NULL,
            category TEXT NOT NULL,
            options_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS poll_votes (
            poll_id TEXT NOT NULL,
            user_hash TEXT NOT NULL,
            option_index INTEGER NOT NULL,
            created_at REAL NOT NULL,
            PRIMARY KEY (poll_id, user_hash)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS app_metadata (
            key TEXT PRIMARY KEY,
            val TEXT
        )
    ''')
    
    # Mark database initialized. Never auto-reseed if tables are emptied by user!
    c.execute('SELECT val FROM app_metadata WHERE key = ?', ('seeded',))
    row = c.fetchone()
    if not row:
        c.execute('INSERT OR REPLACE INTO app_metadata (key, val) VALUES (?, ?)', ('seeded', '1'))
    conn.commit()
    conn.close()

# --- ADMIN SECRET SECURITY KEY ---
ADMIN_SECRET_KEY = os.getenv("AKSS_ADMIN_SECRET", "XORAZMIY_780")

# --- PROFANITY & SPAM FILTER ---
FORBIDDEN_WORDS = ['ahmoq', 'itvachcha', 'tupoy', 'dalbayob', 'haromi', 'mol']

def is_clean_text(text):
    lowered = text.lower()
    for word in FORBIDDEN_WORDS:
        if word in lowered:
            return False
    return True

# --- API REQUEST HANDLER ---
class VoiceAPIHandler(SimpleHTTPRequestHandler):
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-User-Id')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-User-Id')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/proposals':
            # Query proposals
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM proposals ORDER BY vote_count DESC, created_at DESC')
            rows = c.fetchall()
            proposals = []
            for r in rows:
                proposals.append({
                    'id': r['id'],
                    'title': r['title'],
                    'desc': r['description'],
                    'category': r['category'],
                    'categoryName': r['category_name'],
                    'author': r['author_alias'],
                    'votes': r['vote_count'],
                    'status': r['status'],
                    'date': self.format_relative_time(r['created_at'])
                })
            conn.close()
            self.send_json({'success': True, 'proposals': proposals})
            return

        elif path == '/api/stats':
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM proposals')
            total = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM proposals WHERE vote_count >= 50 AND status != "resolved"')
            active_council = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM proposals WHERE status = "resolved"')
            resolved = c.fetchone()[0]
            c.execute('SELECT SUM(vote_count) FROM proposals')
            votes_sum = c.fetchone()[0] or 0
            conn.close()

            self.send_json({
                'total': total,
                'active_council': active_council,
                'resolved': resolved,
                'total_votes': votes_sum
            })
            return

        elif path == '/api/my-votes':
            # Check which items the requesting user has voted on
            user_id = self.headers.get('X-User-Id', 'anonymous')
            user_hash = hashlib.sha256(user_id.encode('utf-8')).hexdigest()
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT proposal_id FROM votes WHERE user_hash = ?', (user_hash,))
            voted_ids = [r[0] for r in c.fetchall()]
            conn.close()
            self.send_json({'voted_ids': voted_ids})
            return

        elif path == '/api/polls':
            user_id = self.headers.get('X-User-Id', 'anonymous')
            user_hash = hashlib.sha256(user_id.encode('utf-8')).hexdigest()

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM polls ORDER BY created_at DESC')
            rows = c.fetchall()
            polls = []
            for r in rows:
                opts = json.loads(r['options_json'])
                c.execute('SELECT option_index FROM poll_votes WHERE poll_id = ? AND user_hash = ?', (r['id'], user_hash))
                voted_row = c.fetchone()
                my_choice = voted_row[0] if voted_row else None
                total_votes = sum(o.get('votes', 0) for o in opts)

                polls.append({
                    'id': r['id'],
                    'title': r['title'],
                    'organizer': r['organizer'],
                    'category': r['category'],
                    'options': opts,
                    'totalVotes': total_votes,
                    'myChoice': my_choice,
                    'status': r['status'],
                    'date': self.format_relative_time(r['created_at'])
                })
            conn.close()
            self.send_json({'success': True, 'polls': polls})
            return

        # Fallback to serve static files (voice.html, index.html, etc.)
        if path == '/' or path == '':
            self.path = '/voice.html'
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_length).decode('utf-8')
        try:
            body = json.loads(post_body) if post_body else {}
        except Exception:
            self.send_json({'error': 'Noto\'g\'ri JSON ma\'lumot'}, 400)
            return

        if path == '/api/proposals':
            # Create new proposal
            title = body.get('title', '').strip()
            desc = body.get('desc', '').strip()
            category = body.get('category', 'sharoit')
            category_name = body.get('categoryName', 'Sinfxonalar & Sharoit')

            if len(title) < 5 or len(desc) < 10:
                self.send_json({'error': 'Sarlavha kamida 5 ta, tavsif kamida 10 ta belgidan iborat bo\'lishi shart!'}, 400)
                return

            if not is_clean_text(title) or not is_clean_text(desc):
                self.send_json({'error': 'Iltimos, nojo\'ya yoki haqoratli so\'zlardan foydalanmang!'}, 400)
                return

            new_id = f"prop-{int(time.time() * 1000)}"
            user_id = self.headers.get('X-User-Id', f"anon-{time.time()}")
            user_hash = hashlib.sha256(user_id.encode('utf-8')).hexdigest()

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''
                INSERT INTO proposals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_id, title, desc, category, category_name, "Anonim O'quvchi", time.time(), 'voting', 1))
            c.execute('''
                INSERT INTO votes VALUES (?, ?, ?)
            ''', (new_id, user_hash, time.time()))
            conn.commit()
            conn.close()

            self.send_json({'success': True, 'id': new_id})
            return

        elif path.startswith('/api/vote/'):
            # Toggle vote
            prop_id = path.replace('/api/vote/', '')
            user_id = self.headers.get('X-User-Id')
            if not user_id:
                self.send_json({'error': 'Foydalanuvchi identifikatori topilmadi'}, 400)
                return

            user_hash = hashlib.sha256(user_id.encode('utf-8')).hexdigest()
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()

            # Check if voted
            c.execute('SELECT 1 FROM votes WHERE proposal_id = ? AND user_hash = ?', (prop_id, user_hash))
            existing = c.fetchone()

            if existing:
                # Remove vote
                c.execute('DELETE FROM votes WHERE proposal_id = ? AND user_hash = ?', (prop_id, user_hash))
                c.execute('UPDATE proposals SET vote_count = MAX(0, vote_count - 1) WHERE id = ?', (prop_id,))
                voted = False
            else:
                # Add vote
                c.execute('INSERT INTO votes VALUES (?, ?, ?)', (prop_id, user_hash, time.time()))
                c.execute('UPDATE proposals SET vote_count = vote_count + 1 WHERE id = ?', (prop_id,))
                voted = True

            # Check 50 threshold
            c.execute('SELECT vote_count, status FROM proposals WHERE id = ?', (prop_id,))
            row = c.fetchone()
            if row and row[0] >= 50 and row[1] == 'voting':
                c.execute('UPDATE proposals SET status = "council" WHERE id = ?', (prop_id,))

            conn.commit()
            new_count = row[0] if row else 0
            conn.close()

            self.send_json({'success': True, 'voted': voted, 'votes': new_count})
            return

        elif path.startswith('/api/poll-vote/'):
            poll_id = path.replace('/api/poll-vote/', '')
            option_index = body.get('optionIndex')
            user_id = self.headers.get('X-User-Id')

            if user_id is None or option_index is None:
                self.send_json({'error': 'Noto\'g\'ri so\'rov ma\'lumotlari'}, 400)
                return

            user_hash = hashlib.sha256(user_id.encode('utf-8')).hexdigest()
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()

            # Check if already voted
            c.execute('SELECT option_index FROM poll_votes WHERE poll_id = ? AND user_hash = ?', (poll_id, user_hash))
            existing = c.fetchone()

            # Fetch poll
            c.execute('SELECT options_json FROM polls WHERE id = ?', (poll_id,))
            poll_row = c.fetchone()
            if not poll_row:
                conn.close()
                self.send_json({'error': 'So\'rovnoma topilmadi'}, 404)
                return

            opts = json.loads(poll_row[0])

            if existing:
                prev_idx = existing[0]
                if prev_idx != option_index:
                    opts[prev_idx]['votes'] = max(0, opts[prev_idx]['votes'] - 1)
                    opts[option_index]['votes'] = opts[option_index].get('votes', 0) + 1
                    c.execute('UPDATE poll_votes SET option_index = ?, created_at = ? WHERE poll_id = ? AND user_hash = ?',
                              (option_index, time.time(), poll_id, user_hash))
            else:
                opts[option_index]['votes'] = opts[option_index].get('votes', 0) + 1
                c.execute('INSERT INTO poll_votes VALUES (?, ?, ?, ?)', (poll_id, user_hash, option_index, time.time()))

            c.execute('UPDATE polls SET options_json = ? WHERE id = ?', (json.dumps(opts, ensure_ascii=False), poll_id))
            conn.commit()
            total_votes = sum(o.get('votes', 0) for o in opts)
            conn.close()

            self.send_json({'success': True, 'options': opts, 'totalVotes': total_votes, 'myChoice': option_index})
            return

        elif path == '/api/polls':
            # Create new official poll (Admin / Student Council)
            title = body.get('title', '').strip()
            organizer = body.get('organizer', 'Student Council & Ma\'muriyat').strip()
            category = body.get('category', 'Maktab Tartibi').strip()
            options = body.get('options', [])
            admin_pin = body.get('adminPin', '').strip()

            # Strict secret key check
            if admin_pin != ADMIN_SECRET_KEY:
                self.send_json({'error': 'Xato Maxfiy Kod! So\'rovnoma yaratish faqat Maktab Ma\'muriyati va Student Council raisiga ruxsat etilgan.'}, 403)
                return

            if len(title) < 6:
                self.send_json({'error': 'So\'rovnoma savoli kamida 6 ta belgidan iborat bo\'lishi kerak!'}, 400)
                return

            clean_opts = []
            for opt in options:
                txt = opt.get('text', '').strip() if isinstance(opt, dict) else str(opt).strip()
                if txt:
                    clean_opts.append({'text': txt, 'votes': 0})

            if len(clean_opts) < 2:
                self.send_json({'error': 'So\'rovnomada kamida 2 ta variant bo\'lishi shart!'}, 400)
                return

            new_poll_id = f"poll-{int(time.time() * 1000)}"
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''
                INSERT INTO polls VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (new_poll_id, title, organizer, category, json.dumps(clean_opts, ensure_ascii=False), time.time(), 'active'))
            conn.commit()
            conn.close()

            self.send_json({
                'success': True,
                'poll': {
                    'id': new_poll_id,
                    'title': title,
                    'organizer': organizer,
                    'category': category,
                    'options': clean_opts,
                    'totalVotes': 0,
                    'myChoice': None,
                    'status': 'active',
                    'date': 'Hozirgina'
                }
            })
            return

        elif path.startswith('/api/poll-delete/'):
            poll_id = path.replace('/api/poll-delete/', '')
            admin_pin = body.get('adminPin', '').strip()

            if admin_pin != ADMIN_SECRET_KEY:
                self.send_json({'error': 'Xato Maxfiy Kod! So\'rovnomani o\'chirish faqat Admin uchun ruxsat etilgan.'}, 403)
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM polls WHERE id = ?', (poll_id,))
            c.execute('DELETE FROM poll_votes WHERE poll_id = ?', (poll_id,))
            conn.commit()
            conn.close()

            self.send_json({'success': True, 'deletedId': poll_id})
            return

        elif path.startswith('/api/proposal-status/'):
            prop_id = path.replace('/api/proposal-status/', '')
            new_status = body.get('status', '').strip()
            admin_pin = body.get('adminPin', '').strip()

            if admin_pin != ADMIN_SECRET_KEY:
                self.send_json({'error': 'Xato Maxfiy Kod! Holatni o\'zgartirish faqat Admin uchun ruxsat etilgan.'}, 403)
                return

            if new_status not in ['voting', 'council', 'resolved', 'rejected']:
                self.send_json({'error': 'Noto\'g\'ri holat tanlandi'}, 400)
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('UPDATE proposals SET status = ? WHERE id = ?', (new_status, prop_id))
            conn.commit()
            conn.close()

            self.send_json({'success': True, 'id': prop_id, 'status': new_status})
            return

        elif path.startswith('/api/proposal-delete/'):
            prop_id = path.replace('/api/proposal-delete/', '')
            admin_pin = body.get('adminPin', '').strip()

            if admin_pin != ADMIN_SECRET_KEY:
                self.send_json({'error': 'Xato Maxfiy Kod!'}, 403)
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM proposals WHERE id = ?', (prop_id,))
            c.execute('DELETE FROM votes WHERE proposal_id = ?', (prop_id,))
            conn.commit()
            conn.close()

            self.send_json({'success': True, 'deletedId': prop_id})
            return

        elif path == '/api/admin/reset-database':
            admin_pin = body.get('adminPin', '').strip()
            if admin_pin != ADMIN_SECRET_KEY:
                self.send_json({'error': 'Xato Maxfiy Kod!'}, 403)
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM proposals')
            c.execute('DELETE FROM votes')
            c.execute('DELETE FROM polls')
            c.execute('DELETE FROM poll_votes')
            c.execute('INSERT OR REPLACE INTO app_metadata (key, val) VALUES (?, ?)', ('seeded', '1'))
            conn.commit()
            conn.close()

            self.send_json({'success': True, 'message': 'Barcha ma\'lumotlar tozalandi (0 ta)'})
            return

        self.send_json({'error': 'API topilmadi'}, 404)

    def format_relative_time(self, ts):
        diff = time.time() - ts
        if diff < 3600:
            return f"{max(1, int(diff // 60))} daqiqa oldin"
        elif diff < 86400:
            return f"{int(diff // 3600)} soat oldin"
        else:
            return f"{int(diff // 86400)} kun oldin"

# --- 24/7 TELEGRAM BOT DAEMON (RUNS INSIDE RENDER CLOUD) ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9273166206:AAGjhSkH1qoWIrBBIA1xhtDLFJfMyrACAFc").strip()
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://akss-voice.onrender.com").strip()

def tg_api_call(method, payload=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception as e:
        if "timed out" not in str(e).lower():
            print(f"[Telegram API Error] {method}: {e}")
        return None

def get_live_stats_text():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM proposals")
        total_props = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM proposals WHERE status = 'resolved'")
        resolved = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM proposals WHERE status = 'council' OR vote_count >= 50")
        council = c.fetchone()[0]
        c.execute("SELECT SUM(vote_count) FROM proposals")
        votes = c.fetchone()[0] or 0
        c.execute("SELECT title, vote_count FROM proposals ORDER BY vote_count DESC LIMIT 1")
        top = c.fetchone()
        conn.close()

        top_title = top[0] if top else "Hozircha yo'q"
        top_votes = top[1] if top else 0

        return (
            "📊 <b>AKSS Voice — Jonli Maktab Statistikasi:</b>\n\n"
            f"💡 Jami anonim takliflar: <b>{total_props} ta</b>\n"
            f"🔥 Direktor stolida (50+ ovoz): <b>{council} ta</b>\n"
            f"🟢 Hal etilgan / Bajarilgan: <b>{resolved} ta</b>\n"
            f"🗳 O'quvchilar bergan ovozlari: <b>{votes} ta</b>\n\n"
            f"🏆 <b>Eng faol taklif:</b>\n"
            f"«<i>{top_title}</i>» (<b>{top_votes} ta ovoz</b>)\n\n"
            "O'z taklifingizni kiritish uchun quyidagi tugmani bosing!"
        )
    except Exception as e:
        return f"Statistika yuklanmadi: {e}"

def tg_send_welcome(chat_id, first_name):
    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>! 👋\n\n"
        "🏛 <b>AKSS Voice — Muhammad al-Xorazmiy nomidagi ixtisoslashtirilgan maktabi</b>\n"
        "<b>Student Council (O'quvchilar Kengashi)</b> rasmiy anonim takliflar va muammolar platformasiga xush kelibsiz!\n\n"
        "📌 <b>Platformada siz:</b>\n"
        "• Maktabdagi har qanday kamchilik (Wi-Fi, oshxona, sharoit) bo'yicha <b>100% anonim</b> taklif qoldirishingiz;\n"
        "• Boshqa o'quvchilar takliflariga ovoz berishingiz;\n"
        "• Kengash e'lon qilgan 6 ta vazirlik so'rovnomalarida qatnashishingiz mumkin.\n\n"
        "⚡ <b>50 ta ovoz yig'ilgan har bir masala</b> dushanba kuni Student Council orqali "
        "<b>to'g'ridan-to'g'ri maktab direktoriga</b> taqdim etiladi.\n\n"
        "Quyidagi tugmani bosing va platformani oching 👇"
    )

    inline_kb = {
        "inline_keyboard": [
            [{"text": "🚀 AKSS Voice Portalini Ochish", "web_app": {"url": WEB_APP_URL}}],
            [{"text": "📊 Jonli Statistika", "callback_data": "btn_stats"}, {"text": "ℹ️ Qoidalar", "callback_data": "btn_rules"}]
        ]
    }

    # Bitta tezkor so'rov bilan darhol javob qaytaramiz (kechikishsiz)
    tg_api_call("sendMessage", {
        "chat_id": chat_id,
        "text": welcome_text,
        "parse_mode": "HTML",
        "reply_markup": inline_kb
    })

def run_telegram_bot_daemon():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️ [Telegram Bot] Token yo'q, bot ishga tushmadi.")
        return

    print(f"🤖 [Telegram Bot] Bulutda (Render) 24/7 orqa fonda ishga tushmoqda...")
    try:
        tg_api_call("setChatMenuButton", {
            "menu_button": {
                "type": "web_app",
                "text": "📢 AKSS Voice",
                "web_app": {"url": WEB_APP_URL}
            }
        })
    except Exception as e:
        print(f"[Telegram MenuButton Error] {e}")

    offset = 0
    while True:
        try:
            # 1 soniyalik ultra-tezkor tekshiruv (kechikishlarsiz)
            updates = tg_api_call("getUpdates", {"offset": offset, "timeout": 1})
            if updates and updates.get("ok"):
                for item in updates.get("result", []):
                    offset = item["update_id"] + 1

                    msg = item.get("message")
                    if msg:
                        text = msg.get("text", "")
                        chat_id = msg["chat"]["id"]
                        first_name = msg["from"].get("first_name", "O'quvchi")

                        print(f"📩 [Telegram Xabar] {first_name}: {text}")

                        if text.startswith("/start"):
                            tg_send_welcome(chat_id, first_name)
                        elif text.startswith("/portal") or "portal" in text.lower():
                            tg_api_call("sendMessage", {
                                "chat_id": chat_id,
                                "text": "🚀 <b>AKSS Voice Portalini ochish uchun quyidagi tugmani bosing:</b>",
                                "parse_mode": "HTML",
                                "reply_markup": {
                                    "inline_keyboard": [[{"text": "🚀 Portalni Ochish", "web_app": {"url": WEB_APP_URL}}]]
                                }
                            })
                        elif text.startswith("/stats") or "statistika" in text.lower():
                            tg_api_call("sendMessage", {
                                "chat_id": chat_id,
                                "text": get_live_stats_text(),
                                "parse_mode": "HTML",
                                "reply_markup": {
                                    "inline_keyboard": [[{"text": "🚀 Portalni Ochish", "web_app": {"url": WEB_APP_URL}}]]
                                }
                            })
                        elif text.startswith("/help") or "yordam" in text.lower() or "qoida" in text.lower():
                            tg_api_call("sendMessage", {
                                "chat_id": chat_id,
                                "text": (
                                    "ℹ️ <b>AKSS Voice Platformasi Qoidalari:</b>\n\n"
                                    "1. <b>100% Anonimlik:</b> Ism-familiyangiz hech kimga ko'rinmaydi.\n"
                                    "2. <b>50 ta Ovoz:</b> 50 ta haqiqiy ovoz to'plagan har bir masala dushanba kuni direktor stoliga kiritiladi.\n"
                                    "3. <b>6 ta Vazirlik:</b> Student Council so'rovnomalari 6 ta vazirlik yo'nalishida o'tkaziladi."
                                ),
                                "parse_mode": "HTML",
                                "reply_markup": {
                                    "inline_keyboard": [[{"text": "🚀 Portalni Ochish", "web_app": {"url": WEB_APP_URL}}]]
                                }
                            })
                        else:
                            tg_api_call("sendMessage", {
                                "chat_id": chat_id,
                                "text": f"Assalomu alaykum, <b>{first_name}</b>!\nPortalni ochish uchun quyidagi tugmani bosing 👇",
                                "parse_mode": "HTML",
                                "reply_markup": {
                                    "inline_keyboard": [[{"text": "🚀 AKSS Voice Portalini Ochish", "web_app": {"url": WEB_APP_URL}}]]
                                }
                            })

                    cb = item.get("callback_query")
                    if cb:
                        cb_id = cb["id"]
                        cb_data = cb.get("data")
                        cb_chat = cb["message"]["chat"]["id"]
                        tg_api_call("answerCallbackQuery", {"callback_query_id": cb_id})
                        if cb_data == "btn_stats":
                            tg_api_call("sendMessage", {
                                "chat_id": cb_chat,
                                "text": get_live_stats_text(),
                                "parse_mode": "HTML",
                                "reply_markup": {
                                    "inline_keyboard": [[{"text": "🚀 Portalni Ochish", "web_app": {"url": WEB_APP_URL}}]]
                                }
                            })
                        elif cb_data == "btn_rules":
                            tg_api_call("sendMessage", {
                                "chat_id": cb_chat,
                                "text": "ℹ️ <b>50 ta ovoz yig'ilgan har bir masala dushanba kuni direktor stoliga rasmiy taqdim etiladi.</b>",
                                "parse_mode": "HTML"
                            })

            time.sleep(0.1)
        except Exception as e:
            time.sleep(2)

def run_server(port=None):
    if port is None:
        port = int(os.environ.get('PORT', 3000))
    init_db()

    # Start 24/7 Telegram Bot Daemon in the cloud!
    bot_thread = threading.Thread(target=run_telegram_bot_daemon, daemon=True)
    bot_thread.start()
    print("🤖 Telegram Boti bulutda (Render) 24/7 orqa fonda ishga tushdi!")

    server_address = ('', port)
    httpd = HTTPServer(server_address, VoiceAPIHandler)
    print("=" * 60)
    print(f"🚀 AKSS Voice Haqiqiy Backend Serveri ishga tushdi! (Port: {port})")
    print(f"📍 Manzil: http://localhost:{port}/voice.html")
    print(f"💾 SQLite Ma'lumotlar bazasi: {DB_FILE}")
    print("=" * 60)
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
