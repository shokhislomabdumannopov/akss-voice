# 🚀 "AKSS Voice" — Real Ishga Tushirish va Ommalashtirish Qo'llanmasi

> Ushbu qo'llanma orqali siz **AKSS Voice** platformasini maktab o'quvchilari va o'qituvchilari o'z telefonlarida (Telegram orqali) real ishlatishi uchun to'liq internetga chiqarasiz.

---

## 🏗️ Tizim Strukturasi

```
           [O'quvchi Telefoni / Telegram]
                         │
                         ▼
        ┌──────────────────────────────────┐
        │       Telegram Web App (TWA)     │
        │   (O'quvchi bitta tugma bilan    │
        │    Telegram ichida ochadi)       │
        └────────────────┬─────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────┐
        │       Backend Server (Python)    │
        │        (server.py / API)         │
        └────────────────┬─────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────┐
        │      SQLite Baza (voice.db)      │
        │  (Ovozlar, Takliflar, Nazorat)   │
        └──────────────────────────────────┘
```

---

## 1-QADAM: Kompyuteringizda Haqiqiy Serverni Yoqish

Terminalda quyidagi buyruqni bering:

```bash
cd /Users/shoxislom/Desktop/new
python3 server.py
```

Server ishga tushadi:
* 🌐 Sayt va API: `http://localhost:3000/voice.html`
* 💾 Baza fayli: `voice.db` (barcha haqiqiy ovozlar va takliflar shu yerda saqlanadi).

---

## 2-QADAM: Telegram Bot Ochish (3 daqiqa)

Barcha o'quvchilar buni Telegram orqali ochishi uchun:

1. Telegramda rasmiy **[@BotFather](https://t.me/BotFather)** ga kiring.
2. `/newbot` buyrug'ini yuboring.
3. Botga nom bering: `AKSS Voice | Student Council`
4. Username tanlang: masalan `akss_voice_bot` yoki `xorazmiy_voice_bot`.
5. `@BotFather` sizga **API Token** beradi (masalan: `7492819482:AAHj...`).

### Bot Menyu Tugmasiga WebApp Bog'lash (Juda oson):
`@BotFather` ga quyidagi buyruqlarni yuboring:
* `/setmenubutton` yozing;
* Botingizni tanlang;
* Tugma nomini yozing: `📢 AKSS Voice`
* URL manzilini kiriting (quyidagi 3-qadamda olingan havola).

---

## 3-QADAM: Butun Maktab Ko'rishi Uchun Internetga Chiqarish (3 xil usul)

### 🥇 1-Usul: Cloudflare Tunnel (Eng tez va bepul)
Kompyuteringizdagi serverni darhol xavfsiz `https://...` manzilga aylantiradi:
```bash
brew install cloudflare/cloudflare/cloudflared
cloudflared tunnel --url http://localhost:3000
```
Sizga bepul `https://random-nomi.trycloudflare.com` havolasi beriladi. Uni to'g'ridan-to'g'ri Telegram botga qo'yasiz!

### 🥈 2-Usul: Render.com (24/7 kompyuteringiz o'chiq bo'lsa ham ishlaydi)
1. Ushbu loyihani o'zingizning GitHub akkauntingizga yuklang (`git push`).
2. [Render.com](https://render.com) ga kiring (bepul).
3. **New Web Service** $\rightarrow$ GitHub reponi tanlang.
4. **Build Command:** `pip install -r requirements.txt || true`
5. **Start Command:** `python3 server.py`
6. Render sizga 24/7 ishlaydigan `https://akss-voice.onrender.com` bepul domenini beradi!

### 🥉 3-Usul: Maktabning `alxorazmiyandijon.uz` Serveriga Joylash
Maktab veb-saytini boshqaradigan o'quvchi yoki IT o'qituvchiga ushbu fayllarni bersangiz, ular maktab serveridagi bitta papkaga (masalan `alxorazmiyandijon.uz/voice`) joylab qo'yishi mumkin!

---

## 4-QADAM: O'quvchilar O'rtasida Ommalashtirish

Student Council bu platformani maktabda qanday tarqatadi?

1. **Sinf Telegram Guruhlariga E'lon:**
   > *"Hurmatli AKSS o'quvchilari! Maktabimizdagi har qanday kamchilik, oshxona, Wi-Fi yoki o'quv sharoitlari bo'yicha taklifingizni 100% anonim qoldirishingiz mumkin bo'lgan rasmiy @akss_voice_bot ishga tushdi. 50 ta ovoz to'plagan har bir masala dushanba kuni direktor qabuliga kiritiladi!"*

2. **Sinfxonalarga QR-kod Yopishtirish:**
   * Botning havolasini QR-kod qilib chiqarib, har bir sinf xonasi va oshxona eshigiga yopishtirib chiqish.
   * O'quvchi telefon kamerasini tutadi $\rightarrow$ Telegram ochiladi $\rightarrow$ darhol ovoz beradi!
