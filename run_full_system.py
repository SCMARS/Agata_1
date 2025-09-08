
import os
import sys
import subprocess
import time
import signal
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Добавляем путь к проекту
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class AgathaSystemManager:
    """Менеджер для запуска полной системы Agatha"""
    
    def __init__(self):
        self.server_process = None
        self.bot_process = None
        self.running = False
        
        # Настройки из переменных окружения
        self.setup_environment()
    
    def setup_environment(self):
        """Настройка переменных окружения"""
        # Загружаем переменные из config.env файла
        config_env_path = PROJECT_ROOT / "config.env"
        if config_env_path.exists():
            logger.info("📁 Загружаем config.env файл")
            with open(config_env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
            logger.info("✅ Переменные из config.env загружены")
        else:
            logger.warning("⚠️ config.env файл не найден")
        
        # Проверяем критичные переменные
        if not os.getenv('OPENAI_API_KEY'):
            logger.warning("⚠️ OPENAI_API_KEY не найден в окружении")
            openai_key = input("🔑 Введите OpenAI API ключ (или Enter для пропуска): ").strip()
            if openai_key:
                os.environ['OPENAI_API_KEY'] = openai_key
        
        if not os.getenv('TELEGRAM_BOT_TOKEN'):
            logger.warning("⚠️ TELEGRAM_BOT_TOKEN не найден в окружении")
            bot_token = input("🤖 Введите Telegram Bot Token (или Enter для пропуска): ").strip()
            if bot_token:
                os.environ['TELEGRAM_BOT_TOKEN'] = bot_token
        
        # Настройки по умолчанию
        os.environ.setdefault('HOST', '0.0.0.0')
        os.environ.setdefault('PORT', '8000')
        os.environ.setdefault('API_HOST', 'localhost')
        os.environ.setdefault('API_PORT', '8000')
        
        logger.info("🔧 Переменные окружения настроены")
    
    def start_api_server(self):
        """Запускает API сервер"""
        try:
            logger.info("🚀 Запускаем API сервер...")
            
            # Активируем виртуальное окружение и запускаем сервер
            venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
            server_script = PROJECT_ROOT / "run_server.py"
            
            if venv_python.exists():
                python_cmd = str(venv_python)
            else:
                python_cmd = sys.executable
                logger.warning("⚠️ Виртуальное окружение не найдено, используем системный Python")
            
            self.server_process = subprocess.Popen([
                python_cmd, str(server_script)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Ждем запуска сервера
            logger.info("⏳ Ждем запуска API сервера...")
            time.sleep(5)
            
            if self.server_process.poll() is None:
                logger.info("✅ API сервер запущен успешно")
                return True
            else:
                stdout, stderr = self.server_process.communicate()
                logger.error(f"❌ Ошибка запуска API сервера:")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка запуска API сервера: {e}")
            return False
    
    def start_telegram_bot(self):
        """Запускает Telegram bot"""
        try:
            logger.info("🤖 Запускаем Telegram bot...")
            
            venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
            bot_script = PROJECT_ROOT / "telegram_bot.py"
            
            if venv_python.exists():
                python_cmd = str(venv_python)
            else:
                python_cmd = sys.executable
            
            self.bot_process = subprocess.Popen([
                python_cmd, str(bot_script)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            logger.info("⏳ Ждем запуска Telegram bot...")
            time.sleep(3)
            
            if self.bot_process.poll() is None:
                logger.info("✅ Telegram bot запущен успешно")
                return True
            else:
                stdout, stderr = self.bot_process.communicate()
                logger.error(f"❌ Ошибка запуска Telegram bot:")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка запуска Telegram bot: {e}")
            return False
    
    def test_system(self):
        """Тестирует работу системы"""
        logger.info("🧪 Тестируем систему...")
        
        try:
            import requests
            
            # Тест API health check
            api_url = f"http://localhost:{os.getenv('PORT', '5000')}"
            response = requests.get(f"{api_url}/healthz", timeout=5)
            
            if response.status_code == 200:
                logger.info("✅ API сервер отвечает")
                
                # Тест endpoints памяти
                info_response = requests.get(f"{api_url}/api/info", timeout=5)
                if info_response.status_code == 200:
                    data = info_response.json()
                    memory_endpoints = data.get('endpoints', {}).get('memory', {})
                    if memory_endpoints:
                        logger.info("✅ Memory endpoints доступны")
                        logger.info(f"📋 Доступные endpoints: {list(memory_endpoints.keys())}")
                    else:
                        logger.warning("⚠️ Memory endpoints не найдены")
                else:
                    logger.error("❌ Ошибка получения API info")
            else:
                logger.error("❌ API сервер не отвечает")
                
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования: {e}")
    
    def stop_system(self):
        """Останавливает всю систему"""
        logger.info("🛑 Останавливаем систему...")
        
        if self.bot_process:
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=5)
                logger.info("✅ Telegram bot остановлен")
            except subprocess.TimeoutExpired:
                self.bot_process.kill()
                logger.info("🔪 Telegram bot принудительно остановлен")
            except Exception as e:
                logger.error(f"❌ Ошибка остановки bot: {e}")
        
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                logger.info("✅ API сервер остановлен")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                logger.info("🔪 API сервер принудительно остановлен")
            except Exception as e:
                logger.error(f"❌ Ошибка остановки сервера: {e}")
        
        self.running = False
    
    def run(self):
        """Запускает полную систему"""
        print("🚀 ЗАПУСК ПОЛНОЙ СИСТЕМЫ AGATHA")
        print("=" * 50)
        print("🤖 AI Companion с системой памяти")
        print("📱 Telegram Bot для тестирования")
        print("🧠 LangChain + LangGraph + ChromaDB")
        print("=" * 50)
        
        try:
            # Запускаем API сервер
            if not self.start_api_server():
                logger.error("❌ Не удалось запустить API сервер")
                return False
            
            # Тестируем систему
            self.test_system()
            
            # Запускаем Telegram bot
            if not self.start_telegram_bot():
                logger.error("❌ Не удалось запустить Telegram bot")
                self.stop_system()
                return False
            
            self.running = True
            
            print("\n🎉 СИСТЕМА ЗАПУЩЕНА УСПЕШНО!")
            print("=" * 50)
            print(f"🌐 API сервер: http://localhost:{os.getenv('PORT', '5000')}")
            print(f"🤖 Telegram bot: @{os.getenv('TELEGRAM_BOT_TOKEN', '').split(':')[0]}")
            print("📋 Доступные API endpoints:")
            print("   • GET  /healthz - проверка здоровья")
            print("   • GET  /api/info - информация об API")
            print("   • POST /api/chat - чат с Agatha")
            print("   • POST /api/memory/<user_id>/add - добавить в память")
            print("   • POST /api/memory/<user_id>/search - поиск в памяти")
            print("   • GET  /api/memory/<user_id>/overview - обзор памяти")
            print("   • POST /api/memory/<user_id>/clear - очистить память")
            print("=" * 50)
            print("💡 Используйте Telegram bot для тестирования системы памяти")
            print("🛑 Нажмите Ctrl+C для остановки")
            
            # Ожидаем сигнал остановки
            def signal_handler(signum, frame):
                logger.info("📡 Получен сигнал остановки")
                self.stop_system()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Мониторим процессы
            while self.running:
                time.sleep(1)
                
                # Проверяем состояние процессов
                if self.server_process and self.server_process.poll() is not None:
                    logger.error("❌ API сервер неожиданно остановился")
                    break
                
                if self.bot_process and self.bot_process.poll() is not None:
                    logger.error("❌ Telegram bot неожиданно остановился")
                    break
            
            return True
            
        except KeyboardInterrupt:
            logger.info("📡 Получен сигнал остановки от пользователя")
            self.stop_system()
            return True
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            self.stop_system()
            return False


def main():
    """Главная функция"""
    manager = AgathaSystemManager()
    
    try:
        success = manager.run()
        if success:
            print("✅ Система завершена успешно")
        else:
            print("❌ Система завершена с ошибками")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
