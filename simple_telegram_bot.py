
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
        logging.FileHandler('simple_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleTelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлена")
        
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.application = Application.builder().token(self.token).build()
        
        # Добавляем обработчики
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("Simple Telegram bot initialized")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        welcome_msg = f"""🤖 Привет! Я Agatha.
        
Просто напиши мне сообщение, и я отвечу.
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
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/chat",
                    json={
                        "user_id": str(user_id),
                        "messages": [{"role": "user", "content": message_text}]
                    }
                )
            
            if response.status_code == 200:
                chat_response = response.json()
                response_text = chat_response.get("response", "Нет ответа")
                await update.message.reply_text(response_text)
                logger.info(f"Sent response to {user_id}: {response_text[:50]}...")
            else:
                await update.message.reply_text("😔 Извини, что-то пошло не так. Попробуй еще раз.")
                logger.error(f"API error: {response.status_code}")
                
        except Exception as e:
            await update.message.reply_text("😔 Извини, что-то пошло не так. Попробуй еще раз.")
            logger.error(f"Error handling message: {e}")
    
    async def start_bot(self):
        """Запуск бота"""
        logger.info("Starting simple bot...")
        
        # Устанавливаем команды
        commands = [BotCommand("start", "Начать общение")]
        await self.application.bot.set_my_commands(commands)
        
        # Удаляем webhook
        try:
            await self.application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted")
        except Exception as e:
            logger.warning(f"Failed to delete webhook: {e}")
        
        # Инициализируем приложение
        await self.application.initialize()
        await self.application.start()
        
        # Запускаем polling
        await self.application.updater.start_polling(drop_pending_updates=True)
        logger.info("Bot is polling...")
        
        try:
            # Держим бота активным
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot interrupted by user")
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Bot stopped")

def main():
    """Точка входа"""
    try:
        print("🤖 Запуск простого Telegram бота...")
        
        if not os.getenv('TELEGRAM_BOT_TOKEN'):
            print("❌ TELEGRAM_BOT_TOKEN не установлена")
            return
        
        bot = SimpleTelegramBot()
        asyncio.run(bot.start_bot())
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
