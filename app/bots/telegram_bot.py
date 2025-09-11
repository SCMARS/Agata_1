import os
import json
import asyncio
import logging
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from collections import defaultdict
import traceback

# Импорты с fallback
try:
    import telegram
    from telegram import Update, BotCommand
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ python-telegram-bot not installed. Install with: pip install python-telegram-bot")


@dataclass
class BotConfig:
    """Конфигурация бота из настроек"""
    token: str
    timeout: int = 30
    connection_pool_size: int = 8
    allowed_users: Set[int] = field(default_factory=set)
    admin_users: Set[int] = field(default_factory=set)
    max_message_length: int = 4096
    rate_limit_messages_per_minute: int = 20
    rate_limit_commands_per_hour: int = 100
    commands: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    messages: Dict[str, str] = field(default_factory=dict)
    memory_integration: Dict[str, Any] = field(default_factory=dict)
    logging_config: Dict[str, Any] = field(default_factory=dict)


class ProductionTelegramBot:
    """Production-ready Telegram Bot без хардкода"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = None
        self.application = None
        self.rate_limiter = defaultdict(list)

        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # Загружаем конфигурацию
        self._load_config()
        
        # Настраиваем логирование
        self._setup_logging()
        
        # Настраиваем бота
        self._setup_bot()
    
    def _load_config(self):
        """Загружает конфигурацию бота"""
        try:
            # Получаем токен из переменной окружения
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            if not token:
                raise ValueError("TELEGRAM_BOT_TOKEN не установлена")
            
            # Получаем админов из переменной окружения
            admin_users_str = os.getenv('BOT_ADMIN_USERS', '[]')
            try:
                admin_users = set(json.loads(admin_users_str))
            except json.JSONDecodeError:
                admin_users = set()
                print("⚠️ Предупреждение: BOT_ADMIN_USERS не установлена")
                print("💡 Для включения админских команд установите:")
                print("   export BOT_ADMIN_USERS='[123456789, 987654321]'")
                print("   (замените на ваши Telegram user ID)")
            
            self.config = BotConfig(
                token=token,
                allowed_users=set(),  # Пустой список = все пользователи
                admin_users=admin_users,
                commands={
                    "start": {"description": "Запуск бота и приветствие", "enabled": True},
                    "help": {"description": "Справка по командам", "enabled": True},
                    "memory": {"description": "Добавить сообщение в память", "enabled": True},
                    "search": {"description": "Поиск в памяти", "enabled": True},
                    "overview": {"description": "Обзор памяти", "enabled": True},
                    "clear": {"description": "Очистить память", "enabled": True},
                    "test": {"description": "Тест системы памяти", "enabled": True},
                },
                messages={
                    "welcome": """🤖 Добро пожаловать в Agatha Memory Bot!

Я - бот для тестирования системы памяти Agatha с LangChain и LangGraph.

Доступные команды:
• /start - Начать работу
• /help - Справка по командам  
• /memory - Добавить сообщение в память
• /search <запрос> - Поиск в памяти
• /overview - Обзор памяти
• /clear - Очистить память
• /test - Тест системы памяти

Как использовать:
1. Просто напишите сообщение - оно будет добавлено в память
2. Используйте команды для управления памятью
3. Тестируйте поиск и контекст

Ваш ID: {user_id}""",
                    "help": """📖 Справка по командам:

/start - перезапуск и приветствие
/help - эта справка
/memory <текст> - сохранить текст в память
/search <запрос> - найти в памяти
/overview - обзор памяти
/clear - очистить память
/test - тест системы

