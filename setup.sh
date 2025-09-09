#!/bin/bash

# Agatha AI Companion - Первоначальная настройка проекта
# Этот скрипт настраивает проект с нуля: устанавливает зависимости, создает окружение, настраивает конфигурацию

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
    echo -e "${PURPLE}🤖 Agatha AI Companion - Настройка${NC}"
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

# Проверка операционной системы
check_os() {
    print_step "Проверяем операционную систему..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        print_success "macOS обнаружена"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        print_success "Linux обнаружен"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        print_success "Windows обнаружена"
    else
        print_warning "Неизвестная ОС: $OSTYPE"
        OS="unknown"
    fi
}

# Проверка Python
check_python() {
    print_step "Проверяем Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION найден"
        
        # Проверяем версию Python
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
            print_error "Требуется Python 3.8 или выше. Текущая версия: $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python3 не найден. Установите Python 3.8+ и попробуйте снова."
        exit 1
    fi
}

# Проверка pip
check_pip() {
    print_step "Проверяем pip..."
    
    if command -v pip3 &> /dev/null; then
        print_success "pip3 найден"
    else
        print_error "pip3 не найден. Установите pip и попробуйте снова."
        exit 1
    fi
}

# Проверка Git
check_git() {
    print_step "Проверяем Git..."
    
    if command -v git &> /dev/null; then
        print_success "Git найден"
    else
        print_warning "Git не найден. Рекомендуется установить Git для версионирования."
    fi
}

# Проверка Docker (опционально)
check_docker() {
    print_step "Проверяем Docker..."
    
    if command -v docker &> /dev/null; then
        if docker ps &> /dev/null; then
            print_success "Docker найден и запущен"
            DOCKER_AVAILABLE=true
        else
            print_warning "Docker найден, но не запущен. Запустите Docker Desktop."
            DOCKER_AVAILABLE=false
        fi
    else
        print_warning "Docker не найден. Для полной функциональности установите Docker."
        DOCKER_AVAILABLE=false
    fi
}

# Создание виртуального окружения
create_venv() {
    print_step "Создаем виртуальное окружение..."
    
    if [ -d "venv" ]; then
        print_warning "Виртуальное окружение уже существует"
        read -p "Пересоздать? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Удаляем старое окружение..."
            rm -rf venv
        else
            print_status "Используем существующее окружение"
            return 0
        fi
    fi
    
    print_status "Создаем новое виртуальное окружение..."
    python3 -m venv venv
    print_success "Виртуальное окружение создано"
}

# Активация виртуального окружения
activate_venv() {
    print_step "Активируем виртуальное окружение..."
    
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_success "Виртуальное окружение активировано"
    else
        print_error "Не удалось активировать виртуальное окружение"
        exit 1
    fi
}

# Обновление pip
upgrade_pip() {
    print_step "Обновляем pip..."
    
    pip install --upgrade pip
    print_success "pip обновлен"
}

# Установка зависимостей
install_dependencies() {
    print_step "Устанавливаем зависимости..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "Файл requirements.txt не найден"
        exit 1
    fi
    
    print_status "Устанавливаем Python пакеты..."
    pip install -r requirements.txt
    
    print_success "Зависимости установлены"
}

# Создание конфигурации
setup_config() {
    print_step "Настраиваем конфигурацию..."
    
    if [ ! -f "config.env" ]; then
        print_error "Файл config.env не найден"
        exit 1
    fi
    
    # Проверяем, нужно ли настраивать API ключи
    if grep -q "your_openai_api_key_here" config.env; then
        print_warning "API ключи не настроены в config.env"
        echo ""
        echo "Для работы системы необходимо настроить API ключи:"
        echo ""
        echo "1. OpenAI API ключ:"
        echo "   - Перейдите на https://platform.openai.com/api-keys"
        echo "   - Создайте новый ключ"
        echo "   - Скопируйте ключ"
        echo ""
        echo "2. Telegram Bot Token:"
        echo "   - Напишите @BotFather в Telegram"
        echo "   - Создайте нового бота командой /newbot"
        echo "   - Скопируйте токен"
        echo ""
        
        read -p "Настроить API ключи сейчас? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            setup_api_keys
        else
            print_warning "API ключи не настроены. Настройте их вручную в config.env"
        fi
    else
        print_success "API ключи уже настроены"
    fi
}

