import json
import sqlite3
import hashlib
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
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
    
    # Check if empty, populate with realistic AKSS Andijan initial seeds
    c.execute('SELECT COUNT(*) FROM proposals')
    if c.fetchone()[0] == 0:
        initial_seeds = [
            (
                'prop-1',
                "3-qavat IT Lab 2 dagi Wi-Fi router tezligini oshirish va qayta sozlash",
                "Dasturlash darslarida (C++ va Python paketlarini yuklashda) internet tezligi tushib ketmoqda. Har bir darsda 30 ta o'quvchi bir vaqtda ulanganda router qizib o'chib qolmoqda. Bitta qo'shimcha Gigabit switch yoki 5GHz access point o'rnatish taklif etiladi.",
                'it', 'Wi-Fi & IT Uskunalar', 'Anonim O\'quvchi (10-sinf)',
                time.time() - 86400 * 3, 'council', 78
            ),
            (
                'prop-2',
                "Oshxonadagi navbatni kamaytirish uchun tanaffusdan 15 daqiqa oldin Telegram orqali buyurtma berish",
                "Katta tanaffusda 15 daqiqa davomida kassada uzun navbat hosil bo'lmoqda. Ko'pchilik ovqat yeb ulgurmay qolyapti. Oshxona uchun oddiy menyu-bot yaratib, o'quvchilar oldindan band qilib qo'yadigan tizim kiritilsa yaxshi bo'lardi.",
                'oshxona', 'Oshxona & Taomlar', 'Anonim O\'quvchi (9-sinf)',
                time.time() - 86400 * 5, 'council', 64
            ),
            (
                'prop-3',
                "Kutubxonaga xalqaro SAT Math va yangi C++ / Algoritmlar kitoblarini qo'shish",
                "Kutubxonamizda badiiy kitoblar ko'p, lekin New Uzbekistan va xorijiy universitetlarga tayyorlanish uchun yangi 2024–2025 Digital SAT qo'llanmalari va IOI algoritmlari bo'yicha kitoblar yetishmayapti.",
                'kutubxona', 'Kutubxona & SAT/IELTS', 'Anonim O\'quvchi (11-sinf)',
                time.time() - 86400, 'voting', 48
            ),
            (
                'prop-4',
                "Sport zalidagi stol tennisi raketkalari va to'rlarini yangilash",
                "Darsdan keyingi tanaffusda o'quvchilar stol tennisi o'ynashni xohlashadi, ammo mavjud 4 ta raketkaning rezinkalari ko'chib ketgan. Student Council hisobidan yangi 4 juft sifatli raketka olib berilishi so'raladi.",
                'sport', 'Sport & Salomatlik', 'Anonim O\'quvchi (8-sinf)',
                time.time() - 86400 * 14, 'resolved', 82
            ),
            (
                'prop-5',
                "2-qavatdagi sinfxonalar proyektorlariga HDMI kabellari va pultlarini sozlash",
                "Prezentatsiya darslarida o'qituvchilar doim HDMI kabel qidirib vaqt yo'qotmoqda. Har bir sinf xonasiga bittadan qattiq mahkamlangan kabel va pult qo'yilsa darslar tezroq boshlanardi.",
                'sharoit', 'Sinfxonalar & Sharoit', 'Anonim O\'quvchi (7-sinf)',
                time.time() - 12000, 'voting', 38
            )
        ]
        c.executemany('''
            INSERT INTO proposals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', initial_seeds)

    # Populate initial realistic polls if empty
    c.execute('SELECT COUNT(*) FROM polls')
    if c.fetchone()[0] == 0:
        initial_polls = [
            (
                'poll-1',
                "Juma kunlari maktabda erkin kiyim (IT Casual / Qulay kiyim) kuni joriy etilishiga rozimisiz?",
                "Student Council & Ma'muriyat",
                "Maktab Tartibi",
                json.dumps([
                    {"text": "Ha, to'liq qo'llab-quvvatlayman (Hudi/Jinsi)", "votes": 142},
                    {"text": "Faqat to'q rangli erkin kiyim ruxsat etilsin", "votes": 35},
                    {"text": "Klassik forma qolgani ma'qul", "votes": 14}
                ], ensure_ascii=False),
                time.time() - 86400 * 2,
                "active"
            ),
            (
                'poll-2',
                "Keyingi oylik maktab Hackathon musobaqasi qaysi yo'nalishda bo'lsin?",
                "AKSS IT Qo'mitasi",
                "Texnologiya & IT",
                json.dumps([
                    {"text": "Sun'iy Intellekt va AI Agentlar (LLM)", "votes": 118},
                    {"text": "Telegram Botlar & WebApp (TWA)", "votes": 84},
                    {"text": "Kiberxavfsizlik & CTF (Ethical Hacking)", "votes": 59}
                ], ensure_ascii=False),
                time.time() - 86400 * 4,
                "active"
            ),
            (
                'poll-3',
                "Oshxonadagi tushlik taomlari menyusiga qaysi yangi taom qo'shilsin?",
                "Oshxona Komissiyasi",
                "Oshxona & Taomlar",
                json.dumps([
                    {"text": "Lag'mon & Qovurma", "votes": 96},
                    {"text": "Mini Pitsa & Toster", "votes": 72},
                    {"text": "Tovuqli Salat & Grechka", "votes": 41}
                ], ensure_ascii=False),
                time.time() - 86400 * 6,
                "active"
            )
        ]
        c.executemany('''
            INSERT INTO polls VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', initial_polls)
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

        self.send_json({'error': 'API topilmadi'}, 404)

    def format_relative_time(self, ts):
        diff = time.time() - ts
        if diff < 3600:
            return f"{max(1, int(diff // 60))} daqiqa oldin"
        elif diff < 86400:
            return f"{int(diff // 3600)} soat oldin"
        else:
            return f"{int(diff // 86400)} kun oldin"

def run_server(port=3000):
    init_db()
    server_address = ('', port)
    httpd = HTTPServer(server_address, VoiceAPIHandler)
    print("=" * 60)
    print(f"🚀 AKSS Voice Haqiqiy Backend Serveri ishga tushdi!")
    print(f"📍 Manzil: http://localhost:{port}/voice.html")
    print(f"💾 SQLite Ma'lumotlar bazasi: {DB_FILE}")
    print("=" * 60)
    httpd.serve_forever()

if __name__ == '__main__':
    run_server(3000)
