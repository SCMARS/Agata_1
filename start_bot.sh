#!/bin/bash
# Универсальный запуск Telegram бота Agata

echo "🤖 Запуск Agata Telegram бота..."
cd "$(dirname "$0")"
source venv/bin/activate
python3 run_telegram_bot.py
