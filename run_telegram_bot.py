#!/usr/bin/env python3
"""
Скрипт запуска Telegram бота без хардкода
"""
import os
import sys
import logging
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_environment():
    """Настройка окружения для бота"""
    # Проверяем наличие токена бота
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ Ошибка: Переменная окружения TELEGRAM_BOT_TOKEN не установлена")
        print("💡 Установите её командой:")
        print("   export TELEGRAM_BOT_TOKEN='8181686852:AAH93K4NhfI2oUhhrvLd9MK8Eln1_XsyFi4'")
        return False
    
    # Проверяем переменную окружения для админов (опционально)
    admin_users = os.getenv('BOT_ADMIN_USERS')
    if not admin_users:
        print("⚠️ Предупреждение: BOT_ADMIN_USERS не установлена")
        print("💡 Для включения админских команд установите:")
        print("   export BOT_ADMIN_USERS='[123456789, 987654321]'")
        print("   (замените на ваши Telegram user ID)")
    
    # Устанавливаем переменные окружения по умолчанию
    os.environ.setdefault('APP_ENVIRONMENT', 'development')
    os.environ.setdefault('CONFIG_DIR', str(project_root / 'app' / 'config'))
    os.environ.setdefault('CONFIG_LOG_LEVEL', 'INFO')
    
    return True

def main():
    """Основная функция запуска"""
    print("🤖 Запуск Telegram бота Agata...")
    
    # Настраиваем окружение
    if not setup_environment():
        sys.exit(1)
    
    try:
        # Импортируем и запускаем бота
        from app.bots.telegram_bot import main as bot_main
        bot_main()
        
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Убедитесь, что все зависимости установлены:")
        print("   pip install python-telegram-bot pyyaml psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
