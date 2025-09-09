#!/bin/bash

# Agatha AI Companion - Полный запуск системы
# Этот скрипт запускает всю систему: базу данных, Redis, API и Telegram бота

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
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

# Проверка наличия Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker не установлен. Установите Docker и попробуйте снова."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
        exit 1
    fi
}

# Проверка переменных окружения
check_env() {
    print_status "Проверяем переменные окружения..."
    
    if [ -z "$OPENAI_API_KEY" ]; then
        print_warning "OPENAI_API_KEY не установлен в переменных окружения"
        print_status "Загружаем из config.env..."
        if [ -f "config.env" ]; then
            export $(grep -v '^#' config.env | xargs)
            print_success "Переменные загружены из config.env"
        else
            print_error "config.env не найден. Создайте файл с API ключами."
            exit 1
        fi
    fi
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        print_warning "TELEGRAM_BOT_TOKEN не установлен в переменных окружения"
        print_status "Загружаем из config.env..."
        if [ -f "config.env" ]; then
            export $(grep -v '^#' config.env | xargs)
            print_success "Переменные загружены из config.env"
        else
            print_error "config.env не найден. Создайте файл с API ключами."
            exit 1
        fi
    fi
    
    print_success "Переменные окружения настроены"
}

# Остановка существующих контейнеров
stop_existing() {
    print_status "Останавливаем существующие контейнеры..."
    docker-compose down --remove-orphans 2>/dev/null || true
    print_success "Существующие контейнеры остановлены"
}

# Запуск базы данных и Redis
start_infrastructure() {
    print_status "Запускаем инфраструктуру (PostgreSQL + Redis)..."
    docker-compose up -d postgres redis
    
    print_status "Ожидаем готовности базы данных..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose exec -T postgres pg_isready -U agatha -d agatha &>/dev/null; then
            print_success "PostgreSQL готов"
            break
        fi
        sleep 2
        timeout=$((timeout-2))
    done
    
    if [ $timeout -le 0 ]; then
        print_error "PostgreSQL не запустился за 60 секунд"
        exit 1
    fi
    
    print_status "Ожидаем готовности Redis..."
    timeout=30
    while [ $timeout -gt 0 ]; do
        if docker-compose exec -T redis redis-cli ping &>/dev/null; then
            print_success "Redis готов"
            break
        fi
        sleep 2
        timeout=$((timeout-2))
    done
    
    if [ $timeout -le 0 ]; then
        print_error "Redis не запустился за 30 секунд"
        exit 1
    fi
}

# Запуск API сервера
start_api() {
    print_status "Запускаем API сервер..."
    
    # Проверяем, запущен ли уже API сервер
    if curl -s http://localhost:8000/healthz &>/dev/null; then
        print_warning "API сервер уже запущен на порту 8000"
        return 0
    fi
    
    # Запускаем API сервер в фоне
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
    
    # Проверяем, запущен ли уже бот
    if pgrep -f "run_telegram_bot.py" &>/dev/null; then
        print_warning "Telegram бот уже запущен"
        return 0
    fi
    
    # Запускаем бота в фоне
    source venv/bin/activate
    nohup python run_telegram_bot.py > bot.log 2>&1 &
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
    
    # Проверка готовности
    if curl -s http://localhost:8000/readyz &>/dev/null; then
        print_success "✅ Система готова к работе"
    else
        print_warning "⚠️ Система не полностью готова"
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
    echo "🚀 Agatha AI Companion - Система запущена!"
    echo "=========================================="
    echo ""
    echo "📊 Статус сервисов:"
    echo "  • API сервер: http://localhost:8000"
    echo "  • PostgreSQL: localhost:5432"
    echo "  • Redis: localhost:6379"
    echo ""
    echo "📝 Логи:"
    echo "  • API: tail -f api.log"
    echo "  • Bot: tail -f bot.log"
    echo ""
    echo "🛑 Остановка:"
    echo "  • ./stop_all.sh - остановить все"
    echo "  • docker-compose down - остановить только БД"
    echo ""
    echo "🧪 Тестирование:"
    echo "  curl http://localhost:8000/healthz"
    echo "  curl http://localhost:8000/readyz"
    echo ""
}

# Основная функция
main() {
    echo "🤖 Agatha AI Companion - Запуск системы"
    echo "========================================"
    
    check_docker
    check_env
    stop_existing
    start_infrastructure
    start_api
    start_bot
    check_system
    show_status
}

# Обработка сигналов
trap 'echo ""; print_warning "Получен сигнал остановки..."; exit 0' INT TERM

# Запуск
main "$@"
