#!/usr/bin/env bash
# AKSS Voice Launcher
cd "$(dirname "$0")"
PORT=3000

echo "=========================================================="
echo "  📢 AKSS VOICE & SO'ROVNOMALAR (STUDENT COUNCIL)"
echo "  Muhammad al-Xorazmiy nomidagi ixtisoslashtirilgan maktab"
echo "=========================================================="
echo ""
echo "🚀 Server ishga tushmoqda: http://localhost:$PORT/voice.html"
echo "💾 SQLite ma'lumotlar bazasi: voice.db"
echo "⏹️ To'xtatish uchun: Ctrl + C bosing"
echo ""

python3 server.py