# Настройка API ключей
setup_api_keys() {
    print_step "Настраиваем API ключи..."
    
    # OpenAI API Key
    echo ""
    read -p "Введите OpenAI API ключ: " OPENAI_KEY
    if [ ! -z "$OPENAI_KEY" ]; then
        sed -i.bak "s/your_openai_api_key_here/$OPENAI_KEY/" config.env
        print_success "OpenAI API ключ настроен"
    fi
    
    # Telegram Bot Token
    echo ""
    read -p "Введите Telegram Bot Token: " TELEGRAM_TOKEN
    if [ ! -z "$TELEGRAM_TOKEN" ]; then
        sed -i.bak "s/your_telegram_bot_token_here/$TELEGRAM_TOKEN/" config.env
        print_success "Telegram Bot Token настроен"
    fi
    
    # Очистка backup файлов
    rm -f config.env.bak
}

# Создание необходимых директорий
create_directories() {
    print_step "Создаем необходимые директории..."
    
    mkdir -p logs
    mkdir -p data
    mkdir -p temp
    
    print_success "Директории созданы"
}

# Установка прав на скрипты
setup_permissions() {
    print_step "Настраиваем права на скрипты..."
    
    chmod +x start_local.sh start_all.sh stop_all.sh setup.sh 2>/dev/null || true
    
    print_success "Права на скрипты настроены"
}

# Тестирование установки
test_installation() {
    print_step "Тестируем установку..."
    
    # Тест импорта основных модулей
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from app.config.settings import settings
    print('✅ Настройки загружены')
except Exception as e:
    print(f'❌ Ошибка загрузки настроек: {e}')
    sys.exit(1)

try:
    from app.graph.pipeline import AgathaPipeline
    print('✅ Pipeline импортирован')
except Exception as e:
    print(f'❌ Ошибка импорта pipeline: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_success "Тест установки пройден"
    else
        print_error "Тест установки не пройден"
        exit 1
    fi
}

# Показать следующие шаги
show_next_steps() {
    echo ""
    echo "=========================================="
    echo "🎉 Настройка завершена успешно!"
    echo "=========================================="
    echo ""
    echo "📋 Следующие шаги:"
    echo ""
    echo "1. 🚀 Запуск системы:"
    echo "   ./start_local.sh    # Быстрый запуск (API + бот)"
    echo "   ./start_all.sh      # Полный запуск (с Docker)"
    echo ""
    echo "2. 🧪 Тестирование:"
    echo "   curl http://localhost:8000/healthz"
    echo "   curl http://localhost:8000/readyz"
    echo ""
    echo "3. 📖 Документация:"
    echo "   cat README.md"
    echo ""
    echo "4. 🛑 Остановка:"
    echo "   ./stop_all.sh"
    echo ""
    
    if [ "$DOCKER_AVAILABLE" = true ]; then
        echo "💡 Рекомендуется использовать ./start_all.sh для полной функциональности"
    else
        echo "💡 Используйте ./start_local.sh для быстрого запуска"
    fi
    
    echo ""
    echo "🔧 Если возникли проблемы:"
    echo "   - Проверьте логи: tail -f api.log"
    echo "   - Перезапустите: ./stop_all.sh && ./start_local.sh"
    echo "   - Обратитесь к README.md"
    echo ""
}

# Основная функция
main() {
    print_header
    
    check_os
    check_python
    check_pip
    check_git
    check_docker
    create_venv
    activate_venv
    upgrade_pip
    install_dependencies
    setup_config
    create_directories
    setup_permissions
    test_installation
    show_next_steps
}

# Обработка аргументов
case "${1:-}" in
    --help|-h)
        echo "Использование: $0 [опции]"
        echo ""
        echo "Опции:"
        echo "  --help     Показать эту справку"
        echo "  --force    Принудительно пересоздать окружение"
        echo ""
        echo "Этот скрипт настраивает проект Agatha AI Companion с нуля:"
        echo "- Проверяет системные требования"
        echo "- Создает виртуальное окружение"
        echo "- Устанавливает зависимости"
        echo "- Настраивает конфигурацию"
        echo "- Тестирует установку"
        echo ""
        ;;
    --force)
        print_warning "Принудительная переустановка..."
        rm -rf venv
        main
        ;;
    *)
        main
        ;;
esac
