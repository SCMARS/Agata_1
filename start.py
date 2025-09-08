#!/usr/bin/env python3
"""
Простой скрипт запуска системы Agatha
Автоматически загружает config.env и запускает API сервер
"""
import os
import sys
import subprocess
from pathlib import Path

# Добавляем путь к проекту
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def load_config_env():
    """Загружает переменные из config.env"""
    config_env_path = PROJECT_ROOT / "config.env"
    if config_env_path.exists():
        print("📁 Загружаем config.env...")
        with open(config_env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print("✅ Переменные окружения загружены")
        return True
    else:
        print("❌ config.env файл не найден!")
        return False

def main():
    """Главная функция"""
    print("🚀 ЗАПУСК AGATHA AI COMPANION")
    print("=" * 40)
    
    # Загружаем конфигурацию
    if not load_config_env():
        print("Создайте config.env файл с настройками")
        return False
    
    # Проверяем ключи
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY не найден в config.env")
        return False
    
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        print("❌ TELEGRAM_BOT_TOKEN не найден в config.env")
        return False
    
    print(f"✅ OpenAI API Key: {os.getenv('OPENAI_API_KEY')[:20]}...")
    print(f"✅ Telegram Token: {os.getenv('TELEGRAM_BOT_TOKEN').split(':')[0]}")
    print(f"🌐 Порт сервера: {os.getenv('PORT', '8000')}")
    
    # Запускаем API сервер
    print("\n🚀 Запускаем API сервер...")
    try:
        venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
        if venv_python.exists():
            python_cmd = str(venv_python)
        else:
            python_cmd = sys.executable
            print("⚠️ Виртуальное окружение не найдено, используем системный Python")
        
        # Запускаем сервер
        server_process = subprocess.Popen([
            python_cmd, str(PROJECT_ROOT / "run_server.py")
        ])
        
        print(f"✅ API сервер запущен с PID: {server_process.pid}")
        print(f"🌐 API доступно на: http://localhost:{os.getenv('PORT', '8000')}")
        print("\n💡 Для запуска Telegram bot откройте новый терминал и выполните:")
        print(f"   cd {PROJECT_ROOT}")
        print("   source venv/bin/activate")
        print("   python telegram_bot.py")
        print("\n🛑 Нажмите Ctrl+C для остановки")
        
        # Ожидаем завершения
        try:
            server_process.wait()
        except KeyboardInterrupt:
            print("\n📡 Получен сигнал остановки")
            server_process.terminate()
            server_process.wait()
            print("✅ Сервер остановлен")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
