#!/bin/bash

# 🚀 БЫСТРЫЙ ЗАПУСК СИСТЕМЫ AGATHA
# =================================

echo "🚀 ЗАПУСК СИСТЕМЫ AGATHA"
echo "========================"

# Переходим в директорию проекта
cd "$(dirname "$0")"

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден! Установите Python 3.8+"
    exit 1
fi

# Проверяем виртуальное окружение
if [ ! -d "venv" ]; then
    echo "⚠️ Виртуальное окружение не найдено"
    echo "💡 Создайте его: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Проверяем config.env
if [ ! -f "config.env" ]; then
    echo "❌ Файл config.env не найден!"
    echo "💡 Создайте config.env с необходимыми переменными"
    exit 1
fi

# Активируем виртуальное окружение и загружаем переменные
echo "🔧 Настраиваем окружение..."
source venv/bin/activate
export $(cat config.env | grep -v '^#' | grep -v '^$' | xargs)

# Проверяем обязательные переменные
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY не установлен в config.env"
    exit 1
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN не установлен в config.env"
    exit 1
fi

echo "✅ Окружение настроено"

# Запускаем полную систему
echo "🚀 Запускаем полную систему..."
python3 start_agatha.py
