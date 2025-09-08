#!/usr/bin/env python3
"""
Простой скрипт запуска Agatha AI Companion
Автоматически запускает API сервер и Telegram бота
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path

def print_banner():
    """Печатает красивый баннер"""
    print("=" * 60)
    print("🤖 AGATHA AI COMPANION - АВТОЗАПУСК")
    print("=" * 60)
    print("📁 Проект:", os.getcwd())
    print("🐍 Python:", sys.version.split()[0])
    print("=" * 60)

def check_environment():
    """Проверяет окружение"""
    print("🔍 Проверка окружения...")
    
    # Проверяем виртуальное окружение
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️ Виртуальное окружение не активировано!")
        print("💡 Запустите: source venv/bin/activate")
        return False
    
    # Проверяем файлы
    required_files = ['run_server.py', 'telegram_bot.py', 'config.env']
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ Файл не найден: {file}")
            return False
    
    # Проверяем зависимости
    try:
        import flask
        import openai
        import telegram
        print("✅ Основные зависимости найдены")
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("💡 Запустите: pip install -r requirements.txt")
        return False
    
    # Проверяем переменные окружения
    config_env = Path('config.env')
    if config_env.exists():
        print("✅ Конфигурация найдена")
        # Загружаем переменные из config.env
        with open(config_env, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    return True

def start_api_server():
    """Запускает API сервер"""
    print("🚀 Запуск API сервера...")
    try:
        api_process = subprocess.Popen(
            [sys.executable, 'run_server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Даем время на запуск
        time.sleep(3)
        
        # Проверяем, что процесс запустился
        if api_process.poll() is None:
            print("✅ API сервер запущен (PID: {})".format(api_process.pid))
            return api_process
        else:
            stdout, stderr = api_process.communicate()
            print("❌ Ошибка запуска API сервера:")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return None
            
    except Exception as e:
        print(f"❌ Ошибка запуска API сервера: {e}")
        return None

def start_telegram_bot():
    """Запускает Telegram бота"""
    print("🤖 Запуск Telegram бота...")
    try:
        bot_process = subprocess.Popen(
            [sys.executable, 'telegram_bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Даем время на запуск
        time.sleep(2)
        
        # Проверяем, что процесс запустился
        if bot_process.poll() is None:
            print("✅ Telegram бот запущен (PID: {})".format(bot_process.pid))
            return bot_process
        else:
            stdout, stderr = bot_process.communicate()
            print("❌ Ошибка запуска Telegram бота:")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return None
            
    except Exception as e:
        print(f"❌ Ошибка запуска Telegram бота: {e}")
        return None

def test_api_server():
    """Тестирует API сервер"""
    print("🧪 Тестирование API сервера...")
    try:
        import requests
        response = requests.get('http://localhost:8000/healthz', timeout=5)
        if response.status_code == 200:
            print("✅ API сервер отвечает корректно")
            return True
        else:
            print(f"⚠️ API сервер вернул статус: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API сервер недоступен: {e}")
        return False

def cleanup_processes(processes):
    """Завершает процессы"""
    print("\n🛑 Завершение процессов...")
    for name, process in processes.items():
        if process and process.poll() is None:
            print(f"🛑 Завершение {name} (PID: {process.pid})")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"🔥 Принудительное завершение {name}")

def main():
    """Основная функция"""
    print_banner()
    
    # Проверяем окружение
    if not check_environment():
        print("\n❌ Проверка окружения не пройдена!")
        print("💡 Исправьте ошибки и попробуйте снова")
        return 1
    
    processes = {}
    
    try:
        # Запускаем API сервер
        api_process = start_api_server()
        if not api_process:
            print("❌ Не удалось запустить API сервер")
            return 1
        processes['API Server'] = api_process
        
        # Тестируем API сервер
        if not test_api_server():
            print("❌ API сервер не работает корректно")
            cleanup_processes(processes)
            return 1
        
        # Запускаем Telegram бота
        bot_process = start_telegram_bot()
        if not bot_process:
            print("⚠️ Не удалось запустить Telegram бота (API сервер продолжает работать)")
        else:
            processes['Telegram Bot'] = bot_process
        
        # Выводим информацию о запуске
        print("\n" + "=" * 60)
        print("🎉 AGATHA AI COMPANION ЗАПУЩЕНА!")
        print("=" * 60)
        print("🌐 API сервер: http://localhost:8000")
        print("📊 Проверка здоровья: http://localhost:8000/healthz")
        print("📖 API документация: http://localhost:8000/api/info")
        if 'Telegram Bot' in processes:
            print("🤖 Telegram бот: Активен и готов к работе")
        print("=" * 60)
        print("💡 Для остановки нажмите Ctrl+C")
        print("=" * 60)
        
        # Ожидаем сигнала завершения
        def signal_handler(signum, frame):
            cleanup_processes(processes)
            print("\n👋 Agatha AI Companion остановлена")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Мониторим процессы
        while True:
            time.sleep(5)
            
            # Проверяем API сервер
            if processes.get('API Server') and processes['API Server'].poll() is not None:
                print("❌ API сервер остановился неожиданно!")
                break
            
            # Проверяем Telegram бота
            if processes.get('Telegram Bot') and processes['Telegram Bot'].poll() is not None:
                print("⚠️ Telegram бот остановился, перезапуск...")
                bot_process = start_telegram_bot()
                if bot_process:
                    processes['Telegram Bot'] = bot_process
                else:
                    print("❌ Не удалось перезапустить Telegram бота")
                    del processes['Telegram Bot']
        
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал завершения...")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
    finally:
        cleanup_processes(processes)
        print("👋 Agatha AI Companion остановлена")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())