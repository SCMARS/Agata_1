"""
Memory Adapter - адаптер для подготовки данных памяти для промпта
"""
from typing import Dict, Optional, List, Any
from datetime import datetime
import logging
import yaml
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from .unified_memory import UnifiedMemoryManager

logger = logging.getLogger(__name__)


class MemoryAdapter:
    """Адаптер для унификации работы с разными типами памяти"""
    
    def __init__(self, memory_manager, config=None):
        self.memory_manager = memory_manager
        
        # НОВАЯ АРХИТЕКТУРА: Инициализируем UnifiedMemoryManager
        # ИСПРАВЛЕНИЕ: Получаем правильный user_id
        if hasattr(memory_manager, 'user_id'):
            user_id = memory_manager.user_id
        else:
            user_id = getattr(memory_manager, 'user_id', 'default_user')
        
        # Сохраняем user_id для использования в get_for_prompt
        self.current_user_id = user_id
        
        try:
            # ИСПРАВЛЕНИЕ: Используем переданный UnifiedMemoryManager если он уже есть
            if isinstance(memory_manager, UnifiedMemoryManager):
                self.unified_memory = memory_manager
                self.use_unified = True
                logger.info(f"✅ [ADAPTER] Используем переданный UnifiedMemoryManager для {user_id}")
                print(f"✅ [ADAPTER] Используем переданный UnifiedMemoryManager для {user_id}")
            else:
                # Создаем только если не передан UnifiedMemoryManager
                self.unified_memory = UnifiedMemoryManager(user_id)
                self.use_unified = True
                logger.info(f"✅ [ADAPTER] Создан новый UnifiedMemoryManager для {user_id}")
                print(f"✅ [ADAPTER] Создан новый UnifiedMemoryManager для {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ [ADAPTER] Ошибка инициализации UnifiedMemoryManager: {e}")
            self.unified_memory = None
            self.use_unified = False
        self.logger = logging.getLogger(__name__)
        
        # Загружаем конфигурацию
        self.config = self._load_config(config)
        self.max_facts = self.config.get('max_facts', 50)
        self.max_short_messages = self.config.get('max_short_messages', 20)
        self.max_semantic_results = self.config.get('max_semantic_results', 8)
        self.facts_search_multiplier = self.config.get('facts_search_multiplier', 4)
        self.search_queries = self.config.get('search_queries', {
            'personal_info': 'личная информация пользователь предпочтения интересы семья работа учеба',
            'general_context': 'контекст диалог разговор общение'
        })
        self.content_limits = self.config.get('content_limits', {
            'short_message_length': 100,
            'min_fact_length': 10,
            'min_document_length': 20,
            'log_preview_length': 50,
            'fact_log_preview_length': 30
        })

        self._cache = {}
        self._cache_ttl = 60  # 60 секунд кэша
        self._executor = ThreadPoolExecutor(max_workers=2)  
    
    def _load_config(self, config=None):
        """Загружает конфигурацию из файла или переданных параметров"""
        if config:
            return config
            
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'memory_adapter_config.yml')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f)
                    return full_config.get('memory_adapter', {})
        except Exception as e:
            self.logger.warning(f"Не удалось загрузить конфигурацию: {e}")
            
        return {}
    
    def _get_cache_key(self, user_id: str, operation: str, params: str = "") -> str:
        """Генерирует ключ кэша"""
        return f"{user_id}:{operation}:{hash(params)}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[str]:
        """Получает результат из кэша"""
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.info(f"✅ [ADAPTER] Используем кэш для {cache_key}")
                return result
            else:
                # Удаляем устаревший кэш
                del self._cache[cache_key]
        return None
    
    def _set_cached_result(self, cache_key: str, result: str):
        """Сохраняет результат в кэш"""
        self._cache[cache_key] = (result, time.time())
        logger.info(f"💾 [ADAPTER] Сохранили в кэш {cache_key}")
    
    def _search_memory_with_timeout(self, query: str, limit: int, timeout: float = 5.0) -> List:
        """Поиск в памяти с таймаутом"""
        try:
            if hasattr(self.memory_manager, 'long_term') and self.memory_manager.long_term:
                # Используем ThreadPoolExecutor для неблокирующего поиска
                future = self._executor.submit(
                    self.memory_manager.long_term.search_memories,
                    query, limit
                )
                return future.result(timeout=timeout)
            return []
        except Exception as e:
            logger.warning(f"⚠️ [ADAPTER] Поиск с таймаутом не удался: {e}")
            return []
    
    def get_for_prompt(self, user_id: str, query: str) -> Dict[str, str]:
        """
        Получает все данные памяти для промпта
        НОВАЯ АРХИТЕКТУРА: Использует UnifiedMemoryManager
        
        Args:
            user_id: ID пользователя
            query: текущий запрос пользователя
            
        Returns:
            Словарь с данными для промпта
        """
        try:
            logger.info(f"🚀 [ADAPTER] СТАРТ get_for_prompt для {user_id}, запрос: {query[:50]}...")
            print(f"🚀 [ADAPTER] СТАРТ get_for_prompt для {user_id}, запрос: {query[:50]}...")
            
            # НОВАЯ АРХИТЕКТУРА: Используем UnifiedMemoryManager если доступен
            if self.use_unified and self.unified_memory:
                logger.info(f"🧠 [ADAPTER] Используем НОВУЮ АРХИТЕКТУРУ (UnifiedMemoryManager) для {user_id}")
                print(f"🧠 [ADAPTER] Используем НОВУЮ АРХИТЕКТУРУ (UnifiedMemoryManager) для {user_id}")
                
                # ИСПРАВЛЕНИЕ: Если user_id не совпадает с текущим, создаем новый UnifiedMemoryManager
                if self.current_user_id != user_id:
                    logger.info(f"🔄 [ADAPTER] Смена пользователя: {self.current_user_id} → {user_id}")
                    print(f"🔄 [ADAPTER] Смена пользователя: {self.current_user_id} → {user_id}")
                    try:
                        self.unified_memory = UnifiedMemoryManager(user_id)
                        self.current_user_id = user_id
                        logger.info(f"✅ [ADAPTER] Создан новый UnifiedMemoryManager для {user_id}")
                        print(f"✅ [ADAPTER] Создан новый UnifiedMemoryManager для {user_id}")
                    except Exception as e:
                        logger.error(f"❌ [ADAPTER] Ошибка создания UnifiedMemoryManager для {user_id}: {e}")
                        print(f"❌ [ADAPTER] Ошибка создания UnifiedMemoryManager для {user_id}: {e}")
                        return self._get_legacy_context(user_id, query)
                
                # Получаем контекст из унифицированной системы
                unified_context = self.unified_memory.get_context_for_prompt(query)
                
                # Логируем статистику памяти
                stats = self.unified_memory.get_memory_stats()
                logger.info(f"📊 [ADAPTER] Статистика памяти: {stats}")
                print(f"📊 [ADAPTER] Статистика памяти: {stats}")
                
                result = unified_context
            else:
                logger.info(f"⚠️ [ADAPTER] Используем СТАРУЮ АРХИТЕКТУРУ (fallback)")
                print(f"⚠️ [ADAPTER] Используем СТАРУЮ АРХИТЕКТУРУ (fallback)")
                
                # Fallback к старой системе
                result = self._get_legacy_context(user_id, query)
            
            logger.info(f"✅ [ADAPTER] РЕЗУЛЬТАТ get_for_prompt: short={len(result['short_memory_summary'])}, facts={len(result['long_memory_facts'])}, semantic={len(result['semantic_context'])}")
            print(f"✅ [ADAPTER] РЕЗУЛЬТАТ get_for_prompt: short={len(result['short_memory_summary'])}, facts={len(result['long_memory_facts'])}, semantic={len(result['semantic_context'])}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [ADAPTER] Ошибка получения данных памяти для промпта: {e}")
            print(f"❌ [ADAPTER] Ошибка получения данных памяти для промпта: {e}")
            import traceback
            logger.error(f"❌ [ADAPTER] Traceback: {traceback.format_exc()}")
            print(f"❌ [ADAPTER] Traceback: {traceback.format_exc()}")
            
            # Возвращаем пустые данные в случае ошибки
            return {
                "short_memory_summary": "—",
                "long_memory_facts": "—",
                "semantic_context": "—"
            }
    
    def add_message_to_unified(self, role: str, content: str, metadata: Dict[str, Any] = None, user_id: str = None, timestamp: Optional[datetime] = None) -> Dict[str, bool]:
        """
        Добавляет сообщение в унифицированную систему памяти
        НОВАЯ АРХИТЕКТУРА
        """
        if self.use_unified and self.unified_memory:
            # ИСПРАВЛЕНИЕ: Проверяем соответствие user_id
            if user_id and self.current_user_id != user_id:
                logger.info(f"🔄 [ADAPTER] Смена пользователя в add_message: {self.current_user_id} → {user_id}")
                try:
                    self.unified_memory = UnifiedMemoryManager(user_id)
                    self.current_user_id = user_id
                    logger.info(f"✅ [ADAPTER] Создан новый UnifiedMemoryManager для {user_id}")
                except Exception as e:
                    logger.error(f"❌ [ADAPTER] Ошибка создания UnifiedMemoryManager для {user_id}: {e}")
                    return {'short_term': False, 'long_term': False}
            
            try:
                result = self.unified_memory.add_message(role, content, metadata, timestamp)
                logger.info(f"✅ [ADAPTER] Сообщение добавлено в унифицированную память: {result}")
                return result
            except Exception as e:
                logger.error(f"❌ [ADAPTER] Ошибка добавления в унифицированную память: {e}")
                return {'short_term': False, 'long_term': False}
        else:
            logger.warning(f"⚠️ [ADAPTER] UnifiedMemoryManager недоступен, используем старую систему")
            return {'short_term': False, 'long_term': False}
    
    def _get_legacy_context(self, user_id: str, query: str) -> Dict[str, str]:
        """Старая архитектура - fallback"""
        # Получаем короткую сводку
        short_summary = self._get_short_memory_summary(user_id)
        
        # Получаем долгосрочные факты (с улучшенным поиском)
        long_facts = self._get_long_memory_facts(user_id)
        
        # Получаем семантический контекст
        semantic_context = self._get_semantic_context(user_id, query)
        
        # НОВОЕ: Специальный поиск имени, если его нет в других результатах
        name_context = self._ensure_name_in_context(user_id, long_facts, semantic_context)
        
        # Объединяем долгосрочные факты с найденным именем
        if name_context and name_context not in (long_facts or ""):
            combined_facts = f"{name_context}\n{long_facts}" if long_facts else name_context
        else:
            combined_facts = long_facts
        
        result = {
            "short_memory_summary": short_summary or "—",
            "long_memory_facts": combined_facts or "—", 
            "semantic_context": semantic_context or "—",
        }
        
        # Ищем актуальные факты
        logger.info(f"🔍 [ADAPTER] ПРОВЕРЯЕМ long_memory_facts: '{result['long_memory_facts'][:50]}...'")
        if result["long_memory_facts"] == "—" or len(result["long_memory_facts"]) < 50:
                try:
                    logger.info(f"🚨 [ADAPTER] ПРИНУДИТЕЛЬНОЕ ИСПРАВЛЕНИЕ: Ищем актуальные факты пользователя")
                    # Принудительный поиск актуальных фактов
                    if hasattr(self.memory_manager, 'long_term') and self.memory_manager.long_term:
                        # Используем текущий запрос для поиска релевантных фактов
                        current_query = query if query and len(query) > 5 else "информация о пользователе"
                        
                        search_results = self.memory_manager.long_term.search(current_query, similarity_threshold=0.0, max_results=15)
                        
                        if search_results:
                            forced_facts = []
                            logger.info(f"🔍 [ADAPTER] Обрабатываем {len(search_results)} результатов поиска")
                            
                            for i, search_result in enumerate(search_results[:10]):
                                content = search_result.get('content', '') or search_result.get('document', '')
                                score = search_result.get('relevance_score', 0)
                                
                                logger.info(f"🔍 [ADAPTER] Результат {i+1}: score={score:.3f}, content='{content[:80]}...'")
                                
                                # Берем ВСЕ результаты с хорошим score
                                if content and len(content) > 10 and score > 0.1:
                                    # Используем интеллектуальную фильтрацию вместо хардкода
                                    try:
                                        from ..utils.fact_extractor import fact_extractor
                                        if fact_extractor.should_store_in_long_term(content, "user"):
                                            forced_facts.append(f"• {content}")
                                            logger.info(f"✅ [ADAPTER] Добавлен факт: {content[:60]}...")
                                        else:
                                            logger.info(f"🚫 [ADAPTER] Отфильтрован (не важен): {content[:60]}...")
                                    except Exception as e:
                                        logger.warning(f"⚠️ Ошибка интеллектуальной фильтрации: {e}")

                            else:
                                logger.warning(f"⚠️ Не найдено подходящих фактов после фильтрации")
                        else:
                            logger.warning(f"⚠️ Поиск в векторной БД не вернул результатов")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка принудительного поиска: {e}")
        
        return result
            
    
    def _get_short_memory_summary(self, user_id: str) -> Optional[str]:
        """Получает короткую сводку последних сообщений"""
        try:
            logger.info(f"🔍 [ADAPTER] Получаем короткую сводку для {user_id}")
            
            # ИСПРАВЛЕНИЕ: Проверяем разные типы memory_manager
            
            # Вариант 1: MemoryLevelsManager
            if hasattr(self.memory_manager, 'short_term') and self.memory_manager.short_term:
                short_term = self.memory_manager.short_term
                logger.info(f"🔍 [ADAPTER] short_term найден: {type(short_term)}")
                
                # Метод 1: get_context_string (основной для ShortMemory)
                if hasattr(short_term, 'get_context_string'):
                    try:
                        context_string = short_term.get_context_string()
                        if context_string and context_string != "Нет сообщений в памяти":
                            logger.info(f"✅ [ADAPTER] get_context_string вернул {len(context_string)} символов")
                            return context_string
                    except Exception as e:
                        logger.warning(f"⚠️ [ADAPTER] get_context_string failed: {e}")
                
                # Метод 2: get_context (возвращает список сообщений)
                if hasattr(short_term, 'get_context'):
                    try:
                        messages = short_term.get_context()
                        if messages:
                            logger.info(f"✅ [ADAPTER] get_context вернул {len(messages)} сообщений")
                            
                            # Форматируем в читаемый вид
                            summary_parts = []
                            for msg in messages[-self.max_short_messages:]:  # Настраиваемое количество сообщений
                                if isinstance(msg, dict):
                                    role = msg.get('role', 'unknown')
                                    content = msg.get('content', '')[:self.content_limits['short_message_length']]  # Обрезаем длинные сообщения
                                else:
                                    # Если это объект сообщения
                                    role = getattr(msg, 'role', 'unknown')
                                    content = getattr(msg, 'content', str(msg))[:self.content_limits['short_message_length']]
                                
                                if content:
                                    summary_parts.append(f"[{role.upper()}]: {content}")
                            
                            if summary_parts:
                                result = "\n".join(summary_parts)
                                logger.info(f"✅ [ADAPTER] Сформирована сводка из get_context: {len(result)} символов")
                                return result
                    except Exception as e:
                        logger.warning(f"⚠️ [ADAPTER] get_context failed: {e}")
            
            # Вариант 2: HybridMemory с short_memory
            if hasattr(self.memory_manager, 'short_memory') and self.memory_manager.short_memory:
                try:
                    buffer = self.memory_manager.short_memory
                    logger.info(f"🔍 [ADAPTER] HybridMemory.short_memory найден: {type(buffer)}")
                    
                    if hasattr(buffer, 'messages') and buffer.messages:
                        recent_messages = buffer.messages[-20:]  # Последние 20 сообщений
                        logger.info(f"✅ [ADAPTER] short_memory.messages: {len(recent_messages)} сообщений")
                        
                        # Форматируем в читаемый вид
                        summary_parts = []
                        for msg in recent_messages:
                            if isinstance(msg, dict):
                                role = msg.get('role', 'unknown')
                                content = msg.get('content', '')[:self.content_limits['short_message_length']]
                            else:
                                role = getattr(msg, 'role', 'unknown')
                                content = getattr(msg, 'content', str(msg))[:self.content_limits['short_message_length']]
                            
                            if content:
                                summary_parts.append(f"[{role.upper()}]: {content}")
                        
                        if summary_parts:
                            result = "\n".join(summary_parts)
                            logger.info(f"✅ [ADAPTER] Сформирована сводка из HybridMemory: {len(result)} символов")
                            return result
                except Exception as e:
                    logger.warning(f"⚠️ [ADAPTER] HybridMemory short_memory failed: {e}")
            
            # Вариант 3: Простой MemoryAdapter с messages
            if hasattr(self.memory_manager, 'messages') and self.memory_manager.messages:
                try:
                    recent_messages = self.memory_manager.messages[-10:]
                    logger.info(f"✅ [ADAPTER] direct messages: {len(recent_messages)} сообщений")
                    
                    # Форматируем в читаемый вид
                    summary_parts = []
                    for msg in recent_messages:
                        if isinstance(msg, dict):
                            role = msg.get('role', 'unknown')
                            content = msg.get('content', '')[:100]
                        else:
                            role = getattr(msg, 'role', 'unknown')
                            content = getattr(msg, 'content', str(msg))[:100]
                        
                        if content:
                            summary_parts.append(f"[{role.upper()}]: {content}")
                    
                    if summary_parts:
                        result = "\n".join(summary_parts)
                        logger.info(f"✅ [ADAPTER] Сформирована сводка из direct messages: {len(result)} символов")
                        return result
                except Exception as e:
                    logger.warning(f"⚠️ [ADAPTER] direct messages failed: {e}")
            
            logger.warning(f"❌ [ADAPTER] Не удалось получить короткую сводку для {user_id}")
            logger.info(f"❌ [ADAPTER] Доступные атрибуты memory_manager: {dir(self.memory_manager)}")
            return None
            
        except Exception as e:
            logger.warning(f"❌ [ADAPTER] Ошибка получения короткой сводки: {e}")
            return None
    
    def _get_long_memory_facts(self, user_id: str) -> Optional[str]:
        """Получает долгосрочные факты о пользователе с кэшированием и таймаутом"""
        try:
            
            cache_key = self._get_cache_key(user_id, "long_facts", "")
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            logger.info(f"🔍 [ADAPTER] Получаем долгосрочные факты для {user_id}")
            
            # Вариант 1: MemoryLevelsManager с long_term
            if hasattr(self.memory_manager, 'long_term') and self.memory_manager.long_term:
                logger.info(f"🔍 [ADAPTER] long_term найден: {type(self.memory_manager.long_term)}")
                
                try:
                    # Оптимизированный поиск с таймаутом
                    user_facts = self._search_memory_with_timeout(
                        query=self.search_queries.get('personal_info', 'личная информация пользователь предпочтения интересы'),
                        limit=self.max_semantic_results * self.facts_search_multiplier,
                        timeout=3.0  # Ограничиваем время поиска
                    )
                    
                    logger.info(f"🔍 [ADAPTER] Поиск фактов вернул {len(user_facts) if user_facts else 0} результатов")
                    
                    if user_facts:
                        facts_parts = []
                        for fact in user_facts:
                            content = fact.get('content', '')
                            logger.info(f"🔍 [ADAPTER] Обрабатываем факт: {content[:self.content_limits['log_preview_length']]}...")
                            
                            # Добавляем все найденные факты - доверяем векторному поиску
                            if content and len(content) > self.content_limits['min_fact_length']:
                                facts_parts.append(f"• {content}")
                                logger.info(f"✅ [ADAPTER] Факт добавлен: {content[:self.content_limits['fact_log_preview_length']]}...")
                        
                        if facts_parts:
                            # Используем настраиваемое ограничение (если не отключено)
                            if self.max_facts == -1:
                                result = "\n".join(facts_parts)  # Без ограничений
                            else:
                                result = "\n".join(facts_parts[:self.max_facts])
                            logger.info(f"✅ [ADAPTER] Сформированы долгосрочные факты: {len(facts_parts)} фактов, {len(result)} символов")
                            
                            # Кэшируем результат
                            self._set_cached_result(cache_key, result)
                            return result
                        else:
                            logger.warning(f"⚠️ [ADAPTER] Факты найдены, но все отфильтрованы")
                    else:
                        logger.warning(f"⚠️ [ADAPTER] Долгосрочные факты не найдены")
                except Exception as e:
                    logger.warning(f"⚠️ [ADAPTER] long_term.search_memories failed: {e}")
            
            # Вариант 2: HybridMemory с long_memory
            if hasattr(self.memory_manager, 'long_memory') and self.memory_manager.long_memory:
                try:
                    long_memory = self.memory_manager.long_memory
                    logger.info(f"🔍 [ADAPTER] HybridMemory.long_memory найден: {type(long_memory)}")
                    
                    # Пытаемся получить профиль пользователя
                    if hasattr(long_memory, 'get_user_profile'):
                        profile = long_memory.get_user_profile()
                        if profile:
                            logger.info(f"✅ [ADAPTER] Получен профиль пользователя: {profile}")
                            
                            facts_parts = []
                            if profile.get('name'):
                                facts_parts.append(f"• Имя: {profile['name']}")
                            if profile.get('age'):
                                facts_parts.append(f"• Возраст: {profile['age']} лет")
                            if profile.get('interests'):
                                facts_parts.append(f"• Интересы: {', '.join(profile['interests'])}")
                            if profile.get('favorite_topics'):
                                facts_parts.append(f"• Любимые темы: {', '.join([t[0] if isinstance(t, tuple) else str(t) for t in profile['favorite_topics'][:3]])}")
                            
                            if facts_parts:
                                result = "\n".join(facts_parts)
                                logger.info(f"✅ [ADAPTER] Сформированы факты из профиля HybridMemory: {len(result)} символов")
                                return result
                    
                    # Альтернативно: поиск в памяти
                    if hasattr(long_memory, 'search_memory'):
                        search_results = long_memory.search_memory("личная информация", max_results=100)
                        if search_results:
                            facts_parts = []
                            for result in search_results:
                                content = result.get('content', '')
                                if content and len(content) > self.content_limits['min_fact_length']:
                                    facts_parts.append(f"• {content}")
                            
                            if facts_parts:
                                result = "\n".join(facts_parts[:self.max_facts] if self.max_facts != -1 else facts_parts)
                                logger.info(f"✅ [ADAPTER] Сформированы факты из поиска HybridMemory: {len(result)} символов")
                                return result
                except Exception as e:
                    logger.warning(f"⚠️ [ADAPTER] HybridMemory long_memory failed: {e}")
            
            # Вариант 3: Попытка получить данные напрямую
            if hasattr(self.memory_manager, 'get_user_profile'):
                try:
                    profile = self.memory_manager.get_user_profile()
                    if profile:
                        facts_parts = []
                        if profile.get('name'):
                            facts_parts.append(f"• Имя: {profile['name']}")
                        if profile.get('age'):
                            facts_parts.append(f"• Возраст: {profile['age']} лет")
                        if profile.get('interests'):
                            facts_parts.append(f"• Интересы: {', '.join(profile['interests'])}")
                        
                        if facts_parts:
                            result = "\n".join(facts_parts)
                            logger.info(f"✅ [ADAPTER] Сформированы факты из direct profile: {len(result)} символов")
                            return result
                except Exception as e:
                    logger.warning(f"⚠️ [ADAPTER] direct get_user_profile failed: {e}")
            
            logger.warning(f"❌ [ADAPTER] Не удалось получить долгосрочные факты для {user_id}")
            logger.info(f"❌ [ADAPTER] Доступные атрибуты memory_manager: {[attr for attr in dir(self.memory_manager) if not attr.startswith('_')]}")
            return None
            
        except Exception as e:
            logger.warning(f"❌ [ADAPTER] Ошибка получения долгосрочных фактов: {e}")
            return None
    
    def _get_semantic_context(self, user_id: str, query: str) -> Optional[str]:
        """Получает семантический контекст по запросу с кэшированием"""
        try:
            # Проверяем кэш
            cache_key = self._get_cache_key(user_id, "semantic", query[:50])
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
                
            logger.info(f"🔍 [ADAPTER] Получаем семантический контекст для {user_id}, запрос: {query[:self.content_limits['log_preview_length']]}...")
                 
            if hasattr(self.memory_manager, 'long_term') and self.memory_manager.long_term:
                logger.info(f"🔍 [ADAPTER] long_term найден для семантического поиска")
                
                try:
                    # Оптимизированный поиск с таймаутом
                    relevant_docs = self._search_memory_with_timeout(
                        query=query,
                        limit=self.max_semantic_results,
                        timeout=2.0  # Еще меньший таймаут для семантического поиска
                    )
                    
                    logger.info(f"🔍 [ADAPTER] Семантический поиск вернул {len(relevant_docs) if relevant_docs else 0} документов")
                    
                    if relevant_docs:
                        context_parts = []
                        for doc in relevant_docs:
                            content = doc.get('content', '')
                            logger.info(f"🔍 [ADAPTER] Обрабатываем документ: {content[:self.content_limits['log_preview_length']]}...")
                            
                            if content and len(content) > self.content_limits['min_document_length']:  
                                context_parts.append(f"📝 {content}")
                                logger.info(f"✅ [ADAPTER] Документ добавлен в семантический контекст")
                            else:
                                logger.info(f"⚠️ [ADAPTER] Документ отфильтрован (слишком короткий): {len(content)} символов")
                        
                        if context_parts:
                            result = "\n".join(context_parts)
                            logger.info(f"✅ [ADAPTER] Сформирован семантический контекст: {len(context_parts)} документов, {len(result)} символов")
                            
                            # Кэшируем результат
                            self._set_cached_result(cache_key, result)
                            return result
                        else:
                            logger.warning(f"⚠️ [ADAPTER] Документы найдены, но все отфильтрованы")
                    else:
                        logger.warning(f"⚠️ [ADAPTER] Релевантные документы не найдены")
                except Exception as e:
                    logger.warning(f"⚠️ [ADAPTER] long_term.search_memories failed: {e}")
            
            # Вариант 2: HybridMemory с long_memory
            if hasattr(self.memory_manager, 'long_memory') and self.memory_manager.long_memory:
                try:
                    long_memory = self.memory_manager.long_memory
                    logger.info(f"🔍 [ADAPTER] HybridMemory.long_memory найден для семантического поиска")
                    
                    if hasattr(long_memory, 'search_memory'):
                        search_results = long_memory.search_memory(query, max_results=3)
                        if search_results:
                            context_parts = []
                            for result in search_results:
                                content = result.get('content', '')
                                if content and len(content) > self.content_limits['min_document_length']:
                                    context_parts.append(f"📝 {content}")
                            
                            if context_parts:
                                result = "\n".join(context_parts)
                                logger.info(f"✅ [ADAPTER] Сформирован семантический контекст из HybridMemory: {len(result)} символов")
                                return result
                except Exception as e:
                    logger.warning(f"⚠️ [ADAPTER] HybridMemory semantic search failed: {e}")
            
            # Вариант 3: Простой поиск по всем доступным методам
            # ИСПРАВЛЕНО: Динамически находим доступные методы поиска
            search_methods = [method for method in dir(self.memory_manager) 
                            if 'search' in method.lower() and not method.startswith('_')]
            for method_name in search_methods:
                if hasattr(self.memory_manager, method_name):
                    try:
                        method = getattr(self.memory_manager, method_name)
                        if callable(method):
                            logger.info(f"🔍 [ADAPTER] Пытаемся использовать метод {method_name}")
                            
                            # Разные сигнатуры методов
                            if method_name == 'get_relevant_context':
                                results = method(query)
                            else:
                                results = method(query, limit=3)
                            
                            if results:
                                context_parts = []
                                for item in results:
                                    if isinstance(item, dict):
                                        content = item.get('content', '')
                                    elif isinstance(item, str):
                                        content = item
                                    else:
                                        content = str(item)
                                    
                                    if content and len(content) > self.content_limits['min_document_length']:
                                        context_parts.append(f"📝 {content}")
                                
                                if context_parts:
                                    result = "\n".join(context_parts)
                                    logger.info(f"✅ [ADAPTER] Сформирован семантический контекст через {method_name}: {len(result)} символов")
                                    return result
                    except Exception as e:
                        logger.warning(f"⚠️ [ADAPTER] {method_name} failed: {e}")
            
            logger.warning(f"❌ [ADAPTER] Не удалось получить семантический контекст для {user_id}")
            logger.info(f"❌ [ADAPTER] Доступные методы memory_manager: {[method for method in dir(self.memory_manager) if 'search' in method.lower() or 'context' in method.lower()]}")
            return None
            
        except Exception as e:
            logger.warning(f"❌ [ADAPTER] Ошибка получения семантического контекста: {e}")
            return None
    
    def _ensure_name_in_context(self, user_id: str, long_facts: Optional[str], semantic_context: Optional[str]) -> Optional[str]:
        """Упрощенный поиск - доверяем векторному поиску без хардкода"""
        try:
            # Не делаем специальный поиск имени - векторный поиск должен сам находить релевантные факты
            # Если векторный поиск не находит имя, значит его нет в памяти или поиск работает неправильно
            logger.info(f"🔍 [ADAPTER] Доверяем векторному поиску - не делаем специальный поиск имени")
            return None
            
        except Exception as e:
            logger.warning(f"❌ [ADAPTER] Ошибка в _ensure_name_in_context: {e}")
            return None
    
    def get_question_counter(self, user_id: str) -> int:
        """Получает счетчик вопросов для контроля частоты"""
        try:
            # Можно хранить в Redis или БД, пока используем простой счетчик
            # В реальной реализации здесь должна быть персистентность
            # Реализуем персистентный счетчик через memory_manager
            if hasattr(self.memory_manager, 'get_user_stats'):
                stats = self.memory_manager.get_user_stats()
                return stats.get('question_count', 0)
            return 0
        except Exception as e:
            logger.warning(f"Ошибка получения счетчика вопросов: {e}")
            return 0
    
    def can_ask_question(self, user_id: str) -> bool:
        """Проверяет, можно ли задать вопрос"""
        counter = self.get_question_counter(user_id)
        return (counter % 3 == 2)  # Вопрос каждый 3-й раз
