"""
Интеллектуальная векторная память с поддержкой LangChain
Интегрируется с ChromaDB и обеспечивает семантический поиск
Полностью без хардкода - все настройки из конфигурации
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

# LangChain импорты с проверкой доступности
try:
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# ChromaDB импорты с проверкой доступности
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Импорты проекта
from .base import MemoryAdapter, Message, MemoryContext
try:
    from ..config.production_config_manager import get_config
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False


@dataclass
class MemoryDocument:
    """Документ для хранения в векторной памяти"""
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: datetime = None
    importance_score: float = 0.5
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class IntelligentVectorMemory:
    """
    Интеллектуальная векторная память с поддержкой семантического поиска
    Использует ChromaDB + OpenAI Embeddings для долгосрочного хранения
    """
    
    def __init__(self, user_id: str, collection_name: Optional[str] = None):
        """
        Инициализация интеллектуальной векторной памяти
        
        Args:
            user_id: Идентификатор пользователя
            collection_name: Имя коллекции (по умолчанию user_id)
        """
        self.user_id = user_id
        self.collection_name = collection_name or f"user_{user_id}"
        self.logger = logging.getLogger(f"{__name__}.{user_id}")
        
        # Загружаем конфигурацию
        self.config = self._load_config()
        
        # Инициализируем компоненты
        self.embeddings = None
        self.vectorstore = None
        self.chroma_client = None
        
        print(f"🚀 [VECTOR-{user_id}] Создаем IntelligentVectorMemory...")
        if LANGCHAIN_AVAILABLE and CHROMADB_AVAILABLE:
            print(f"✅ [VECTOR-{user_id}] LangChain и ChromaDB доступны, инициализируем...")
            self._initialize_components()
            
            # Проверяем результат инициализации
            if self.vectorstore is None:
                self.logger.error(f"❌ [VECTOR-{user_id}] КРИТИЧЕСКАЯ ОШИБКА: vectorstore остался None после инициализации!")
                
                try:
                    self.logger.warning(f"🔄 [VECTOR-{user_id}] Пытаемся fallback на EphemeralClient...")
                    import chromadb
                    from langchain_community.vectorstores import Chroma
                    from langchain_openai import OpenAIEmbeddings
                    import os
                    
                    openai_key = os.getenv('OPENAI_API_KEY')
                    if openai_key:
                        self.embeddings = OpenAIEmbeddings(model='text-embedding-3-small', openai_api_key=openai_key)
                        self.chroma_client = chromadb.EphemeralClient()
                        self.vectorstore = Chroma(
                            client=self.chroma_client,
                            collection_name=self.collection_name,
                            embedding_function=self.embeddings
                        )
                        self.logger.info(f"✅ [VECTOR-{user_id}] Fallback инициализация успешна (EphemeralClient)")
                    else:
                        self.logger.error(f"❌ [VECTOR-{user_id}] Нет OpenAI ключа для fallback")
                except Exception as fallback_error:
                    self.logger.error(f"❌ [VECTOR-{user_id}] Fallback тоже не сработал: {fallback_error}")
            else:
                self.logger.info(f"✅ [VECTOR-{user_id}] vectorstore успешно инициализирован")
        else:
            print(f"❌ [VECTOR-{user_id}] LangChain или ChromaDB недоступны!")
            self.logger.warning("LangChain or ChromaDB not available - using fallback mode")
        
        self.logger.info(f"IntelligentVectorMemory initialized for user {user_id}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию без хардкода"""
        if CONFIG_MANAGER_AVAILABLE:
            try:
                # Загружаем конфигурацию векторной памяти
                vector_config = get_config('vector_memory_config', self.user_id, {})
                enhanced_config = get_config('enhanced_memory_config', self.user_id, {})
                
                return {
                    **vector_config,
                    'llm': enhanced_config.get('llm', {}),
                    'features': enhanced_config.get('features', {})
                }
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
        
        # Fallback конфигурация
        return {
            'embedding_model': 'text-embedding-ada-002',
            'collection_settings': {
                'distance_function': 'cosine',
                'max_documents': 10000
            },
            'search_settings': {
                'similarity_threshold': 0.7,
                'max_results': 5,
                'include_metadata': True
            },
            'persistence': {
                'enabled': True,
                'path': './data/chroma_db'
            },
            'features': {
                'auto_cleanup': True,
                'importance_filtering': True,
                'temporal_decay': True
            }
        }
    
    def _initialize_components(self):
        """Инициализирует LangChain и ChromaDB компоненты"""
        self.logger.error(f"🚀 [VECTOR-{self.user_id}] МЕТОД _initialize_components ВЫЗВАН!")
        try:
            import os
            
            print(f"🔧 [VECTOR-{self.user_id}] Начинаем инициализацию компонентов...")
            self.logger.warning(f"🔧 [VECTOR-{self.user_id}] Начинаем инициализацию компонентов...")
            
            # Проверяем OpenAI API ключ
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                print(f"❌ [VECTOR-{self.user_id}] OPENAI_API_KEY не найден!")
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            
            self.logger.warning(f"✅ [VECTOR-{self.user_id}] OpenAI ключ найден")
            
            # Инициализируем embeddings
            embedding_model = self.config.get('embedding_model', 'text-embedding-3-small')
            print(f"🔧 [VECTOR-{self.user_id}] Инициализируем embeddings: {embedding_model}")
            self.embeddings = OpenAIEmbeddings(model=embedding_model, openai_api_key=openai_key)
            self.logger.debug(f"Embeddings initialized with model: {embedding_model}")
            print(f"✅ [VECTOR-{self.user_id}] Embeddings инициализированы")
            
            # Настройки ChromaDB - упрощенная инициализация
            persistence_config = self.config.get('persistence', {})
            print(f"🔧 [VECTOR-{self.user_id}] Настройки persistence: {persistence_config}")
            
            if persistence_config.get('enabled', True):
                persist_directory = persistence_config.get('path', './data/chroma_db')
                # Преобразуем в абсолютный путь
                persist_directory = os.path.abspath(persist_directory)
                self.logger.warning(f"📁 [VECTOR-{self.user_id}] Создаем директорию: {persist_directory}")
                
                # Создаем директорию если не существует
                try:
                    os.makedirs(persist_directory, exist_ok=True)
                    self.logger.warning(f"📁 [VECTOR-{self.user_id}] Директория создана успешно")
                except Exception as dir_error:
                    self.logger.error(f"❌ [VECTOR-{self.user_id}] Ошибка создания директории: {dir_error}")
                    raise
                
                self.logger.debug(f"Using persist directory: {persist_directory}")
                
                self.logger.warning(f"🔧 [VECTOR-{self.user_id}] Инициализируем PersistentClient...")
                # Используем PersistentClient для надежности
                try:
                    self.chroma_client = chromadb.PersistentClient(path=persist_directory)
                    self.logger.warning(f"✅ [VECTOR-{self.user_id}] PersistentClient создан")
                except Exception as client_error:
                    self.logger.error(f"❌ [VECTOR-{self.user_id}] Ошибка создания PersistentClient: {client_error}")
                    raise
            else:
                print(f"🔧 [VECTOR-{self.user_id}] Используем EphemeralClient (в памяти)")
                # In-memory клиент для тестирования
                self.chroma_client = chromadb.EphemeralClient()
                print(f"✅ [VECTOR-{self.user_id}] EphemeralClient создан")
            
            self.logger.debug("ChromaDB client initialized")
            
            self.logger.info(f"🔧 [VECTOR-{self.user_id}] Создаем Chroma vectorstore...")
            # Инициализируем Chroma vectorstore
            try:
                # Используем новую версию Chroma из langchain-chroma
                try:
                    from langchain_chroma import Chroma
                    self.vectorstore = Chroma(
                        client=self.chroma_client,
                        collection_name=self.collection_name,
                        embedding_function=self.embeddings
                    )
                except ImportError:
                    # Fallback на старую версию
                    from langchain.vectorstores import Chroma
                    self.vectorstore = Chroma(
                        client=self.chroma_client,
                        collection_name=self.collection_name,
                        embedding_function=self.embeddings
                    )
                self.logger.info(f"✅ [VECTOR-{self.user_id}] Chroma vectorstore создан!")
            except Exception as vs_error:
                self.logger.error(f"❌ [VECTOR-{self.user_id}] Ошибка создания Chroma vectorstore: {vs_error}")
                raise
            
            self.logger.warning(f"✅ [VECTOR-{self.user_id}] Все компоненты инициализированы успешно!")
            self.logger.warning(f"🔍 [VECTOR-{self.user_id}] Финальная проверка: embeddings={self.embeddings is not None}, vectorstore={self.vectorstore is not None}")
            self.logger.info("LangChain components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"💥 [VECTOR-{self.user_id}] ОШИБКА инициализации: {e}")
            self.logger.error(f"💥 [VECTOR-{self.user_id}] Тип ошибки: {type(e).__name__}")
            self.logger.error(f"Failed to initialize LangChain components: {e}")
            self.logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            
            # Подробная диагностика
            import traceback
            self.logger.error(f"💥 [VECTOR-{self.user_id}] Полный traceback:")
            self.logger.error(traceback.format_exc())
            
            self.embeddings = None
            self.vectorstore = None
            return False
    
    def add_document(self, content: str, metadata: Dict[str, Any] = None, 
                    importance_score: float = 0.5) -> bool:
        """
        Добавляет документ в векторную память
        
        Args:
            content: Содержимое документа
            metadata: Метаданные документа
            importance_score: Оценка важности (0.0-1.0)
            
        Returns:
            True если документ добавлен успешно
        """
        try:
            print(f"🔍 [VECTOR-{self.user_id}] Добавляем документ: '{content[:50]}...' (важность: {importance_score})")
            print(f"🔍 [VECTOR-{self.user_id}] Проверяем состояние: vectorstore={self.vectorstore}, embeddings={self.embeddings}")
            print(f"🔍 [VECTOR-{self.user_id}] Результат проверки: not vectorstore={not self.vectorstore}, not embeddings={not self.embeddings}")
            
            if self.vectorstore is None or self.embeddings is None:
                print(f"⚠️ [VECTOR-{self.user_id}] Vector store не инициализирован!")
                self.logger.warning("Vector store or embeddings not initialized - attempting re-initialization")
                print(f"🔄 [VECTOR-{self.user_id}] Пытаемся переинициализировать...")
                self.logger.error(f"🔄 [VECTOR-{self.user_id}] ВЫЗЫВАЕМ _initialize_components()...")
                init_success = self._initialize_components()
                self.logger.error(f"🔄 [VECTOR-{self.user_id}] _initialize_components() вернул: {init_success}")
                if init_success and self.vectorstore:
                    print(f"✅ [VECTOR-{self.user_id}] Переинициализация успешна")
                else:
                    print(f"❌ [VECTOR-{self.user_id}] Не удалось инициализировать! init_success={init_success}, vectorstore={self.vectorstore}")
                    return False
            
            # Проверяем важность документа
            if self.config.get('features', {}).get('importance_filtering', True):
                min_importance = self.config.get('search_settings', {}).get('min_importance', 0.3)
                print(f"📊 [VECTOR-{self.user_id}] Проверяем важность: {importance_score} >= {min_importance}")
                if importance_score < min_importance:
                    print(f"❌ [VECTOR-{self.user_id}] Документ пропущен - низкая важность: {importance_score} < {min_importance}")
                    self.logger.debug(f"Document skipped due to low importance: {importance_score}")
                    return False
                print(f"✅ [VECTOR-{self.user_id}] Важность достаточна: {importance_score}")
            
            # Подготавливаем метаданные
            doc_metadata = {
                'user_id': self.user_id,
                'created_at': datetime.utcnow().isoformat(),
                'importance_score': importance_score,
                'content_length': len(content),
                **(metadata or {})
            }
            
            # Создаем Document объект
            document = Document(
                page_content=content,
                metadata=doc_metadata
            )
            
            # Добавляем в векторную базу
            doc_ids = self.vectorstore.add_documents([document])
            
            self.logger.debug(f"Document added to vector memory: {doc_ids[0]}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add document to vector memory: {e}")
            return False
    
    def search_similar(self, query: str, max_results: int = None, 
                      similarity_threshold: float = None) -> List[Dict[str, Any]]:
        """
        Поиск похожих документов по семантическому сходству
        
        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов
            similarity_threshold: Порог сходства
            
        Returns:
            Список найденных документов с метаданными
        """
        try:
            if not self.vectorstore:
                self.logger.warning("Vector store not initialized")
                return []
            
            # Параметры поиска из конфигурации
            search_config = self.config.get('search_settings', {})
            max_results = max_results or search_config.get('max_results', 5)
            threshold = similarity_threshold or search_config.get('similarity_threshold', 0.05)
            
            print(f"🔍 [VECTOR-{self.user_id}] Поиск: '{query}' (порог: {threshold}, max: {max_results})")
            
            # Выполняем поиск с оценками сходства
            print(f"🔍 [VECTOR-{self.user_id}] Выполняем поиск в ChromaDB...")
            results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=max_results
            )
            
            print(f"🔍 [VECTOR-{self.user_id}] ChromaDB вернул {len(results)} результатов")
            
            # Попробуем альтернативный поиск без scores
            if not results:
                print(f"🔍 [VECTOR-{self.user_id}] Попробуем поиск без scores...")
                results_no_score = self.vectorstore.similarity_search(query, k=max_results)
                print(f"🔍 [VECTOR-{self.user_id}] Поиск без scores вернул {len(results_no_score)} результатов")
                if results_no_score:
                    # Конвертируем в формат с scores
                    results = [(doc, 0.0) for doc in results_no_score]
                    print(f"🔍 [VECTOR-{self.user_id}] Конвертировали в формат с scores")
            
            # Фильтруем по порогу сходства и форматируем результаты
            formatted_results = []
            for i, (doc, score) in enumerate(results):
                if score == 0.0:
                    similarity = 1.0  # Поиск без scores - считаем идеальным совпадением
                else:
                    similarity = max(0.1, 1.0 - score)
                
                print(f"🔍 [VECTOR-{self.user_id}] Результат {i+1}: score={score}, similarity={similarity}, content='{doc.page_content[:50]}...'")
                
                if similarity >= threshold:
                    formatted_results.append({
                        'content': doc.page_content,
                        'metadata': doc.metadata,
                        'similarity_score': similarity,
                        'relevance_score': similarity,
                        'timestamp': doc.metadata.get('message_timestamp'),
                        'role': doc.metadata.get('message_role', 'unknown')
                    })
                    print(f"✅ [VECTOR-{self.user_id}] Документ {i+1} прошел порог {threshold}")
                else:
                    print(f"❌ [VECTOR-{self.user_id}] Документ {i+1} НЕ прошел порог {threshold} (similarity={similarity})")
            
            print(f"🔍 [VECTOR-{self.user_id}] Итоговый результат: {len(formatted_results)} документов выше порога {threshold}")
            self.logger.debug(f"Search found {len(formatted_results)} documents above threshold {threshold}")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Failed to search vector memory: {e}")
            return []
    
    def search_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Алиас для search_similar для совместимости с MemoryLevelsManager
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных воспоминаний
        """
        return self.search_similar(query, max_results=limit)
    
    def _apply_temporal_decay(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Применяет временное затухание к результатам поиска
        
        Args:
            results: Результаты поиска
            
        Returns:
            Результаты с скорректированными оценками
        """
        try:
            decay_config = self.config.get('temporal_decay', {})
            half_life_days = decay_config.get('half_life_days', 30)  # 30 дней
            
            current_time = datetime.utcnow()
            
            for result in results:
                # Получаем время создания документа
                created_at_str = result['metadata'].get('created_at')
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    
                    # Вычисляем возраст в днях
                    age_days = (current_time - created_at).total_seconds() / (24 * 3600)
                    
                    # Применяем экспоненциальное затухание
                    decay_factor = 0.5 ** (age_days / half_life_days)
                    
                    # Корректируем оценку сходства
                    original_score = result['similarity_score']
                    result['similarity_score'] = original_score * decay_factor
                    result['temporal_decay_factor'] = decay_factor
                    result['age_days'] = age_days
            
            return results
            
        except Exception as e:
            self.logger.warning(f"Failed to apply temporal decay: {e}")
            return results
    
    def add_message_to_memory(self, message: Message, context: MemoryContext,
                             min_importance: float = None) -> bool:
        """
        Добавляет сообщение в долгосрочную векторную память
        
        Args:
            message: Сообщение для добавления
            context: Контекст памяти
            min_importance: Минимальная важность для сохранения
            
        Returns:
            True если сообщение добавлено
        """
        try:
            # Определяем важность сообщения
            importance = self._calculate_message_importance(message, context)
            
            # Проверяем порог важности
            min_importance = min_importance or self.config.get('search_settings', {}).get('min_importance', 0.5)
            if importance < min_importance:
                return False
            
            # Подготавливаем метаданные
            metadata = {
                'message_role': message.role,
                'conversation_id': context.conversation_id or 'default',
                'day_number': context.day_number,
                'user_id': context.user_id,
                'message_timestamp': message.timestamp.isoformat(),
                **message.metadata
            }
            
            # Добавляем в векторную память
            return self.add_document(
                content=message.content,
                metadata=metadata,
                importance_score=importance
            )
            
        except Exception as e:
            self.logger.error(f"Failed to add message to vector memory: {e}")
            return False
    
    def _calculate_message_importance(self, message: Message, context: MemoryContext) -> float:
        """
        Рассчитывает важность сообщения для долгосрочного хранения
        
        Args:
            message: Сообщение
            context: Контекст
            
        Returns:
            Оценка важности (0.0-1.0)
        """
        # Базовая важность по роли
        role_weights = self.config.get('importance_calculation', {}).get('role_weights', {})
        base_importance = role_weights.get(message.role, 0.5)
        
        # Проверяем ключевые слова важности - ИСПРАВЛЕНО: учитываем ВСЕ маркеры
        importance_markers = self.config.get('importance_calculation', {}).get('importance_markers', {})
        content_lower = message.content.lower()
        
        # Ищем максимальный вес среди всех найденных маркеров
        max_weight = 0.0
        for category, data in importance_markers.items():
            markers = data.get('markers', [])
            weight = data.get('weight', 0.0)
            
            if any(marker in content_lower for marker in markers):
                max_weight = max(max_weight, weight)
        
        base_importance += max_weight
        
        # Учитываем длину сообщения
        length_config = self.config.get('importance_calculation', {}).get('length_weights', {})
        content_length = len(message.content)
        
        if content_length > length_config.get('long_threshold', 200):
            base_importance += length_config.get('long_bonus', 0.1)
        elif content_length < length_config.get('short_threshold', 10):
            base_importance += length_config.get('short_penalty', -0.1)
        
        # Дополнительный бонус для первых дней общения
        if context.day_number <= 3:
            base_importance += 0.1
        
        return max(0.0, min(1.0, base_importance))
    
    def cleanup_old_documents(self, max_age_days: int = None) -> int:
        try:
            if not self.vectorstore or not self.config.get('features', {}).get('auto_cleanup', True):
                return 0
            
            max_age_days = max_age_days or self.config.get('cleanup', {}).get('max_age_days', 90)
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            
            # Получаем все документы коллекции
            collection = self.chroma_client.get_collection(self.collection_name)
            all_docs = collection.get(include=['metadatas'])
            
            # Находим документы для удаления
            docs_to_delete = []
            for doc_id, metadata in zip(all_docs['ids'], all_docs['metadatas']):
                created_at_str = metadata.get('created_at')
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if created_at < cutoff_date:
                        docs_to_delete.append(doc_id)
            
            # Удаляем старые документы
            if docs_to_delete:
                collection.delete(ids=docs_to_delete)
                self.logger.info(f"Cleaned up {len(docs_to_delete)} old documents")
            
            return len(docs_to_delete)
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old documents: {e}")
            return 0
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Получает статистику векторной памяти
        
        Returns:
            Словарь со статистикой
        """
        try:
            if not self.vectorstore:
                return {'status': 'not_initialized'}
            
            # Получаем информацию о коллекции
            collection = self.chroma_client.get_collection(self.collection_name)
            collection_info = collection.get(include=['metadatas'])
            
            total_docs = len(collection_info['ids'])
            
            # Анализируем метаданные
            importance_scores = []
            content_lengths = []
            recent_docs = 0
            
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            for metadata in collection_info['metadatas']:
                if 'importance_score' in metadata:
                    importance_scores.append(metadata['importance_score'])
                if 'content_length' in metadata:
                    content_lengths.append(metadata['content_length'])
                
                created_at_str = metadata.get('created_at')
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if created_at > week_ago:
                        recent_docs += 1
            
            return {
                'status': 'active',
                'total_documents': total_docs,
                'recent_documents_7d': recent_docs,
                'avg_importance': sum(importance_scores) / len(importance_scores) if importance_scores else 0,
                'avg_content_length': sum(content_lengths) / len(content_lengths) if content_lengths else 0,
                'collection_name': self.collection_name,
                'config': {
                    'embedding_model': self.config.get('embedding_model'),
                    'max_results': self.config.get('search_settings', {}).get('max_results'),
                    'similarity_threshold': self.config.get('search_settings', {}).get('similarity_threshold')
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get memory stats: {e}")
            return {'status': 'error', 'error': str(e)}


# Функция-фабрика для создания интеллектуальной векторной памяти
def create_intelligent_vector_memory(user_id: str, collection_name: Optional[str] = None) -> IntelligentVectorMemory:
    """
    Создает экземпляр интеллектуальной векторной памяти
    
    Args:
        user_id: Идентификатор пользователя
        collection_name: Имя коллекции
        
    Returns:
        Экземпляр интеллектуальной векторной памяти
    """
    return IntelligentVectorMemory(user_id, collection_name)
