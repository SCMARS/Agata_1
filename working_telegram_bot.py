#!/usr/bin/env python3
"""
Рабочий Telegram бот для Agatha - проверенная версия
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('working_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WorkingTelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлена")
        
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.application = None
        self.running = False
        
        logger.info("Working Telegram bot initialized")
    
    def setup_handlers(self):
        """Настраивает обработчики команд"""
        self.application = Application.builder().token(self.token).build()
        
        # Добавляем обработчики
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("Handlers configured")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        welcome_msg = f"""🤖 Привет! Я Agatha.
        
Просто напиши мне сообщение, и я отвечу с вопросами из стейджев.
Твой ID: {user_id}"""
        await update.message.reply_text(welcome_msg)
        logger.info(f"Start command from user {user_id}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик обычных сообщений"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        logger.info(f"Message from {user_id}: {message_text}")
        
        try:
            # Отправляем в API
            timeout = httpx.Timeout(60.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Sending to API: {self.api_base_url}/api/chat")
                response = await client.post(
                    f"{self.api_base_url}/api/chat",
                    json={
                        "user_id": str(user_id),
                        "messages": [{"role": "user", "content": message_text}]
                    }
                )
                logger.info(f"API responded with status: {response.status_code}")
            
            if response.status_code == 200:
                chat_response = response.json()
                response_text = chat_response.get("response", "Нет ответа от нейросети")
                
                if response_text and response_text.strip():
                    await update.message.reply_text(response_text)
                    logger.info(f"Sent response to {user_id}: {response_text[:100]}...")
                else:
                    await update.message.reply_text("🤔 Получил пустой ответ. Попробуй еще раз.")
                    logger.warning(f"Empty response from API for user {user_id}")
            else:
                error_text = f"API error: {response.status_code}"
                logger.error(error_text)
                await update.message.reply_text("😔 Извини, проблема с API. Попробуй еще раз.")
                
        except httpx.TimeoutException:
            logger.error(f"API timeout for user {user_id}")
            await update.message.reply_text("⏰ Тайм-аут API. Попробуй еще раз.")
        except Exception as e:
            logger.error(f"Error handling message from {user_id}: {e}")
            await update.message.reply_text("😔 Извини, что-то пошло не так. Попробуй еще раз.")
    
    async def start_polling(self):
        """Запуск polling с проверками"""
        if self.running:
            logger.warning("Bot already running")
            return
        
        try:
            self.setup_handlers()
            
            logger.info("Setting up bot commands...")
            commands = [BotCommand("start", "Начать общение")]
            await self.application.bot.set_my_commands(commands)
            
            # Удаляем webhook с максимальным ожиданием
            logger.info("Deleting webhook...")
            await self.application.bot.delete_webhook(drop_pending_updates=True)
            
            # Даем время на очистку предыдущих соединений
            await asyncio.sleep(3)
            
            # Инициализируем приложение
            logger.info("Initializing application...")
            await self.application.initialize()
            await self.application.start()
            
            # Запускаем polling с retry
            logger.info("Starting polling...")
            self.running = True
            
            await self.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
            logger.info("✅ Bot is successfully polling!")
            
            # Основной цикл
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in polling: {e}")
            self.running = False
            raise
        finally:
            logger.info("Shutting down bot...")
            if self.application:
                try:
                    await self.application.updater.stop()
                    await self.application.stop()
                    await self.application.shutdown()
                except:
                    pass
            self.running = False
    
    def stop(self):
        """Остановка бота"""
        self.running = False

async def main():
    """Основная функция"""
    print("🤖 Запуск рабочего Telegram бота...")
    
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        print("❌ TELEGRAM_BOT_TOKEN не установлена")
        return
    
    bot = WorkingTelegramBot()
    
    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
        bot.stop()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
