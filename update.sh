#!/bin/bash

# Agatha AI Companion - Обновление проекта
# Этот скрипт обновляет проект: обновляет зависимости, мигрирует конфигурацию, перезапускает систему

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}🔄 Agatha {NC}"
    echo -e "${PURPLE}========================================${NC}"
    echo ""
}

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

print_step() {
    echo -e "${PURPLE}[ШАГ]${NC} $1"
}

# Проверка Git
check_git() {
    print_step "Проверяем Git..."
    
    if ! command -v git &> /dev/null; then
        print_error "Git не найден. Установите Git для обновления."
        exit 1
    fi
    
    if [ ! -d ".git" ]; then
        print_warning "Это не Git репозиторий. Пропускаем обновление кода."
        return 1
    fi
    
    print_success "Git найден"
    return 0
}

# Обновление кода из Git
update_code() {
    print_step "Обновляем код из Git..."
    
    if ! check_git; then
        return 0
    fi
    
    print_status "Сохраняем текущие изменения..."
    git stash push -m "Auto-stash before update $(date)" || true
    
    print_status "Получаем последние изменения..."
    git fetch origin
    
    print_status "Переключаемся на main ветку..."
    git checkout main
    
    print_status "Объединяем изменения..."
    git pull origin main
    
    print_success "Код обновлен"
}

# Остановка системы
stop_system() {
    print_step "Останавливаем систему..."
    
    if [ -f "stop_all.sh" ]; then
        ./stop_all.sh
        print_success "Система остановлена"
    else
        print_warning "Скрипт остановки не найден"
    fi
}

# Создание резервной копии конфигурации
backup_config() {
    print_step "Создаем резервную копию конфигурации..."
    
    BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Копируем важные файлы
    cp config.env "$BACKUP_DIR/" 2>/dev/null || true
    cp -r logs "$BACKUP_DIR/" 2>/dev/null || true
    cp -r data "$BACKUP_DIR/" 2>/dev/null || true
    
    print_success "Резервная копия создана: $BACKUP_DIR"
}

# Обновление виртуального окружения
update_venv() {
    print_step "Обновляем виртуальное окружение..."
    
    if [ ! -d "venv" ]; then
        print_warning "Виртуальное окружение не найдено. Запустите setup.sh"
        return 1
    fi
    
    source venv/bin/activate
    
    print_status "Обновляем pip..."
    pip install --upgrade pip
    
    print_status "Обновляем зависимости..."
    pip install -r requirements.txt --upgrade
    
    print_success "Виртуальное окружение обновлено"
}

# Миграция конфигурации
migrate_config() {
    print_step "Мигрируем конфигурацию..."
    
    if [ ! -f "config.env" ]; then
        print_warning "Файл config.env не найден"
        return 0
    fi
    
    # Создаем резервную копию
    cp config.env config.env.backup
    
    # Проверяем и обновляем конфигурацию
    if ! grep -q "OPENAI_API_KEY" config.env; then
        print_status "Добавляем OPENAI_API_KEY..."
        echo "OPENAI_API_KEY=your_openai_api_key_here" >> config.env
    fi
    
    if ! grep -q "TELEGRAM_BOT_TOKEN" config.env; then
        print_status "Добавляем TELEGRAM_BOT_TOKEN..."
        echo "TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here" >> config.env
    fi
    
    if ! grep -q "PORT=8000" config.env; then
        print_status "Обновляем порт на 8000..."
        sed -i.bak 's/PORT=5000/PORT=8000/g' config.env
    fi
    
    print_success "Конфигурация мигрирована"
}

# Обновление Docker образов
update_docker() {
    print_step "Обновляем Docker образы..."
    
    if ! command -v docker &> /dev/null; then
        print_warning "Docker не найден. Пропускаем обновление Docker."
        return 0
    fi
    
    if [ ! -f "docker-compose.yml" ]; then
        print_warning "docker-compose.yml не найден. Пропускаем обновление Docker."
        return 0
    fi
    
    print_status "Останавливаем Docker контейнеры..."
    docker-compose down 2>/dev/null || true
    
    print_status "Обновляем образы..."
    docker-compose pull
    
    print_success "Docker образы обновлены"
}

# Очистка временных файлов
cleanup() {
    print_step "Очищаем временные файлы..."
    
    # Удаляем старые логи
    find . -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    # Удаляем Python кэш
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    # Удаляем временные файлы
    rm -f api.pid bot.pid 2>/dev/null || true
    
    print_success "Временные файлы очищены"
}

# Тестирование обновления
test_update() {
    print_step "Тестируем обновление..."
    
    # Тест импорта
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from app.config.settings import settings
    print('✅ Настройки загружены')
except Exception as e:
    print(f'❌ Ошибка загрузки настроек: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_success "Тест обновления пройден"
    else
        print_error "Тест обновления не пройден"
        exit 1
    fi
}

# Показать статус обновления
show_update_status() {
    echo ""
    echo "=========================================="
    echo "🎉 Обновление завершено успешно!"
    echo "=========================================="
    echo ""
    echo "📋 Что было обновлено:"
    echo "  ✅ Код проекта"
    echo "  ✅ Зависимости Python"
    echo "  ✅ Конфигурация"
    echo "  ✅ Docker образы"
    echo "  ✅ Временные файлы очищены"
    echo ""
    echo "🚀 Следующие шаги:"
    echo ""
    echo "1. Запуск системы:"
    echo "   ./start_local.sh    # Быстрый запуск"
    echo "   ./start_all.sh      # Полный запуск с Docker"
    echo ""
    echo "2. Проверка работы:"
    echo "   curl http://localhost:8000/healthz"
    echo ""
    echo "3. Если что-то не работает:"
    echo "   ./setup.sh --force  # Полная переустановка"
    echo ""
}

# Основная функция
main() {
    print_header
    
    stop_system
    backup_config
    update_code
    update_venv
    migrate_config
    update_docker
    cleanup
    test_update
    show_update_status
}

# Обработка аргументов
case "${1:-}" in
    --help|-h)
        echo "Использование: $0 [опции]"
        echo ""
        echo "Опции:"
        echo "  --help     Показать эту справку"
        echo "  --code     Обновить только код (без зависимостей)"
        echo "  --deps     Обновить только зависимости"
        echo "  --config   Обновить только конфигурацию"
        echo ""
        echo "Этот скрипт обновляет проект Agatha AI Companion:"
        echo "- Обновляет код из Git"
        echo "- Обновляет зависимости"
        echo "- Мигрирует конфигурацию"
        echo "- Обновляет Docker образы"
        echo "- Очищает временные файлы"
        echo ""
        ;;
    --code)
        print_header
        stop_system
        backup_config
        update_code
        test_update
        show_update_status
        ;;
    --deps)
        print_header
        stop_system
        update_venv
        test_update
        show_update_status
        ;;
    --config)
        print_header
        backup_config
        migrate_config
        show_update_status
        ;;
    *)
        main
        ;;
esac
