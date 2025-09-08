#!/bin/bash
# Универсальный запуск API сервера Agata

echo "🚀 Запуск Agata API сервера..."
cd "$(dirname "$0")"
source venv/bin/activate
python3 run_server.py
