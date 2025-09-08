
import os
import json

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .base import MemoryAdapter, Message, MemoryContext

# Quiet mode setting
QUIET_MODE = os.getenv('AGATHA_QUIET', 'false').lower() == 'true'

def log_info(message: str):
    """Условное логирование - только если не quiet mode"""
    if not QUIET_MODE:
        print(message)
from ..config.settings import settings

class VectorMemory(MemoryAdapter):
    """
    Векторная память с настоящей БД (pgvector) для семантического поиска
    """
    
    def __init__(self, user_id: str, max_memories: int = 1000):
        self.user_id = user_id
        self.max_memories = max_memories
        self.db_pool = None
        self.connection_error = False
        # Добавляем недостающий атрибут memories для совместимости
        self.memories = []
        
    def _get_db_pool(self):
        """Получить пул соединений с БД (устаревший метод)"""
        print("⚠️ _get_db_pool устарел, используйте _get_db_conn")
        return None

    def _get_db_conn(self):
        """Получить соединение с БД PostgreSQL"""
        try:
            if self.connection_error:
                print("⚠️ Соединение с БД ранее не удалось, пропускаем")
                return None

            conn = psycopg2.connect(
                host=settings.DATABASE_HOST,
                port=settings.DATABASE_PORT,
                user=settings.DATABASE_USER,
                password=settings.DATABASE_PASSWORD,
                database=settings.DATABASE_NAME
            )
            conn.autocommit = False
            return conn

        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            print(f"📍 Попытка подключения к: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}")
            self.connection_error = True
            return None
    
    def _ensure_tables(self):
        """Создать таблицы если их нет"""
        # Кэшируем результат - не создаем таблицы повторно
        if hasattr(self, '_tables_created') and self._tables_created:
            return True
            
        conn = self._get_db_conn()
        if not conn:
            print("⚠️ БД недоступна, пропускаем создание таблиц")
            return False
            
        try:
            with conn.cursor() as cursor:
                # Создаем таблицу для векторных воспоминаний
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS vector_memories (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        content TEXT NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                        day_number INTEGER NOT NULL,
                        importance_score FLOAT NOT NULL,
                        topics JSONB,
                        emotions JSONB,
                        metadata JSONB,
                        embedding VECTOR(1536),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """)
                
                # Создаем индексы для быстрого поиска
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_vector_memories_user_id ON vector_memories(user_id);
                    CREATE INDEX IF NOT EXISTS idx_vector_memories_timestamp ON vector_memories(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_vector_memories_importance ON vector_memories(importance_score);
                """)
                
                # Создаем векторный индекс для семантического поиска
                try:
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
                        ON vector_memories 
                        USING ivfflat (embedding vector_cosine_ops) 
                        WITH (lists = 100);
                    """)
                except Exception as e:
                    print(f"⚠️ Векторный индекс не создан (возможно pgvector не установлен): {e}")
                
                conn.commit()
                print("✅ Таблицы и индексы созданы/проверены")
                self._tables_created = True  # Кэшируем результат
                return True
                
        except Exception as e:
            print(f"❌ Ошибка создания таблиц: {e}")
            return False
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Генерируем векторное представление текста"""
        try:
            # Используем OpenAI embeddings для настоящего семантического понимания
            import openai
            if not settings.OPENAI_API_KEY:
                print("❌ OpenAI API ключ не найден!")
                print("💡 Добавьте OPENAI_API_KEY в config.env файл")
                raise Exception("OpenAI API key required")
                
            print(f"🔑 Используем OpenAI API ключ: {settings.OPENAI_API_KEY[:20]}...")
            
            # НОВЫЙ API для OpenAI 1.0.0+
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            
            embedding = response.data[0].embedding
            print(f"✅ Настоящий эмбеддинг создан: {len(embedding)} элементов")
            return embedding
            
        except Exception as e:
            print(f"❌ Критическая ошибка генерации эмбеддинга: {e}")
            print("💡 Система не может работать без OpenAI API")
            raise Exception(f"Embedding generation failed: {e}")
    
    def add_message(self, message: Message, context: MemoryContext) -> None:
        """Добавить сообщение в векторную БД"""
        try:
            # Проверяем доступность БД только один раз
            if not hasattr(self, '_db_available'):
                self._db_available = self._ensure_tables()
            
            if not self._db_available:
                print("⚠️ БД недоступна, сообщение не сохранено")
                return
            
            # Анализируем важность
            is_important = self._is_important_message(message, context)
            print(f"🧠 VectorMemory: Сообщение '{message.content[:50]}...' важное: {is_important}")
            
            if is_important:
                importance_score = self._calculate_importance(message, context)
                topics = self._extract_topics(message.content)
                emotions = self._detect_emotions(message.content)
                
                # Генерируем эмбеддинг
                embedding = self._generate_embedding(message.content)
                
                # Сохраняем в БД
                conn = self._get_db_conn()
                if conn:
                    with conn.cursor() as cursor:
                        # Преобразуем эмбеддинг в формат для PostgreSQL
                        embedding_str = f"[{','.join(map(str, embedding))}]"
                        
                        cursor.execute("""
                            INSERT INTO vector_memories 
                            (user_id, content, role, timestamp, day_number, importance_score, 
                             topics, emotions, metadata, embedding)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                        """, 
                        (self.user_id, message.content, message.role, 
                         message.timestamp, context.day_number, importance_score,
                         json.dumps(topics), json.dumps(emotions),
                         json.dumps({
                             'message_length': len(message.content),
                             'has_question': '?' in message.content,
                             'day_context': context.day_number
                         }),
                         embedding_str)
                        )
                    
                    conn.commit()
                    print(f"🧠 VectorMemory: Сохранено в БД (важность: {importance_score:.2f})")
                    
                    # Очищаем старые записи если превышен лимит
                    self._cleanup_old_memories()
                else:
                    print("⚠️ БД недоступна, сообщение не сохранено")
            else:
                print(f"🧠 VectorMemory: Сообщение не важное, не сохраняем")
                
        except Exception as e:
            print(f"❌ Ошибка сохранения в VectorMemory: {e}")
    
    def _cleanup_old_memories(self):
        """Очищаем старые записи если превышен лимит"""
        try:
            conn = self._get_db_conn()
            if not conn:
                return
                
            with conn.cursor() as cursor:
                # Получаем количество записей для пользователя
                cursor.execute(
                    "SELECT COUNT(*) FROM vector_memories WHERE user_id = %s",
                    (self.user_id,)
                )
                count = cursor.fetchone()[0]
                
                if count > self.max_memories:
                    # Удаляем наименее важные записи
                    cursor.execute("""
                        DELETE FROM vector_memories 
                        WHERE user_id = %s 
                        AND id NOT IN (
                            SELECT id FROM vector_memories 
                            WHERE user_id = %s 
                            ORDER BY importance_score DESC 
                            LIMIT %s
                        )
                    """, (self.user_id, self.user_id, self.max_memories))
                    
                    conn.commit()
                    print(f"🧠 VectorMemory: Очищено {count - self.max_memories} старых записей")
                    
        except Exception as e:
            print(f"⚠️ Ошибка очистки памяти: {e}")
    
    def get_context(self, context: MemoryContext, query: str = "") -> str:
        """Получить контекст из векторной БД с семантическим поиском"""
        try:
            # Проверяем доступность БД только один раз
            if not hasattr(self, '_db_available'):
                self._db_available = self._ensure_tables()
            
            if not self._db_available:
                return "БД недоступна, используем базовый контекст."
            
            conn = self._get_db_conn()
            if not conn:
                return "БД недоступна, используем базовый контекст."
            
            with conn.cursor() as cursor:
                # Получаем общее количество сообщений
                cursor.execute(
                    "SELECT COUNT(*) FROM vector_memories WHERE user_id = %s",
                    (self.user_id,)
                )
                total_count = cursor.fetchone()[0]
                
                print(f"🧠 VectorMemory: Запрос контекста. Всего в БД: {total_count}")
                
                if total_count == 0:
                    return "Это наше первое общение."
                
                # Семантический поиск если есть запрос
                if query:
                    query_embedding = self._generate_embedding(query)
                    cursor.execute("""
                        SELECT content, importance_score, topics, emotions
                        FROM vector_memories
                        WHERE user_id = %s
                        ORDER BY embedding <=> %s, importance_score DESC
                        LIMIT 5
                    """, (self.user_id, query_embedding))
                    relevant_memories = cursor.fetchall()
                else:
                    # Берем самые важные воспоминания
                    cursor.execute("""
                        SELECT content, importance_score, topics, emotions
                        FROM vector_memories
                        WHERE user_id = %s
                        ORDER BY importance_score DESC
                        LIMIT 5
                    """, (self.user_id,))
                    relevant_memories = cursor.fetchall()
                
                if not relevant_memories:
                    return f"У нас уже было {total_count} важных разговоров."
                
                # Формируем умный контекст
                context_parts = [f"Мы общаемся уже {total_count} важных сообщений."]
                
                for memory in relevant_memories:
                    if memory[1] > 0.5:  # importance_score
                        content_preview = memory[0][:100] + "..." if len(memory[0]) > 100 else memory[0]  # content
                        context_parts.append(f"Помню: {content_preview}")
                
                print(f"🧠 Сформированный контекст: {' | '.join(context_parts)}")
                return " | ".join(context_parts)
                
        except Exception as e:
            print(f"❌ Ошибка получения контекста: {e}")
            return "У нас уже было несколько разговоров."
    
    def _search_memories(self, query: str, context: MemoryContext, limit: int = 5) -> List[Dict[str, Any]]:
        """Семантический поиск в векторной БД"""
        try:
            if not self._ensure_tables():
                return []
            
            if not query:
                return []
            
            query_embedding = self._generate_embedding(query)
            
            conn = self._get_db_conn()
            if not conn:
                return []
                
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Преобразуем эмбеддинг в формат для PostgreSQL
                query_embedding_str = f"[{','.join(map(str, query_embedding))}]"
                
                # Семантический поиск + релевантность по важности
                cursor.execute("""
                    SELECT 
                        content, role, timestamp, day_number, importance_score,
                        topics, emotions, metadata,
                        (embedding <=> %s::vector) as similarity_score
                    FROM vector_memories 
                    WHERE user_id = %s
                    ORDER BY (embedding <=> %s::vector) + (1 - importance_score)
                    LIMIT %s
                """, (query_embedding_str, self.user_id, query_embedding_str, limit))
                
                results = cursor.fetchall()
                memories = []
                for row in results:
                    memory = {
                        'content': row['content'],
                        'role': row['role'],
                        'timestamp': row['timestamp'],
                        'day_number': row['day_number'],
                        'importance_score': row['importance_score'],
                        'topics': row['topics'] or [],
                        'emotions': row['emotions'] or [],
                        'metadata': row['metadata'] or {},
                        'similarity_score': row['similarity_score']
                    }
                    memories.append(memory)
                
                return memories
                
        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            return []
    
    def _is_important_message(self, message: Message, context: MemoryContext) -> bool:
        
        content = message.content.lower()
        
        # Категории важности
        # ИСПРАВЛЕНО: Убираем хардкод маркеров - используем длину и структуру сообщения
        importance_score = 0
        
        # Базовая важность по длине и структуре
        if len(message.content) > 50:
            importance_score += 1
        
        # Проверяем наличие местоимений первого лица (указывает на личную информацию)
        if any(pronoun in content for pronoun in ['я ', 'мне ', 'мой ', 'моя ', 'мои ', 'меня ']):
            importance_score += 1
            
        # Проверяем вопросительные предложения (часто важные)
        if '?' in message.content:
            importance_score += 1
        
        # Дополнительные факторы
        is_detailed = len(message.content) > 50  #
        has_questions = '?' in message.content
        is_first_person = any(pronoun in content for pronoun in ['я ', 'мне ', 'мой ', 'моя ', 'мои ', 'меня '])
        
        final_score = importance_score
        if is_detailed: final_score += 0.5
        if has_questions: final_score += 0.3
        if is_first_person: final_score += 0.4
        
        print(f"🧠 Анализ важности: '{content[:30]}...' = {final_score:.1f} баллов")
        

        if final_score >= 0.5:  
            try:

                test_embedding = self._generate_embedding("test")
                print("✅ Эмбеддинги доступны, сообщение можно сохранить")
                return True
            except Exception as e:
                print(f"❌ Эмбеддинги недоступны: {e}")
                print("⚠️ Сообщение не может быть сохранено без OpenAI API")
                return False
        
        return False
    
    def _calculate_importance(self, message: Message, context: MemoryContext) -> float:
        """Рассчитать важность сообщения (0.0 - 1.0)"""
        score = 0.0
        content = message.content.lower()
        
        # Персональная информация (+0.4)
        # ИСПРАВЛЕНО: Убираем все хардкод маркеры, используем универсальные правила
        
        # Персональная информация - проверяем местоимения первого лица
        if any(pronoun in content for pronoun in ['я ', 'мне ', 'мой ', 'моя ', 'мои ', 'меня ']):
            score += 0.4
        
        # Эмоциональное содержание - проверяем восклицательные знаки и длину
        if '!' in content or len(content) > 100:
            score += 0.3
        
        # Длина сообщения (+0.2)
        if len(message.content) > 100:
            score += 0.2
        
        # Первые дни общения важнее (+0.2)
        if context.day_number <= 3:
            score += 0.2
        
        # Вопросы (+0.1)
        if '?' in message.content:
            score += 0.1
        
        return min(score, 1.0)
    
    def _extract_topics(self, content: str) -> List[str]:
        """Извлечь темы из сообщения"""
        content_lower = content.lower()
        topics = []
        
        # ИСПРАВЛЕНО: Убираем все хардкод темы
        # Используем универсальный подход - определяем темы по структуре текста
        topics = []
        
        # Определяем темы по длине и структуре сообщения
        if len(content) > 50:
            topics.append("подробный_разговор")
        if '?' in content:
            topics.append("вопрос")
        if '!' in content:
            topics.append("эмоциональное")
        
        return topics
    
    def _detect_emotions(self, content: str) -> List[str]:
        """Определить эмоции в сообщении"""
        content_lower = content.lower()
        emotions = []
        
        # ИСПРАВЛЕНО: Убираем хардкод эмоций
        # Определяем эмоции по универсальным признакам
        emotions = []
        
        # Позитивные эмоции - восклицательные знаки, смайлики
        if '!' in content or ':)' in content or '😊' in content:
            emotions.append('позитив')
        
        # Негативные эмоции - грустные смайлики
        if ':(' in content or '😢' in content:
            emotions.append('негатив')
        
        # Вопросительные - неуверенность
        if '?' in content:
            emotions.append('вопрос')
            
        return emotions
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Получить профиль пользователя из векторной БД"""
        try:
            if not self._ensure_tables():
                return {}
            
            conn = self._get_db_conn()
            if not conn:
                return {}
                
            with conn.cursor() as cursor:
                # Базовая статистика
                cursor.execute(
                    "SELECT COUNT(*) FROM vector_memories WHERE user_id = %s",
                    (self.user_id,)
                )
                total_count = cursor.fetchone()[0]
                
                if total_count == 0:
                    return {}
                
                # Анализ тем
                cursor.execute("""
                    SELECT topics FROM vector_memories 
                    WHERE user_id = %s AND topics IS NOT NULL
                """, (self.user_id,))
                topics_result = cursor.fetchall()
                
                all_topics = []
                for row in topics_result:
                    if row['topics']:
                        all_topics.extend(row['topics'])
                
                topic_counts = {}
                for topic in all_topics:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
                
                # Эмоциональный профиль
                cursor.execute("""
                    SELECT emotions FROM vector_memories 
                    WHERE user_id = %s AND emotions IS NOT NULL
                """, (self.user_id,))
                emotions_result = cursor.fetchall()
                
                all_emotions = []
                for row in emotions_result:
                    if row[0]:  # emotions
                        all_emotions.extend(row[0])
                
                emotion_counts = {}
                for emotion in all_emotions:
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                
                # Персональная информация
                cursor.execute("""
                    SELECT content FROM vector_memories 
                    WHERE user_id = %s AND importance_score > 0.7
                    ORDER BY importance_score DESC
                    LIMIT 10
                """, (self.user_id,))
                personal_memories = cursor.fetchall()
                
                profile = {
                    'user_id': self.user_id,
                    'total_messages': total_count,
                    'favorite_topics': sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5],
                    'emotional_profile': emotion_counts,
                    'personal_info': {
                        'has_name': any('я ' in m['content'].lower() for m in personal_memories),
                        'has_profession': any('работ' in m['content'].lower() for m in personal_memories),
                        'details_shared': len(personal_memories)
                    }
                }
                
                return profile
                
        except Exception as e:
            print(f"❌ Ошибка получения профиля: {e}")
            return {}
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Поиск в памяти по запросу"""
        context = MemoryContext(user_id=self.user_id)
        return self._search_memories(query, context, limit)
    
    def summarize_conversation(self, messages: List[Message]) -> str:
        """Суммаризация разговора"""
        if not messages:
            return "Разговор пуст."
        
        try:
            # Используем векторную БД для суммаризации
            if not self._ensure_tables():
                return f"Разговор из {len(messages)} сообщений."
            
            conn = self._get_db_conn()
            if not conn:
                return f"Разговор из {len(messages)} сообщений."
                
            with conn.cursor() as cursor:
                # Получаем важные воспоминания пользователя
                cursor.execute("""
                    SELECT content, topics, emotions
                    FROM vector_memories 
                    WHERE user_id = %s AND importance_score > 0.6
                    ORDER BY importance_score DESC
                    LIMIT 5
                """, (self.user_id,))
                important_memories = cursor.fetchall()
                
                if not important_memories:
                    return f"Разговор из {len(messages)} сообщений."
                
                # Анализируем темы и эмоции
                all_topics = []
                all_emotions = []
                
                for memory in important_memories:
                    if memory['topics']:
                        all_topics.extend(memory['topics'])
                    if memory['emotions']:
                        all_emotions.extend(memory['emotions'])
                
                # Подсчитываем частоту
                topic_counts = {}
                for topic in all_topics:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
                
                emotion_counts = {}
                for emotion in all_emotions:
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                
                # Формируем суммаризацию
                summary_parts = [f"Разговор из {len(messages)} сообщений"]
                
                if topic_counts:
                    top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                    summary_parts.append(f"Основные темы: {', '.join([topic for topic, _ in top_topics])}")
                
                if emotion_counts:
                    top_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                    summary_parts.append(f"Преобладающие эмоции: {', '.join([emotion for emotion, _ in top_emotions])}")
                
                return ". ".join(summary_parts)
                
        except Exception as e:
            print(f"❌ Ошибка суммаризации: {e}")
            return f"Разговор из {len(messages)} сообщений."
    
    def clear_memory(self) -> None:
        """Очистить память пользователя"""
        try:
            if not self._ensure_tables():
                return
                
            conn = self._get_db_conn()
            if not conn:
                return
                
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM vector_memories WHERE user_id = %s",
                    (self.user_id,)
                )
                conn.commit()
                print(f"🧠 VectorMemory: Память пользователя {self.user_id} очищена")
                
        except Exception as e:
            print(f"❌ Ошибка очистки памяти: {e}")
    
    def close(self):
        """Закрыть соединения с БД"""
        if hasattr(self, '_db_conn') and self._db_conn and not self._db_conn.closed:
            self._db_conn.close() 