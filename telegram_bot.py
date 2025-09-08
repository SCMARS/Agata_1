#!/usr/bin/env python3

import os
import sys
import logging
import asyncio
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# Добавляем путь к проекту
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Telegram Bot API
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, 
        CallbackQueryHandler, filters, ContextTypes
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ python-telegram-bot не установлен. Установите: pip install python-telegram-bot")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8181686852:AAH93K4NhfI2oUhhrvLd9MK8Eln1_XsyFi4")
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = os.getenv("API_PORT", "8000")
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"
BOT_NAME = os.getenv("BOT_NAME", "Agatha Memory Bot")

class AgathaMemoryBot:
    """
    Telegram Bot для тестирования системы памяти Agatha
    """
    
    def __init__(self):
        self.api_base_url = API_BASE_URL
        self.user_sessions = {}  # user_id -> session_data
        
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot не установлен")
        
        # Создаем bot application
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Регистрируем handlers
        self._setup_handlers()
        
        logger.info(f"🤖 {BOT_NAME} инициализирован")
    
    def _setup_handlers(self):
        """Настраивает обработчики команд и сообщений"""
        
        # Команды
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("memory", self._memory_command))
        self.application.add_handler(CommandHandler("search", self._search_command))
        self.application.add_handler(CommandHandler("overview", self._overview_command))
        self.application.add_handler(CommandHandler("clear", self._clear_command))
        self.application.add_handler(CommandHandler("test", self._test_command))
        
        # Обработка сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        # Callback queries для inline кнопок
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
        
        logger.info("✅ Handlers настроены")
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        user_id = str(user.id)
        
        welcome_text = f"""
🤖 **Добро пожаловать в {BOT_NAME}!**

Я - бот для тестирования системы памяти Agatha с LangChain и LangGraph.

**Доступные команды:**
• `/start` - Начать работу
• `/help` - Справка по командам  
• `/memory` - Добавить сообщение в память
• `/search <запрос>` - Поиск в памяти
• `/overview` - Обзор памяти
• `/clear` - Очистить память
• `/test` - Тест системы памяти

**Как использовать:**
1. Просто напишите сообщение - оно будет добавлено в память
2. Используйте команды для управления памятью
3. Тестируйте поиск и контекст

Ваш ID: `{user_id}`
        """.strip()
        
        # Создаем inline кнопки
        keyboard = [
            [
                InlineKeyboardButton("📝 Добавить в память", callback_data="add_memory"),
                InlineKeyboardButton("🔍 Поиск", callback_data="search_memory")
            ],
            [
                InlineKeyboardButton("📊 Обзор", callback_data="memory_overview"),
                InlineKeyboardButton("🧹 Очистить", callback_data="clear_memory")
            ],
            [
                InlineKeyboardButton("🧪 Тест", callback_data="test_memory")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Инициализируем сессию пользователя
        self.user_sessions[user_id] = {
            'created_at': datetime.now(),
            'messages_count': 0,
            'last_activity': datetime.now()
        }
        
        logger.info(f"👤 Новый пользователь: {user_id}")
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📚 **Справка по командам**

**Основные команды:**
• `/start` - Начать работу с ботом
• `/help` - Показать эту справку

**Работа с памятью:**
• `/memory <текст>` - Добавить сообщение в память
• `/search <запрос>` - Поиск в памяти пользователя
• `/overview` - Получить обзор памяти
• `/clear` - Очистить всю память пользователя

**Тестирование:**
• `/test` - Запустить тест системы памяти

**Примеры использования:**
• `/memory Привет! Меня зовут Александр`
• `/search Python разработчик`
• `/overview`

**Как работает память:**
1. **Short-term**: Последние сообщения (буфер)
2. **Long-term**: Векторная БД с embeddings
3. **Episodic**: Завершенные диалоги
4. **Summary**: Автоматические резюме

**Технологии:**
• LangChain + ChromaDB
• OpenAI Embeddings
• 4-уровневая архитектура памяти
        """.strip()
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def _memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /memory"""
        user_id = str(update.effective_user.id)
        
        if not context.args:
            await update.message.reply_text(
                "📝 **Использование:** `/memory <текст сообщения>`\n\n"
                "Пример: `/memory Привет! Меня зовут Александр и я Python разработчик`"
            )
            return
        
        # Собираем текст сообщения
        content = " ".join(context.args)
        
        # Добавляем в память через API
        try:
            memory_data = {
                'role': 'user',
                'content': content,
                'metadata': {
                    'source': 'telegram',
                    'user_id': user_id,
                    'timestamp': datetime.now().isoformat()
                },
                'conversation_id': f'tg_{user_id}_{int(datetime.now().timestamp())}',
                'day_number': 1
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/memory/{user_id}/add",
                json=memory_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                memory_result = result.get('result', {})
                
                status_text = f"""
✅ **Сообщение добавлено в память!**

📝 **Текст:** {content[:100]}{'...' if len(content) > 100 else ''}

💾 **Результат:**
• Short-term: {'✅' if memory_result.get('short_term') else '❌'}
• Long-term: {'✅' if memory_result.get('long_term') else '❌'}

🆔 **User ID:** `{user_id}`
                """.strip()
                
                await update.message.reply_text(status_text, parse_mode='Markdown')
                
                # Обновляем статистику сессии
                if user_id in self.user_sessions:
                    self.user_sessions[user_id]['messages_count'] += 1
                    self.user_sessions[user_id]['last_activity'] = datetime.now()
                
            else:
                await update.message.reply_text(
                    f"❌ **Ошибка добавления в память:**\n"
                    f"Status: {response.status_code}\n"
                    f"Response: {response.text}"
                )
                
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Ошибка:** {str(e)}\n\n"
                f"Проверьте, что API сервер запущен на {self.api_base_url}"
            )
            logger.error(f"Ошибка добавления в память: {e}")
    
    async def _search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /search"""
        user_id = str(update.effective_user.id)
        
        if not context.args:
            await update.message.reply_text(
                "🔍 **Использование:** `/search <запрос>`\n\n"
                "Пример: `/search Python разработчик`"
            )
            return
        
        query = " ".join(context.args)
        
        try:
            search_data = {
                'query': query,
                'max_results': 5,
                'levels': ['short_term', 'long_term']
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/memory/{user_id}/search",
                json=search_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                results = result.get('results', [])
                total_found = result.get('total_found', 0)
                
                if total_found > 0:
                    search_text = f"""
🔍 **Результаты поиска по запросу:** `{query}`

📊 **Найдено результатов:** {total_found}

                    """.strip()
                    
                    for i, item in enumerate(results[:3]):  # Показываем первые 3
                        content = item.get('content', '')[:80]
                        level = item.get('source_level', 'unknown')
                        score = item.get('relevance_score', 0)
                        
                        search_text += f"""
**{i+1}. {content}...**
• Уровень: {level}
• Релевантность: {score:.2f}
                        """.strip()
                    
                    if total_found > 3:
                        search_text += f"\n\n... и еще {total_found - 3} результатов"
                    
                    await update.message.reply_text(search_text, parse_mode='Markdown')
                    
                else:
                    await update.message.reply_text(
                        f"🔍 **Поиск по запросу:** `{query}`\n\n"
                        f"❌ **Результаты не найдены**\n\n"
                        f"Попробуйте другой запрос или добавьте больше сообщений в память."
                    )
                    
            else:
                await update.message.reply_text(
                    f"❌ **Ошибка поиска:**\n"
                    f"Status: {response.status_code}\n"
                    f"Response: {response.text}"
                )
                
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Ошибка поиска:** {str(e)}\n\n"
                f"Проверьте, что API сервер запущен на {self.api_base_url}"
            )
            logger.error(f"Ошибка поиска: {e}")
    
    async def _overview_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /overview"""
        user_id = str(update.effective_user.id)
        
        try:
            response = requests.get(
                f"{self.api_base_url}/api/memory/{user_id}/overview",
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                overview = result.get('overview', {})
                
                overview_text = f"""
📊 **Обзор памяти пользователя**

🆔 **User ID:** `{user_id}`

📈 **Статистика:**
• Short-term: {overview.get('short_term_stats', {}).get('messages_count', 0)} сообщений
• Long-term: {overview.get('long_term_stats', {}).get('documents_count', 0)} документов
• Обработка: {overview.get('processing_stats', {}).get('total_operations', 0)} операций

⏰ **Сессия бота:**
• Сообщений: {self.user_sessions.get(user_id, {}).get('messages_count', 0)}
• Последняя активность: {self.user_sessions.get(user_id, {}).get('last_activity', 'неизвестно')}
                """.strip()
                
                await update.message.reply_text(overview_text, parse_mode='Markdown')
                
            else:
                await update.message.reply_text(
                    f"❌ **Ошибка получения обзора:**\n"
                    f"Status: {response.status_code}\n"
                    f"Response: {response.text}"
                )
                
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Ошибка:** {str(e)}\n\n"
                f"Проверьте, что API сервер запущен на {self.api_base_url}"
            )
            logger.error(f"Ошибка получения обзора: {e}")
    
    async def _clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /clear"""
        user_id = str(update.effective_user.id)
        
        try:
            response = requests.post(
                f"{self.api_base_url}/api/memory/{user_id}/clear",
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                clear_text = f"""
🧹 **Память очищена!**

✅ **Результат:** {result.get('message', 'Успешно')}
🆔 **User ID:** `{user_id}`

💡 **Что произошло:**
• Short-term память очищена
• Long-term память очищена
• Все сообщения удалены

📝 **Теперь можете начать заново!**
                """.strip()
                
                await update.message.reply_text(clear_text, parse_mode='Markdown')
                
                # Сбрасываем статистику сессии
                if user_id in self.user_sessions:
                    self.user_sessions[user_id]['messages_count'] = 0
                    self.user_sessions[user_id]['last_activity'] = datetime.now()
                
            else:
                await update.message.reply_text(
                    f"❌ **Ошибка очистки памяти:**\n"
                    f"Status: {response.status_code}\n"
                    f"Response: {response.text}"
                )
                
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Ошибка:** {str(e)}\n\n"
                f"Проверьте, что API сервер запущен на {self.api_base_url}"
            )
            logger.error(f"Ошибка очистки памяти: {e}")
    
    async def _test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /test - тест системы памяти"""
        user_id = str(update.effective_user.id)
        
        test_text = f"""
🧪 **Тест системы памяти Agatha**

🆔 **User ID:** `{user_id}`

📝 **Этап 1: Добавление тестовых сообщений**
Добавляю сообщения в память...
        """.strip()
        
        message = await update.message.reply_text(test_text, parse_mode='Markdown')
        
        try:
            # Тестовые сообщения
            test_messages = [
                {
                    'role': 'user',
                    'content': 'Привет! Меня зовут Александр Петров и я senior Python разработчик с 15 лет опыта в машинном обучении',
                    'metadata': {'test': True, 'importance': 'high'}
                },
                {
                    'role': 'assistant', 
                    'content': 'Привет, Александр! Очень приятно познакомиться с таким опытным специалистом!',
                    'metadata': {'test': True, 'importance': 'normal'}
                },
                {
                    'role': 'user',
                    'content': 'Работаю в крупной IT компании над проектами искусственного интеллекта. Специализируюсь на deep learning и computer vision',
                    'metadata': {'test': True, 'importance': 'high'}
                }
            ]
            
            # Добавляем сообщения
            added_count = 0
            for msg_data in test_messages:
                memory_data = {
                    **msg_data,
                    'conversation_id': f'test_{user_id}_{int(datetime.now().timestamp())}',
                    'day_number': 1
                }
                
                response = requests.post(
                    f"{self.api_base_url}/api/memory/{user_id}/add",
                    json=memory_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    added_count += 1
            
            # Обновляем сообщение
            test_text += f"""
✅ **Добавлено:** {added_count}/{len(test_messages)} сообщений

🔍 **Этап 2: Тест поиска**
Ищу по запросу "Python разработчик машинное обучение"...
            """.strip()
            
            await message.edit_text(test_text, parse_mode='Markdown')
            
            # Тест поиска
            search_data = {
                'query': 'Python разработчик машинное обучение',
                'max_results': 3,
                'levels': ['short_term', 'long_term']
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/memory/{user_id}/search",
                json=search_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                found_count = result.get('total_found', 0)
                
                test_text += f"""
✅ **Найдено результатов:** {found_count}

📊 **Этап 3: Обзор памяти**
Получаю статистику...
                """.strip()
                
                await message.edit_text(test_text, parse_mode='Markdown')
                
                # Получаем обзор
                response = requests.get(
                    f"{self.api_base_url}/api/memory/{user_id}/overview",
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    overview = result.get('overview', {})
                    
                    test_text += f"""
✅ **Обзор получен!**

🎉 **ТЕСТ ЗАВЕРШЕН УСПЕШНО!**

📈 **Результаты:**
• Сообщений добавлено: {added_count}
• Поиск работает: {'✅' if found_count > 0 else '❌'}
• Обзор доступен: ✅

🚀 **Система памяти Agatha работает корректно!**
                    """.strip()
                    
                else:
                    test_text += f"""
❌ **Ошибка получения обзора:** {response.status_code}

⚠️ **Частичный тест завершен**
                    """.strip()
                    
            else:
                test_text += f"""
❌ **Ошибка поиска:** {response.status_code}

⚠️ **Тест не завершен полностью**
                """.strip()
            
            await message.edit_text(test_text, parse_mode='Markdown')
            
        except Exception as e:
            test_text += f"""
❌ **Ошибка тестирования:** {str(e)}

⚠️ **Тест не завершен**
            """.strip()
            
            await message.edit_text(test_text, parse_mode='Markdown')
            logger.error(f"Ошибка тестирования: {e}")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик обычных сообщений - добавляет в память"""
        user_id = str(update.effective_user.id)
        content = update.message.text
        
        # Пропускаем команды
        if content.startswith('/'):
            return
        
        # Добавляем в память
        try:
            memory_data = {
                'role': 'user',
                'content': content,
                'metadata': {
                    'source': 'telegram',
                    'user_id': user_id,
                    'timestamp': datetime.now().isoformat(),
                    'auto_added': True
                },
                'conversation_id': f'tg_{user_id}_{int(datetime.now().timestamp())}',
                'day_number': 1
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/memory/{user_id}/add",
                json=memory_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                memory_result = result.get('result', {})
                
                # Отправляем подтверждение
                confirm_text = f"""
✅ **Сообщение добавлено в память!**

💾 **Статус:**
• Short-term: {'✅' if memory_result.get('short_term') else '❌'}
• Long-term: {'✅' if memory_result.get('long_term') else '❌'}

💡 **Используйте команды для работы с памятью:**
• `/search <запрос>` - поиск
• `/overview` - обзор
• `/help` - справка
                """.strip()
                
                # Получаем ответ от нейросети через /api/chat
                try:
                    chat_data = {
                        'user_id': user_id,
                        'messages': [{'role': 'user', 'content': content}],
                        'metaTime': "2025-09-02T14:07:00Z"
                    }
                    
                    logger.info(f"🔄 Отправляем запрос к chat API для пользователя {user_id}")
                    
                    chat_response = requests.post(
                        f"{self.api_base_url}/api/chat",
                        json=chat_data,
                        timeout=30  # Увеличиваем timeout для стабильности
                    )
                    
                    logger.info(f"📡 Chat API ответил: {chat_response.status_code}")
                    
                    if chat_response.status_code == 200:
                        chat_result = chat_response.json()
                        # API возвращает parts (массив частей ответа)
                        parts = chat_result.get('parts', [])
                        logger.info(f"🧠 Получены части ответа: {len(parts) if parts else 0}")
                        
                        if parts:
                            ai_response = ' '.join(parts)
                            logger.info(f"✅ Отправляем ответ от AI: {ai_response[:50]}...")
                            # Отправляем только ответ от нейросети
                            await update.message.reply_text(ai_response)
                            return  # Важно! Выходим, чтобы не показывать подтверждение
                        else:
                            logger.warning("⚠️ Нет частей в ответе от API")
                            # Если нет частей, показываем подтверждение
                            await update.message.reply_text(confirm_text, parse_mode='Markdown')
                        
                    else:
                        logger.warning(f"❌ Chat API вернул ошибку: {chat_response.status_code} - {chat_response.text}")
                        # Если LLM не работает, показываем подтверждение
                        await update.message.reply_text(confirm_text, parse_mode='Markdown')
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ Ошибка подключения к chat API: {e}")
                    # Если LLM не работает, показываем подтверждение  
                    await update.message.reply_text(confirm_text, parse_mode='Markdown')
                
                # Обновляем статистику сессии
                if user_id in self.user_sessions:
                    self.user_sessions[user_id]['messages_count'] += 1
                    self.user_sessions[user_id]['last_activity'] = datetime.now()
                
            else:
                await update.message.reply_text(
                    f"❌ **Ошибка добавления в память:** {response.status_code}"
                )
                
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Ошибка:** {str(e)}\n\n"
                f"Проверьте, что API сервер запущен на {self.api_base_url}"
            )
            logger.error(f"Ошибка обработки сообщения: {e}")
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback queries от inline кнопок"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        
        if query.data == "add_memory":
            await query.edit_message_text(
                "📝 **Добавление в память:**\n\n"
                "Просто напишите сообщение, и оно будет автоматически добавлено в память!\n\n"
                "Или используйте команду:\n"
                "`/memory <текст сообщения>`"
            )
            
        elif query.data == "search_memory":
            await query.edit_message_text(
                "🔍 **Поиск в памяти:**\n\n"
                "Используйте команду:\n"
                "`/search <запрос>`\n\n"
                "Примеры:\n"
                "• `/search Python разработчик`\n"
                "• `/search машинное обучение`\n"
                "• `/search Александр`"
            )
            
        elif query.data == "memory_overview":
            await query.edit_message_text(
                "📊 **Обзор памяти:**\n\n"
                "Используйте команду:\n"
                "`/overview`\n\n"
                "Покажет статистику вашей памяти:\n"
                "• Количество сообщений\n"
                "• Документы в long-term\n"
                "• Активность сессии"
            )
            
        elif query.data == "clear_memory":
            await query.edit_message_text(
                "🧹 **Очистка памяти:**\n\n"
                "⚠️ **Внимание!** Это действие необратимо!\n\n"
                "Используйте команду:\n"
                "`/clear`\n\n"
                "Удалит все сообщения из памяти."
            )
            
        elif query.data == "test_memory":
            await query.edit_message_text(
                "🧪 **Тест системы памяти:**\n\n"
                "Используйте команду:\n"
                "`/test`\n\n"
                "Автоматически протестирует:\n"
                "• Добавление сообщений\n"
                "• Поиск в памяти\n"
                "• Получение обзора"
            )
    
    def run(self):
        """Запускает бота"""
        logger.info(f"🚀 Запуск {BOT_NAME}...")
        
        try:
            # Проверяем доступность API
            response = requests.get(f"{self.api_base_url}/healthz", timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ API сервер доступен на {self.api_base_url}")
            else:
                logger.warning(f"⚠️ API сервер недоступен: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ API сервер недоступен: {e}")
            logger.warning("⚠️ Убедитесь, что API сервер запущен на http://localhost:8000")
        
        # Запускаем бота
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )


def main():
    """Главная функция"""
    print(f"🤖 Запуск {BOT_NAME}")
    print(f"🔑 Token: {TELEGRAM_TOKEN[:20]}...")
    print(f"🌐 API: {API_BASE_URL}")
    print("=" * 50)
    
    try:
        bot = AgathaMemoryBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
