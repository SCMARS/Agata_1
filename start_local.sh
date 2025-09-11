#!/bin/bash

# Agatha AI Companion - Локальный запуск (без Docker)
# Этот скрипт запускает только API и бота локально

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка Python и виртуального окружения
check_python() {
    if [ ! -d "venv" ]; then
        print_error "Виртуальное окружение не найдено. Создайте его командой:"
        echo "python3 -m venv venv"
        echo "source venv/bin/activate"
        echo "pip install -r requirements.txt"
        exit 1
    fi
    
    if [ ! -f "venv/bin/activate" ]; then
        print_error "Файл активации виртуального окружения не найден"
        exit 1
    fi
}

# Проверка переменных окружения
check_env() {
    print_status "Проверяем переменные окружения..."
    
    if [ -f "config.env" ]; then
        export $(grep -v '^#' config.env | xargs)
        print_success "Переменные загружены из config.env"
    else
        print_error "config.env не найден. Создайте файл с API ключами."
        exit 1
    fi
    
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        print_error "OPENAI_API_KEY не настроен в config.env"
        exit 1
    fi
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" = "your_telegram_bot_token_here" ]; then
        print_error "TELEGRAM_BOT_TOKEN не настроен в config.env"
        exit 1
    fi
}

# Остановка существующих процессов
stop_existing() {
    print_status "Останавливаем существующие процессы..."
    
    # Остановка API сервера
    if [ -f "api.pid" ]; then
        API_PID=$(cat api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            kill $API_PID
            print_success "API сервер остановлен"
        fi
        rm -f api.pid
    fi
    
    # Остановка бота
    if [ -f "bot.pid" ]; then
        BOT_PID=$(cat bot.pid)
        if kill -0 $BOT_PID 2>/dev/null; then
            kill $BOT_PID
            print_success "Telegram бот остановлен"
        fi
        rm -f bot.pid
    fi
    
    # Принудительная остановка процессов на портах
    if lsof -ti:8000 &>/dev/null; then
        print_status "Освобождаем порт 8000..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    fi
}

# Запуск API сервера
start_api() {
    print_status "Запускаем API сервер..."
    
    source venv/bin/activate
    nohup python run_server.py > api.log 2>&1 &
    API_PID=$!
    echo $API_PID > api.pid
    
    print_status "Ожидаем запуска API сервера..."
    timeout=30
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:8000/healthz &>/dev/null; then
            print_success "API сервер запущен (PID: $API_PID)"
            return 0
        fi
        sleep 2
        timeout=$((timeout-2))
    done
    
    if [ $timeout -le 0 ]; then
        print_error "API сервер не запустился за 30 секунд"
        print_status "Проверьте логи: tail -f api.log"
        exit 1
    fi
}

# Запуск Telegram бота
start_bot() {
    print_status "Запускаем Telegram бота..."
    
    source venv/bin/activate
    nohup python simple_telegram_bot.py > bot.log 2>&1 &
    BOT_PID=$!
    echo $BOT_PID > bot.pid
    
    print_success "Telegram бот запущен (PID: $BOT_PID)"
}

# Проверка работы системы
check_system() {
    print_status "Проверяем работу системы..."
    
    # Проверка API
    if curl -s http://localhost:8000/healthz &>/dev/null; then
        print_success "✅ API сервер работает"
    else
        print_error "❌ API сервер не отвечает"
        return 1
    fi
    
    # Тестовый запрос
    print_status "Отправляем тестовый запрос..."
    response=$(curl -s -X POST http://localhost:8000/api/chat \
        -H "Content-Type: application/json" \
        -d '{"user_id":"test","messages":[{"role":"user","content":"Привет"}]}')
    
    if echo "$response" | grep -q "parts"; then
        print_success "✅ API отвечает на запросы"
    else
        print_warning "⚠️ API отвечает, но возможно есть проблемы"
    fi
}

# Показать статус
show_status() {
    echo ""
    echo "=========================================="
    echo "🚀 Agatha AI Companion - Локальная система запущена!"
    echo "=========================================="
    echo ""
    echo "📊 Статус сервисов:"
    echo "  • API сервер: http://localhost:8000"
    echo "  • Telegram бот: активен"
    echo ""
    echo "📝 Логи:"
    echo "  • API: tail -f api.log"
    echo "  • Bot: tail -f bot.log"
    echo ""
    echo "🛑 Остановка:"
    echo "  • ./stop_all.sh - остановить все"
    echo "  • kill \$(cat api.pid) - остановить API"
    echo "  • kill \$(cat bot.pid) - остановить бота"
    echo ""
    echo "🧪 Тестирование:"
    echo "  curl http://localhost:8000/healthz"
    echo "  curl http://localhost:8000/readyz"
    echo ""
    echo "💬 Тест чата:"
    echo "  curl -X POST http://localhost:8000/api/chat \\"
    echo "    -H \"Content-Type: application/json\" \\"
    echo "    -d '{\"user_id\":\"test\",\"messages\":[{\"role\":\"user\",\"content\":\"Привет\"}]}'"
    echo ""
}

# Основная функция
main() {
    echo "🤖 Agatha AI Companion - Локальный запуск"
    echo "========================================="
    
    check_python
    check_env
    stop_existing
    start_api
    start_bot
    check_system
    show_status
}

# Обработка сигналов
trap 'echo ""; print_warning "Получен сигнал остановки..."; exit 0' INT TERM

# Запуск
main "$@"
