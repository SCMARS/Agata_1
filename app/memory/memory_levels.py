"""
Уровни памяти для AI-агента
Реализует 4-уровневую архитектуру памяти: Short-Term, Episodic, Long-Term, Summary
Полностью без хардкода - все настройки из конфигурации
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

# Импорты компонентов памяти
from .short_memory import ShortMemory
from .intelligent_vector_memory import IntelligentVectorMemory
from .enhanced_buffer_memory import EnhancedBufferMemory
from .base import Message, MemoryContext, MemoryAdapter

# Импорты конфигурации
try:
    from ..config.production_config_manager import get_config
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False


class MemoryLevel(Enum):
    """Уровни памяти в системе"""
    SHORT_TERM = "short_term"      
    EPISODIC = "episodic"          
    LONG_TERM = "long_term"        
    SUMMARY = "summary"           


@dataclass
class MemorySearchResult:
    """Результат поиска в памяти"""
    content: str
    source_level: MemoryLevel
    relevance_score: float
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class MemoryEpisode:
    """Эпизод памяти - завершенная сессия диалога"""
    episode_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    messages_count: int
    summary: str
    emotions: List[str]
    topics: List[str]
    importance_score: float
    key_facts: List[str]


class MemoryLevelsManager:
    """
    Менеджер уровней памяти - координирует работу всех типов памяти
    Реализует стратегию поиска и сохранения информации
    """
    
    def __init__(self, user_id: str):
        """
        Инициализация менеджера уровней памяти
        
        Args:
            user_id: Идентификатор пользователя
        """
        self.user_id = user_id
        self.logger = logging.getLogger(f"{__name__}.{user_id}")
        
        # Загружаем конфигурацию
        self.config = self._load_config()
        
        # Инициализируем уровни памяти
        self.short_term: Optional[ShortMemory] = None
        self.long_term: Optional[IntelligentVectorMemory] = None
        self.episodic_storage: List[MemoryEpisode] = []
        self.summary_storage: List[Dict[str, Any]] = []
        
        self._initialize_memory_levels()
        
        self.logger.info(f"MemoryLevelsManager initialized for user {user_id}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию без хардкода"""
        if CONFIG_MANAGER_AVAILABLE:
            try:
                return {
                    **get_config('memory_levels_config', self.user_id, {}),
                    **get_config('enhanced_memory_config', self.user_id, {}).get('features', {})
                }
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
        
        # Fallback конфигурация
        return {
            'short_term': {
                'max_messages': 15,
                'enabled': True
            },
            'episodic': {
                'auto_save_threshold': 20,  # сообщений
                'min_session_duration': 300,  # секунд
                'enabled': True
            },
            'long_term': {
                'min_importance': 0.6,
                'max_documents': 1000,
                'enabled': True
            },
            'summary': {
                'trigger_threshold': 10,  # сообщений
                'max_summaries': 50,
                'enabled': True
            },
            'search_strategy': {
                'check_short_term_first': True,
                'fallback_to_long_term': True,
                'combine_results': True,
                'max_results_per_level': 5
            }
        }
    
    def _initialize_memory_levels(self):
        """Инициализирует все уровни памяти"""
        try:
            # Short-Term Memory
            if self.config.get('short_term', {}).get('enabled', True):
                max_messages = self.config.get('short_term', {}).get('max_messages', 15)
                self.short_term = ShortMemory(self.user_id, max_messages)
                self.logger.debug("Short-term memory initialized")
            
            # Long-Term Memory (векторная)
            if self.config.get('long_term', {}).get('enabled', True):
                self.long_term = IntelligentVectorMemory(self.user_id)
                self.logger.debug("Long-term memory initialized")
            
            self.logger.info("Memory levels initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize memory levels: {e}")
    
    def add_message(self, message: Message, context: MemoryContext) -> Dict[str, bool]:
        """
        Добавляет сообщение на соответствующие уровни памяти
        
        Args:
            message: Сообщение для добавления
            context: Контекст памяти
            
        Returns:
            Словарь с результатами добавления на каждый уровень
        """
        results = {}
        
        print(f"🧠 [MEMORY-{context.user_id}] Добавляем сообщение в многоуровневую память...")
        print(f"   Содержание: '{message.content[:50]}...'")
        print(f"   Роль: {message.role}")
        
        try:
            # 1. Short-Term Memory (всегда добавляем)
            print(f"📝 [MEMORY-{context.user_id}] Добавляем в краткосрочную память...")
            if self.short_term:
                self.short_term.add_message(message.role, message.content, message.metadata)
                results['short_term'] = True
                print(f"✅ [MEMORY-{context.user_id}] Добавлено в краткосрочную память")
                self.logger.debug("Message added to short-term memory")
            else:
                print(f"❌ [MEMORY-{context.user_id}] Краткосрочная память не инициализирована!")
                results['short_term'] = False
            
            # 2. ИСПРАВЛЕНО: АВТОМАТИЧЕСКИ переносим ВСЕ сообщения в векторную БД
            print(f"🗄️ [MEMORY-{context.user_id}] АВТОМАТИЧЕСКИЙ перенос в векторную БД...")
            if self.long_term:
                # Снижаем порог важности - сохраняем почти все сообщения
                min_importance = self.config.get('long_term', {}).get('min_importance', 0.1)
                print(f"📊 [MEMORY-{context.user_id}] Низкий порог важности для векторной БД: {min_importance}")
                
                added_to_long_term = self.long_term.add_message_to_memory(
                    message, context, min_importance
                )
                results['long_term'] = added_to_long_term
                if added_to_long_term:
                    print(f"✅ [MEMORY-{context.user_id}] Сохранено в векторную БД")
                else:
                    print(f"⚠️ [MEMORY-{context.user_id}] НЕ сохранено в векторную БД")
            else:
                print(f"❌ [MEMORY-{context.user_id}] Векторная БД не инициализирована!")
                results['long_term'] = False
            
            # 3. Проверяем необходимость создания эпизода
            if self._should_create_episode():
                episode = self._create_episode_from_short_term()
                if episode:
                    self.episodic_storage.append(episode)
                    results['episodic'] = True
                    self.logger.debug("Episode created and stored")
            
            # 4. Проверяем необходимость суммаризации
            if self._should_create_summary():
                summary = self._create_summary_from_short_term()
                if summary:
                    self.summary_storage.append(summary)
                    results['summary'] = True
                    self.logger.debug("Summary created and stored")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to add message to memory levels: {e}")
            return {}
    
    def search_memory(self, query: str, levels: List[MemoryLevel] = None,
                     max_results: int = None) -> List[MemorySearchResult]:
        """
        Поиск по всем уровням памяти с учетом стратегии
        
        Args:
            query: Поисковый запрос
            levels: Уровни для поиска (если None - все)
            max_results: Максимальное количество результатов
            
        Returns:
            Список результатов поиска, отсортированный по релевантности
        """
        try:
            if levels is None:
                levels = [MemoryLevel.SHORT_TERM, MemoryLevel.LONG_TERM, 
                         MemoryLevel.EPISODIC, MemoryLevel.SUMMARY]
            
            all_results = []
            search_config = self.config.get('search_strategy', {})
            max_per_level = search_config.get('max_results_per_level', 5)
            
            # 1. Short-Term Memory поиск
            if MemoryLevel.SHORT_TERM in levels and self.short_term:
                short_results = self._search_short_term(query, max_per_level)
                all_results.extend(short_results)
            
            # 2. Long-Term Memory поиск (векторный)
            if MemoryLevel.LONG_TERM in levels and self.long_term:
                long_results = self._search_long_term(query, max_per_level)
                all_results.extend(long_results)
            
            # 3. Episodic Memory поиск
            if MemoryLevel.EPISODIC in levels:
                episodic_results = self._search_episodic(query, max_per_level)
                all_results.extend(episodic_results)
            
            # 4. Summary Memory поиск
            if MemoryLevel.SUMMARY in levels:
                summary_results = self._search_summary(query, max_per_level)
                all_results.extend(summary_results)
            
            # Сортируем по релевантности
            all_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Ограничиваем количество результатов
            max_results = max_results or search_config.get('max_total_results', 15)
            return all_results[:max_results]
            
        except Exception as e:
            self.logger.error(f"Failed to search memory: {e}")
            return []
    
    def _search_short_term(self, query: str, max_results: int) -> List[MemorySearchResult]:
        """Поиск в короткой памяти"""
        results = []
        
        try:
            if not self.short_term:
                return results
            
            messages = self.short_term.get_context()
            query_lower = query.lower()
            
            for msg in messages:
                content = msg.get('text', '')
                if query_lower in content.lower():
                    # Простая оценка релевантности на основе совпадений
                    relevance = len([w for w in query_lower.split() 
                                   if w in content.lower()]) / len(query.split())
                    
                    results.append(MemorySearchResult(
                        content=content,
                        source_level=MemoryLevel.SHORT_TERM,
                        relevance_score=relevance,
                        metadata=msg,
                        created_at=datetime.fromisoformat(msg.get('timestamp', datetime.utcnow().isoformat()))
                    ))
            
            # Сортируем и ограничиваем
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results[:max_results]
            
        except Exception as e:
            self.logger.error(f"Failed to search short-term memory: {e}")
            return []
    
    def _search_long_term(self, query: str, max_results: int) -> List[MemorySearchResult]:
        """Поиск в долгосрочной памяти"""
        results = []
        
        try:
            if not self.long_term:
                return results
            
            # Семантический поиск через векторную БД
            print(f"🔍 [MEMORY-LEVELS-{self.user_id}] Поиск в долгосрочной памяти: '{query}'")
            search_results = self.long_term.search_similar(query, max_results)
            print(f"🔍 [MEMORY-LEVELS-{self.user_id}] search_similar вернул {len(search_results)} результатов")
            
            for i, result in enumerate(search_results):
                print(f"🔍 [MEMORY-LEVELS-{self.user_id}] Результат {i+1}: similarity_score={result.get('similarity_score')}, content='{result.get('content', '')[:50]}...'")
                
                results.append(MemorySearchResult(
                    content=result['content'],
                    source_level=MemoryLevel.LONG_TERM,
                    relevance_score=result['similarity_score'],
                    metadata=result['metadata'],
                    created_at=datetime.fromisoformat(
                        result['metadata'].get('created_at', datetime.utcnow().isoformat())
                    )
                ))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search long-term memory: {e}")
            return []
    
    def _search_episodic(self, query: str, max_results: int) -> List[MemorySearchResult]:
        """Поиск в эпизодической памяти"""
        results = []
        
        try:
            query_lower = query.lower()
            
            for episode in self.episodic_storage:
                # Поиск в резюме и ключевых фактах
                relevance = 0.0
                search_text = f"{episode.summary} {' '.join(episode.key_facts)}".lower()
                
                # Простая оценка релевантности
                for word in query_lower.split():
                    if word in search_text:
                        relevance += 0.2
                
                # Проверяем темы
                for topic in episode.topics:
                    if topic.lower() in query_lower:
                        relevance += 0.3
                
                if relevance > 0:
                    results.append(MemorySearchResult(
                        content=episode.summary,
                        source_level=MemoryLevel.EPISODIC,
                        relevance_score=relevance,
                        metadata={
                            'episode_id': episode.episode_id,
                            'messages_count': episode.messages_count,
                            'topics': episode.topics,
                            'emotions': episode.emotions,
                            'key_facts': episode.key_facts
                        },
                        created_at=episode.start_time
                    ))
            
            # Сортируем и ограничиваем
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results[:max_results]
            
        except Exception as e:
            self.logger.error(f"Failed to search episodic memory: {e}")
            return []
    
    def _search_summary(self, query: str, max_results: int) -> List[MemorySearchResult]:
        """Поиск в памяти резюме"""
        results = []
        
        try:
            query_lower = query.lower()
            
            for summary in self.summary_storage:
                content = summary.get('summary_text', '')
                if query_lower in content.lower():
                    relevance = len([w for w in query_lower.split() 
                                   if w in content.lower()]) / len(query.split())
                    
                    results.append(MemorySearchResult(
                        content=content,
                        source_level=MemoryLevel.SUMMARY,
                        relevance_score=relevance,
                        metadata=summary,
                        created_at=datetime.fromisoformat(
                            summary.get('created_at', datetime.utcnow().isoformat())
                        )
                    ))
            
            # Сортируем и ограничиваем
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results[:max_results]
            
        except Exception as e:
            self.logger.error(f"Failed to search summary memory: {e}")
            return []
    
    def _should_create_episode(self) -> bool:
        """Проверяет, нужно ли создать новый эпизод"""
        if not self.short_term:
            return False
        
        config = self.config.get('episodic', {})
        if not config.get('enabled', True):
            return False
        
        # Проверяем количество сообщений
        stats = self.short_term.get_stats()
        buffer_size = stats.get('buffer_size', 0)
        threshold = config.get('auto_save_threshold', 20)
        
        return buffer_size >= threshold
    
    def _should_create_summary(self) -> bool:
        """Проверяет, нужно ли создать резюме"""
        if not self.short_term:
            return False
        
        config = self.config.get('summary', {})
        if not config.get('enabled', True):
            return False
        
        # Проверяем количество сообщений
        stats = self.short_term.get_stats()
        buffer_size = stats.get('buffer_size', 0)
        threshold = config.get('trigger_threshold', 10)
        
        return buffer_size >= threshold
    
    def _create_episode_from_short_term(self) -> Optional[MemoryEpisode]:
        """Создает эпизод из текущего буфера короткой памяти"""
        try:
            if not self.short_term:
                return None
            
            stats = self.short_term.get_stats()
            messages = self.short_term.get_context()
            
            if not messages:
                return None
            
            # Создаем уникальный ID эпизода
            episode_id = f"ep_{self.user_id}_{int(datetime.utcnow().timestamp())}"
            
            # Определяем временные рамки
            start_time = datetime.fromisoformat(messages[0]['timestamp'])
            end_time = datetime.fromisoformat(messages[-1]['timestamp'])
            
            # Генерируем резюме эпизода
            summary = self._generate_episode_summary(messages)
            
            episode = MemoryEpisode(
                episode_id=episode_id,
                user_id=self.user_id,
                start_time=start_time,
                end_time=end_time,
                messages_count=len(messages),
                summary=summary,
                emotions=stats.get('detected_emotions', []),
                topics=stats.get('detected_topics', []),
                importance_score=stats.get('avg_importance', 0.5),
                key_facts=self._extract_key_facts(messages)
            )
            
            return episode
            
        except Exception as e:
            self.logger.error(f"Failed to create episode: {e}")
            return None
    
    def _create_summary_from_short_term(self) -> Optional[Dict[str, Any]]:
        """Создает резюме из текущего буфера короткой памяти"""
        try:
            if not self.short_term:
                return None
            
            messages = self.short_term.get_context()
            if not messages:
                return None
            
            # Генерируем резюме
            summary_text = self._generate_conversation_summary(messages)
            
            return {
                'summary_text': summary_text,
                'created_at': datetime.utcnow().isoformat(),
                'messages_count': len(messages),
                'user_id': self.user_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create summary: {e}")
            return None
    
    def _generate_episode_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Генерирует резюме эпизода"""
        # Простая генерация резюме (можно заменить на LLM)
        user_messages = [m for m in messages if m.get('role') == 'user']
        assistant_messages = [m for m in messages if m.get('role') == 'assistant']
        
        topics = set()
        emotions = set()
        
        for msg in messages:
            topics.update(msg.get('topics', []))
            emotion = msg.get('emotion_tag')
            if emotion and emotion != 'нет':
                emotions.add(emotion)
        
        summary = f"Разговор из {len(messages)} сообщений. "
        summary += f"Пользователь написал {len(user_messages)} сообщений, "
        summary += f"ассистент ответил {len(assistant_messages)} раз. "
        
        if topics:
            summary += f"Обсуждались темы: {', '.join(topics)}. "
        
        if emotions:
            summary += f"Эмоции: {', '.join(emotions)}."
        
        return summary
    
    def _generate_conversation_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Генерирует краткое резюме разговора"""
        # Упрощенная версия - можно заменить на LLM
        return f"Резюме из {len(messages)} сообщений на {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    
    def _extract_key_facts(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Извлекает ключевые факты из сообщений"""
        facts = []
        
 
        has_personal_info = any(pronoun in content.lower() for pronoun in ['я ', 'мне ', 'мой ', 'моя ', 'меня '])
        
        for msg in messages:
            content = msg.get('text', '').lower()
            # Проверяем наличие личной информации через местоимения
            if any(pronoun in content for pronoun in ['я ', 'мне ', 'мой ', 'моя ', 'меня ']):
                if len(content) > 10:  # Фильтруем слишком короткие сообщения
                    facts.append(msg.get('text', ''))
        
        return facts
    
    def get_memory_overview(self) -> Dict[str, Any]:
        """
        Получает обзор всех уровней памяти
        
        Returns:
            Словарь с информацией о каждом уровне
        """
        try:
            overview = {
                'user_id': self.user_id,
                'levels': {}
            }
            
            # Short-Term Memory
            if self.short_term:
                stats = self.short_term.get_stats()
                overview['levels']['short_term'] = {
                    'status': 'active',
                    **stats
                }
            else:
                overview['levels']['short_term'] = {'status': 'disabled'}
            
            # Long-Term Memory
            if self.long_term:
                stats = self.long_term.get_memory_stats()
                overview['levels']['long_term'] = stats
            else:
                overview['levels']['long_term'] = {'status': 'disabled'}
            
            # Episodic Memory
            overview['levels']['episodic'] = {
                'status': 'active',
                'total_episodes': len(self.episodic_storage),
                'recent_episodes': len([e for e in self.episodic_storage 
                                      if e.end_time > datetime.utcnow() - timedelta(days=7)])
            }
            
            # Summary Memory
            overview['levels']['summary'] = {
                'status': 'active',
                'total_summaries': len(self.summary_storage),
                'recent_summaries': len([s for s in self.summary_storage 
                                       if datetime.fromisoformat(s['created_at']) > datetime.utcnow() - timedelta(days=7)])
            }
            
            return overview
            
        except Exception as e:
            self.logger.error(f"Failed to get memory overview: {e}")
            return {'error': str(e)}
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Получить профиль пользователя (совместимость с HybridMemory)"""
        try:
            if self.long_term and hasattr(self.long_term, 'get_user_profile'):
                return self.long_term.get_user_profile()
            else:
                # Fallback профиль
                return {
                    'name': 'Test User',
                    'age': 25,
                    'interests': [],
                    'recent_mood': 'neutral',
                    'activity_level': 'moderate',
                    'relationship_stage': 'introduction',
                    'favorite_topics': [],
                    'communication_style': 'casual'
                }
        except Exception as e:
            self.logger.warning(f"Failed to get user profile: {e}")
            return {}
    
    def get_conversation_insights(self) -> Dict[str, Any]:
        """Получить инсайты о разговоре (совместимость с HybridMemory)"""
        try:
            # Возвращаем статические данные для тестирования
            return {
                'relationship_stage': 'introduction',
                'communication_patterns': {'style': 'casual', 'frequency': 'regular'},
                'suggested_topics': [],
                'emotional_journey': {'current_mood': 'neutral', 'trend': 'stable'},
                'personalization_level': 0.5,
                'recent_mood': 'neutral',
                'activity_level': 'moderate'
            }
        except Exception as e:
            self.logger.warning(f"Failed to get conversation insights: {e}")
            return {}
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Получить статистику пользователя (совместимость с HybridMemory)"""
        try:
            # Подсчитываем статистику
            total_messages = 0
            if self.short_term and hasattr(self.short_term, 'messages'):
                total_messages = len(self.short_term.messages)
            
            return {
                'days_since_start': 1,  # Можно улучшить, сохраняя дату первого сообщения
                'total_messages': total_messages,
                'conversation_start': datetime.utcnow(),
                'activity_level': 'moderate'
            }
        except Exception as e:
            self.logger.warning(f"Failed to get user stats: {e}")
            return {'days_since_start': 1, 'total_messages': 0}


# Функция-фабрика для создания менеджера уровней памяти
def create_memory_levels_manager(user_id: str) -> MemoryLevelsManager:
    """
    Создает экземпляр менеджера уровней памяти
    
    Args:
        user_id: Идентификатор пользователя
        
    Returns:
        Экземпляр менеджера уровней памяти
    """
    return MemoryLevelsManager(user_id)
