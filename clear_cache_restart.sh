#!/bin/bash

# Скрипт для очищення кешу та перезапуску системи

echo "🧹 Очищення кешу та перезапуск системи Agatha..."

# Зупинимо всі процеси
echo "🛑 Зупинка процесів..."
pkill -f run_server.py
pkill -f run_telegram_bot.py
sleep 2

# Очистимо Python кеш
echo "🗑️ Очищення Python кешу..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Очистимо кеш біографії (якщо є)
echo "📚 Очищення кешу біографії..."
rm -f agata_prompt_data/persona/*.cache 2>/dev/null || true

# Перевіримо налаштування
echo "⚙️ Перевірка налаштувань..."
if [ ! -f "config.env" ]; then
    echo "❌ Файл config.env не знайдено!"
    exit 1
fi

# Активуємо віртуальне середовище та запустимо
echo "🚀 Запуск API сервера..."
source venv/bin/activate && python run_server.py &
API_PID=$!

sleep 5

echo "🤖 Запуск Telegram бота..."
source venv/bin/activate && python run_telegram_bot.py &
BOT_PID=$!

echo ""
echo "✅ Система перезапущена!"
echo "📊 API Server PID: $API_PID"
echo "🤖 Telegram Bot PID: $BOT_PID"
echo ""
echo "📋 Тепер логи показуватимуть:"
echo "   🎭 [BEHAVIORAL] - поведінкову адаптацію"
echo "   📊 [STAGE_PROGRESS] - прогрес по стейджах"
echo "   ⏰ [TIME] - орієнтацію в часі"
echo "   ⏰ [DAILY_QUESTIONS] - генерацію питань"
echo ""
echo "🔍 Моніторинг логів:"
echo "   tail -f logs/*.log | grep -E '\[BEHAVIORAL\]|\[STAGE\]|\[TIME\]|\[DAILY\]'"
