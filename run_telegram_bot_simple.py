#!/usr/bin/env python3
"""
Простой запуск Telegram бота без ProductionConfigManager
"""
import os
import asyncio
import logging
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from collections import defaultdict
import traceback

try:
    import telegram
    from telegram import Update, BotCommand
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ python-telegram-bot not installed. Install with: pip install python-telegram-bot")


@dataclass
class SimpleBotConfig:
    """Простая конфигурация бота"""
    token: str
    timeout: int = 30
    max_message_length: int = 4096
    rate_limit_messages_per_minute: int = 20
    commands: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    messages: Dict[str, str] = field(default_factory=dict)


class SimpleTelegramBot:
    """Простой Telegram Bot без сложных зависимостей"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = None
        self.application = None
        self.rate_limiter = defaultdict(list)
        self.api_base_url = "http://localhost:8000"
        
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
            
            self.config = SimpleBotConfig(
                token=token,
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
            
            self.logger.info("Bot config loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load bot config: {e}")
            raise
    
    def _setup_logging(self):
        """Настраивает логирование"""
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(name)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('simple_telegram_bot.log'),
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
            async with httpx.AsyncClient() as client:
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
            async with httpx.AsyncClient() as client:
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
            async with httpx.AsyncClient() as client:
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
            async with httpx.AsyncClient() as client:
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
            async with httpx.AsyncClient() as client:
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
        """Обработчик обычных сообщений"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Проверяем rate limiting
        if not self._check_rate_limit(user_id, "message"):
            await update.message.reply_text("⏰ Слишком много сообщений. Подождите немного.")
            return
        
        # Отправляем сообщение в чат API
        try:
            self.logger.info(f"🔄 Отправляем запрос к chat API для пользователя {user_id}")
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = None
                for attempt in range(3):
                    try:
                        response = await client.post(
                            f"{self.api_base_url}/api/chat",
                            json={
                                "user_id": str(user_id),
                                "messages": [{"role": "user", "content": message_text}]
                            }
                        )
                        break
                    except httpx.ReadTimeout:
                        if attempt == 2:
                            raise
                        await asyncio.sleep(1 + attempt)
            
            self.logger.info(f"📡 Chat API ответил: {response.status_code}")
            
            if response.status_code == 200:
                chat_response = response.json()
                parts = chat_response.get("parts", [])
                self.logger.info(f"🧠 Получены части ответа: {len(parts)}")
                
                # Отправляем ответ частями
                for i, part in enumerate(parts):
                    if i == 0:
                        await update.message.reply_text(part)
                        self.logger.info(f"✅ Отправляем ответ от AI: {part[:50]}...")
                    else:
                        await update.message.reply_text(part)
                    
                    # Небольшая задержка между частями
                    if i < len(parts) - 1:
                        await asyncio.sleep(0.5)
            else:
                await update.message.reply_text(
                    self.config.messages["error_generic"].format(error=f"HTTP {response.status_code}")
                )
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки сообщения: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            await update.message.reply_text(
                self.config.messages["error_generic"].format(error=str(e))
            )
    
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
        
        # Запускаем polling, не закрывая event loop (во избежание ошибок)
        await self.application.run_polling(drop_pending_updates=True, close_loop=False)
    
    def run(self):
        """Синхронный запуск бота"""
        try:
            import nest_asyncio
            nest_asyncio.apply()
            try:
                loop = asyncio.get_running_loop()
                loop.run_until_complete(self.start())
            except RuntimeError:
                asyncio.run(self.start())
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Bot crashed: {e}")
            raise


def main():
    """Точка входа для запуска бота"""
    try:
        print("🤖 Запуск простого Telegram бота Agata...")
        
        # Проверяем переменные окружения
        if not os.getenv('TELEGRAM_BOT_TOKEN'):
            print("❌ Ошибка: Переменная окружения TELEGRAM_BOT_TOKEN не установлена")
            print("💡 Установите её командой:")
            print("   export TELEGRAM_BOT_TOKEN='8181686852:AAH93K4NhfI2oUhhrvLd9MK8Eln1_XsyFi4'")
            return
        
        # Применяем nest_asyncio в самом начале
        import nest_asyncio
        nest_asyncio.apply()
        
        bot = SimpleTelegramBot()
        bot.run()
        
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
