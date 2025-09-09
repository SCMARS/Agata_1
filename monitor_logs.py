#!/usr/bin/env python3
"""
Мониторинг логов системы живого общения в реальном времени
"""
import subprocess
import sys
import time
from datetime import datetime

def log_monitor(message, level="INFO"):
    """Логирование монитора"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def monitor_api_logs():
    """Мониторинг логов API"""
    log_monitor("🔍 Запуск мониторинга логов API...")
    try:
        process = subprocess.Popen(
            ["tail", "-f", "api.log"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                # Фильтруем только интересные логи
                if any(keyword in line.lower() for keyword in [
                    'openai', 'short_msg', 'splitter', 'living_chat', 
                    'analyzer', 'connector', 'question', 'emotion'
                ]):
                    print(f"📊 API: {line.strip()}")
        
    except KeyboardInterrupt:
        log_monitor("⏹️ Мониторинг API остановлен")
    except Exception as e:
        log_monitor(f"❌ Ошибка мониторинга API: {e}", "ERROR")

def monitor_bot_logs():
    """Мониторинг логов бота"""
    log_monitor("🔍 Запуск мониторинга логов бота...")
    try:
        process = subprocess.Popen(
            ["tail", "-f", "bot.log"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                # Фильтруем только интересные логи
                if any(keyword in line.lower() for keyword in [
                    'openai', 'short_msg', 'splitter', 'living_chat',
                    'analyzer', 'connector', 'question', 'emotion'
                ]):
                    print(f"🤖 BOT: {line.strip()}")
        
    except KeyboardInterrupt:
        log_monitor("⏹️ Мониторинг бота остановлен")
    except Exception as e:
        log_monitor(f"❌ Ошибка мониторинга бота: {e}", "ERROR")

def monitor_all_logs():
    """Мониторинг всех логов"""
    log_monitor("🚀 Запуск мониторинга всех логов...")
    log_monitor("Нажмите Ctrl+C для остановки")
    
    try:
        # Запускаем мониторинг API и бота параллельно
        import threading
        
        api_thread = threading.Thread(target=monitor_api_logs)
        bot_thread = threading.Thread(target=monitor_bot_logs)
        
        api_thread.daemon = True
        bot_thread.daemon = True
        
        api_thread.start()
        bot_thread.start()
        
        # Ждем завершения
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        log_monitor("⏹️ Мониторинг остановлен")
    except Exception as e:
        log_monitor(f"❌ Ошибка мониторинга: {e}", "ERROR")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "api":
            monitor_api_logs()
        elif sys.argv[1] == "bot":
            monitor_bot_logs()
        else:
            print("Использование: python monitor_logs.py [api|bot]")
    else:
        monitor_all_logs()
