#!/bin/bash

# Agatha AI Companion - Остановка системы
# Этот скрипт останавливает все компоненты системы

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

# Остановка API сервера
stop_api() {
    if [ -f "api.pid" ]; then
        API_PID=$(cat api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            print_status "Останавливаем API сервер (PID: $API_PID)..."
            kill $API_PID
            print_success "API сервер остановлен"
        else
            print_warning "API сервер уже остановлен"
        fi
        rm -f api.pid
    else
        print_warning "PID файл API сервера не найден"
    fi
}

# Остановка Telegram бота
stop_bot() {
    if [ -f "bot.pid" ]; then
        BOT_PID=$(cat bot.pid)
        if kill -0 $BOT_PID 2>/dev/null; then
            print_status "Останавливаем Telegram бота (PID: $BOT_PID)..."
            kill $BOT_PID
            print_success "Telegram бот остановлен"
        else
            print_warning "Telegram бот уже остановлен"
        fi
        rm -f bot.pid
    else
        print_warning "PID файл бота не найден"
    fi
}

# Остановка Docker контейнеров
stop_docker() {
    print_status "Останавливаем Docker контейнеры..."
    docker-compose down --remove-orphans
    print_success "Docker контейнеры остановлены"
}

# Принудительная остановка процессов
force_stop() {
    print_status "Принудительная остановка процессов..."
    
    # Остановка процессов по имени
    pkill -f "run_server.py" 2>/dev/null || true
    pkill -f "run_telegram_bot.py" 2>/dev/null || true
    
    # Остановка процессов на портах
    if lsof -ti:8000 &>/dev/null; then
        print_status "Освобождаем порт 8000..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    fi
    
    print_success "Принудительная остановка завершена"
}

# Очистка временных файлов
cleanup() {
    print_status "Очистка временных файлов..."
    rm -f api.pid bot.pid
    print_success "Временные файлы удалены"
}

# Показать статус
show_status() {
    echo ""
    echo "=========================================="
    echo "🛑 Agatha AI Companion - Система остановлена"
    echo "=========================================="
    echo ""
    echo "📊 Статус сервисов:"
    
    # Проверка API
    if curl -s http://localhost:8000/healthz &>/dev/null; then
        echo "  • API сервер: ❌ Все еще работает"
    else
        echo "  • API сервер: ✅ Остановлен"
    fi
    
    # Проверка Docker
    if docker-compose ps | grep -q "Up"; then
        echo "  • Docker контейнеры: ❌ Все еще работают"
    else
        echo "  • Docker контейнеры: ✅ Остановлены"
    fi
    
    echo ""
    echo "🔄 Перезапуск: ./start_all.sh"
    echo ""
}

# Основная функция
main() {
    echo "🛑 Agatha AI Companion - Остановка системы"
    echo "=========================================="
    
    stop_api
    stop_bot
    stop_docker
    cleanup
    show_status
}

# Обработка аргументов
case "${1:-}" in
    --force)
        print_warning "Принудительная остановка..."
        force_stop
        stop_docker
        cleanup
        show_status
        ;;
    --help|-h)
        echo "Использование: $0 [опции]"
        echo ""
        echo "Опции:"
        echo "  --force    Принудительная остановка всех процессов"
        echo "  --help     Показать эту справку"
        echo ""
        ;;
    *)
        main
        ;;
esac