Все обычные сообщения автоматически сохраняются в память.""",
                    "unauthorized": "⛔ У вас нет доступа к этой команде",
                    "error_generic": "❌ Произошла ошибка: {error}",
                    "memory_saved": "✅ Сохранено в память",
                    "memory_error": "❌ Ошибка сохранения: {error}",
                    "search_no_results": "🔍 Ничего не найдено по запросу: {query}",
                }
            )
            
            self.logger.info("Bot config loaded successfully. Admin users: %d", len(self.config.admin_users))
            
        except Exception as e:
            self.logger.error(f"Failed to load bot config: {e}")
            raise
    
    def _setup_logging(self):
        """Настраивает логирование"""
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(name)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('telegram_bot.log'),
                logging.StreamHandler()
            ]
        )
        
        # Настраиваем логгер telegram библиотеки
        telegram_logger = logging.getLogger('telegram')
        telegram_logger.setLevel(logging.WARNING)  # Меньше спама
    
    def _setup_bot(self):
        """Настраивает Telegram бота"""
        if not self.config:
            raise RuntimeError("Bot config not loaded")
        
        if not TELEGRAM_AVAILABLE:
            raise RuntimeError("Telegram library not available")
        
        # Создаем приложение
        self.application = Application.builder().token(self.config.token).build()
        
        # Добавляем обработчики команд
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("memory", self._memory_command))
        self.application.add_handler(CommandHandler("search", self._search_command))
        self.application.add_handler(CommandHandler("overview", self._overview_command))
        self.application.add_handler(CommandHandler("clear", self._clear_command))
        self.application.add_handler(CommandHandler("test", self._test_command))
        
        # Добавляем обработчик обычных сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        self.logger.info("Telegram bot setup completed")
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        welcome_msg = self.config.messages["welcome"].format(user_id=user_id)
        await update.message.reply_text(welcome_msg)
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        await update.message.reply_text(self.config.messages["help"])
    
    async def _memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /memory"""
        user_id = update.effective_user.id
        text = ' '.join(context.args) if context.args else "Тестовое сообщение для памяти"
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/memory/{user_id}/add",
                    json={"message": text, "role": "user"}
                )
                
            if response.status_code == 200:
                await update.message.reply_text(self.config.messages["memory_saved"])
            else:
                await update.message.reply_text(
                    self.config.messages["memory_error"].format(error=f"HTTP {response.status_code}")
                )
        except Exception as e:
            await update.message.reply_text(
                self.config.messages["memory_error"].format(error=str(e))
            )
    
    async def _search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /search"""
        user_id = update.effective_user.id
        query = ' '.join(context.args) if context.args else "тест"
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = await client.get(
                    f"{self.api_base_url}/api/memory/{user_id}/search",
                    params={"query": query, "limit": 5}
                )
                
            if response.status_code == 200:
                results = response.json()
                if results.get("results"):
                    message = "🔍 Результаты поиска:\n\n"
                    for i, result in enumerate(results["results"][:3], 1):
                        message += f"{i}. {result['content'][:100]}...\n"
                    await update.message.reply_text(message)
                else:
                    await update.message.reply_text(
                        self.config.messages["search_no_results"].format(query=query)
                    )
            else:
                await update.message.reply_text(
                    self.config.messages["error_generic"].format(error=f"HTTP {response.status_code}")
                )
        except Exception as e:
            await update.message.reply_text(
                self.config.messages["error_generic"].format(error=str(e))
            )
    
    async def _overview_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /overview"""
        user_id = update.effective_user.id
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = await client.get(f"{self.api_base_url}/api/memory/{user_id}/overview")
                
            if response.status_code == 200:
                overview = response.json()
                message = f"📊 Обзор памяти для пользователя {user_id}:\n\n"
                message += f"Короткая память: {overview['overview']['levels']['short_term']['total_messages']} сообщений\n"
                message += f"Долгая память: {overview['overview']['levels']['long_term']['total_documents']} документов\n"
                await update.message.reply_text(message)
            else:
                await update.message.reply_text(
                    self.config.messages["error_generic"].format(error=f"HTTP {response.status_code}")
                )
        except Exception as e:
            await update.message.reply_text(
                self.config.messages["error_generic"].format(error=str(e))
            )
    
    async def _clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /clear"""
        user_id = update.effective_user.id
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = await client.post(f"{self.api_base_url}/api/memory/{user_id}/clear")
                
            if response.status_code == 200:
                await update.message.reply_text("✅ Память очищена")
            else:
                await update.message.reply_text(
                    self.config.messages["error_generic"].format(error=f"HTTP {response.status_code}")
                )
        except Exception as e:
            await update.message.reply_text(
                self.config.messages["error_generic"].format(error=str(e))
            )
    
    async def _test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /test"""
        user_id = update.effective_user.id
        
        try:
            # Тестируем сохранение
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/memory/{user_id}/add",
                    json={"message": f"Тест от {datetime.now().strftime('%H:%M:%S')}", "role": "user"}
                )
                
            if response.status_code == 200:
                await update.message.reply_text("✅ Тест системы памяти прошел успешно!")
            else:
                await update.message.reply_text(
                    self.config.messages["error_generic"].format(error=f"HTTP {response.status_code}")
                )
        except Exception as e:
            await update.message.reply_text(
                self.config.messages["error_generic"].format(error=str(e))
            )
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Проверяем rate limiting
        if not self._check_rate_limit(user_id, "message"):
            await update.message.reply_text("⏰ Слишком много сообщений. Подождите немного.")
            return
        
        # Инициализируем буфер сообщений для пользователя
        if not hasattr(self, 'user_message_buffers'):
            self.user_message_buffers = {}
        
        if user_id not in self.user_message_buffers:
            self.user_message_buffers[user_id] = {
                'messages': [],
                'last_message_time': None,
                'timer_task': None
            }
        
        # Добавляем сообщение в буфер
        current_time = datetime.now()
        self.user_message_buffers[user_id]['messages'].append({
            "role": "user", 
            "content": message_text,
            "timestamp": current_time
        })
        self.user_message_buffers[user_id]['last_message_time'] = current_time
        
        self.logger.info(f"📝 Добавлено сообщение в буфер для {user_id}: '{message_text}'")
        self.logger.info(f"📊 Всего в буфере: {len(self.user_message_buffers[user_id]['messages'])} сообщений")
        
        # Отменяем предыдущий таймер, если есть
        if self.user_message_buffers[user_id]['timer_task']:
            self.user_message_buffers[user_id]['timer_task'].cancel()
        
        # Устанавливаем новый таймер на 10 секунд
        chat_id = update.effective_chat.id
        self.user_message_buffers[user_id]['chat_id'] = chat_id
        self.user_message_buffers[user_id]['timer_task'] = asyncio.create_task(
            self._process_buffered_messages(user_id)
        )
    
    async def _process_buffered_messages(self, user_id: int):
        """Обрабатывает буферизованные сообщения после задержки"""
        try:
            # Ждем 10 секунд
            await asyncio.sleep(10)
            
            if user_id not in self.user_message_buffers:
                return
            
            buffer = self.user_message_buffers[user_id]
            messages = buffer['messages']
            chat_id = buffer.get('chat_id')
            
            if not messages or not chat_id:
                return
            
            self.logger.info(f"⏰ Обрабатываем {len(messages)} буферизованных сообщений для {user_id}")
            
            # Отправляем все сообщения в чат API
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/chat",
                    json={
                        "user_id": str(user_id),
                        "messages": [{"role": msg["role"], "content": msg["content"]} for msg in messages]
                    }
                )
            
            self.logger.info(f"📡 Chat API ответил: {response.status_code}")
            
            if response.status_code == 200:
                chat_response = response.json()
                parts = chat_response.get("parts", [])
                delays_ms = chat_response.get("delays_ms", [])
                
                self.logger.info(f"🧠 Получены части ответа: {len(parts)}")
                

                for i, part in enumerate(parts):
                    # Используем задержку из API или стандартную
                    delay = delays_ms[i] / 1000 if i < len(delays_ms) else 0.5
                    
                    if i > 0:
                        await asyncio.sleep(delay)
                    
                    # Отправляем через bot API
                    from telegram import Bot
                    bot = Bot(token=self.config.token)
                    await bot.send_message(
                        chat_id=chat_id,
                        text=part
                    )
                    self.logger.info(f"✅ Отправлена часть {i+1}: {part[:50]}...")
                
                # Очищаем буфер после успешной обработки
                self.user_message_buffers[user_id]['messages'] = []
                
            else:
                # Ошибка API
                self.logger.error(f"❌ Chat API вернул ошибку: {response.status_code}")
                from telegram import Bot
                bot = Bot(token=self.config.token)
                await bot.send_message(
                    chat_id=chat_id,
                    text="😔 Извини, что-то пошло не так. Попробуй еще раз."
                )
                # Очищаем буфер при ошибке
                self.user_message_buffers[user_id]['messages'] = []
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки буферизованных сообщений для {user_id}: {e}")
            if user_id in self.user_message_buffers:
                chat_id = self.user_message_buffers[user_id].get('chat_id')
                if chat_id:
                    from telegram import Bot
                    bot = Bot(token=self.config.token)
                    await bot.send_message(
                        chat_id=chat_id,
                        text="😔 Извини, что-то пошло не так. Попробуй еще раз."
                    )
                self.user_message_buffers[user_id]['messages'] = []
    
    def _check_rate_limit(self, user_id: int, action: str) -> bool:
        """Проверяет rate limiting"""
        now = datetime.now()
        user_actions = self.rate_limiter[user_id]
        
        # Удаляем старые действия
        cutoff = now - timedelta(minutes=1)
        user_actions[:] = [action_time for action_time in user_actions if action_time > cutoff]
        
        # Проверяем лимиты
        if action == "message":
            limit = self.config.rate_limit_messages_per_minute
        elif action == "command":
            limit = self.config.rate_limit_commands_per_hour
        else:
            return True
        
        if len(user_actions) >= limit:
            return False
        
        user_actions.append(now)
        return True
    
    async def start(self):
        """Асинхронный запуск бота"""
        if not self.application:
            raise RuntimeError("Bot not initialized")
        
        self.logger.info("Starting Telegram bot...")
        
        # Устанавливаем команды бота
        commands = []
        for cmd_name, cmd_config in self.config.commands.items():
            if cmd_config.get("enabled", True):
                commands.append(BotCommand(cmd_name, cmd_config["description"]))
        
        await self.application.bot.set_my_commands(commands)
        self.logger.info(f"Bot commands set: {[cmd.command for cmd in commands]}")
        
        # Сбрасываем возможный webhook перед polling, чтобы избежать 409 Conflict
        try:
            await self.application.bot.delete_webhook(drop_pending_updates=True)
            self.logger.info("Webhook deleted (drop_pending_updates=True)")
        except Exception as e:
            self.logger.warning(f"Failed to delete webhook before polling: {e}")
        
        # Запускаем polling напрямую через updater без управления event loop
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        
        try:
            # Держим бота активным
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            self.logger.info("Bot polling interrupted")
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
    
    def run(self):
        """Синхронный запуск бота"""
        try:
            # Проверяем, есть ли уже запущенный event loop
            try:
                loop = asyncio.get_running_loop()
                # Если есть, создаем задачу в существующем loop
                task = loop.create_task(self.start())
                loop.run_until_complete(task)
            except RuntimeError:
                # Если нет запущенного loop, создаем новый
                asyncio.run(self.start())
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Bot crashed: {e}")
            raise


def main():
    """Точка входа для запуска бота"""
    try:
        print("🤖 Запуск Telegram бота Agata...")
        
        # Проверяем переменные окружения
        if not os.getenv('TELEGRAM_BOT_TOKEN'):
            print("❌ Ошибка: Переменная окружения TELEGRAM_BOT_TOKEN не установлена")
            print("💡 Установите её командой:")
            print("   export TELEGRAM_BOT_TOKEN='8181686852:AAH93K4NhfI2oUhhrvLd9MK8Eln1_XsyFi4'")
            return
        
        bot = ProductionTelegramBot()
        bot.run()
        
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()