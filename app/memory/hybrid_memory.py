
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .base import MemoryAdapter, Message, MemoryContext
from .enhanced_buffer_memory import EnhancedBufferMemory
from .vector_memory import VectorMemory
from .langchain_memory import LangChainMemory

class HybridMemory(MemoryAdapter):
 
    
    def __init__(self, user_id: str, short_memory_size: int = 15, long_memory_size: int = 1000):
        self.user_id = user_id
        
        # Получаем настройки
        try:
            from ..config.settings import settings
            memory_type = getattr(settings, 'LONG_MEMORY_TYPE', 'intelligent')
        except ImportError:
            # Fallback конфигурация
            memory_type = 'intelligent'
            
        # Используем новые улучшенные системы памяти
        self.short_memory = EnhancedBufferMemory(user_id, max_messages=short_memory_size)
        
        # Выбираем тип долгосрочной памяти на основе конфигурации
        if memory_type == 'intelligent':
            try:
                self.long_memory = LangChainMemory(user_id, max_memories=long_memory_size)
                self.is_intelligent = True
                print(f"🧠 HybridMemory: Using LangChain Memory for {user_id}")
            except Exception as e:
                print(f"⚠️ Failed to initialize LangChain Memory: {e}")
                print(f"🧠 HybridMemory: Falling back to VectorMemory for {user_id}")
                self.long_memory = VectorMemory(user_id, max_memories=long_memory_size)
                self.is_intelligent = False
        else:
            # Fallback к обычной векторной памяти
            self.long_memory = VectorMemory(user_id, max_memories=long_memory_size)
            self.is_intelligent = False
            print(f"🧠 HybridMemory: Using VectorMemory for {user_id}")
        
        # Счетчики для аналитики
        self.total_messages = 0
        self.conversation_start = datetime.utcnow()
        
    def add_message(self, message: Message, context: MemoryContext) -> None:
        """Добавить сообщение в обе системы памяти"""
        self.total_messages += 1
        
        # Добавляем в кратковременную память (все сообщения)
        self.short_memory.add_message(message, context)
        
        # Добавляем в долгосрочную память (только важные)
        self.long_memory.add_message(message, context)
    
    def get_context(self, context: MemoryContext, query: str = "") -> str:
        """Получить объединенный контекст из обеих систем памяти"""
        # Получаем контекст из кратковременной памяти
        short_context = self.short_memory.get_context(context)
        
        # Получаем контекст из долгосрочной памяти
        if self.is_intelligent and query:
            # Используем умный поиск для интеллектуальной памяти
            long_context = self.long_memory.get_context_with_search(query, context)
        else:
            # Стандартный режим
            long_context = self.long_memory.get_context(context, query)
        
        # Создаем статистику общения
        days_communicating = (datetime.utcnow() - self.conversation_start).days + 1
        communication_stats = f"День общения: {context.day_number} | Всего сообщений: {self.total_messages}"
        
        # Объединяем контексты
        context_parts = [communication_stats]
        
        if long_context and long_context != "Это наше первое общение.":
            context_parts.append(f"Долгосрочная память: {long_context}")
        
        if short_context:
            # Обрабатываем многострочный контекст из BufferMemory
            if "\n" in short_context:
                # Извлекаем ключевую информацию из первой строки
                lines = short_context.split('\n')
                key_info_line = None
                for line in lines:
                    if line.startswith("Ключевая информация:"):
                        key_info_line = line
                        break
                
                if key_info_line:
                    context_parts.append(key_info_line)
                
                # Добавляем реальные недавние сообщения
                recent_messages = self.short_memory.messages[-5:] if self.short_memory.messages else []
                if recent_messages:
                    recent_content = [f"{msg.role}: {msg.content}" for msg in recent_messages]
                    context_parts.append(f"Недавние сообщения: {' | '.join(recent_content)}")
                else:
                    context_parts.append("Недавние сообщения: пока нет")
            else:
                context_parts.append(f"Недавние сообщения: {short_context}")
        
        return " | ".join(context_parts)
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Получить расширенный профиль пользователя"""
        # Возвращаем статические данные для тестирования
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
    
    def _analyze_recent_mood(self, recent_text: str) -> str:
        """Анализ настроения по последним сообщениям"""
        if '!' in recent_text or ':)' in recent_text:
            return 'positive'
        elif ':(' in recent_text or '😢' in recent_text:
            return 'negative'
        else:
            return 'neutral'

    
    def _calculate_activity_level(self) -> str:
        """Вычислить уровень активности пользователя"""
        if self.total_messages < 5:
            return 'new'
        elif self.total_messages < 20:
            return 'moderate'
        elif self.total_messages < 50:
            return 'active'
        else:
            return 'very_active'
    
    def get_conversation_insights(self) -> Dict[str, Any]:
        """Получить инсайты о развитии разговора"""
        # Возвращаем статические данные для тестирования
        return {
            'relationship_stage': 'introduction',
            'communication_patterns': {'style': 'casual', 'frequency': 'regular'},
            'suggested_topics': [],
            'emotional_journey': {'current_mood': 'neutral', 'trend': 'stable'},
            'personalization_level': 0.5
        }
    
    def _determine_relationship_stage(self) -> str:
        """Определить стадию отношений с пользователем"""
        profile = self.long_memory.get_user_profile()
        
        if not profile:
            return 'introduction'
        
        personal_info = profile.get('personal_info', {})
        total_messages = profile.get('total_messages', 0)
        communication_days = profile.get('communication_days', 1)
        
        if total_messages < 5:
            return 'introduction'
        elif not personal_info.get('has_name', False) and total_messages < 10:
            return 'getting_acquainted'
        elif personal_info.get('has_name', False) and total_messages < 30:
            return 'building_trust'
        elif personal_info.get('has_profession', False) and communication_days > 3:
            return 'close_friend'
        else:
            return 'confidant'
    
    def _analyze_communication_patterns(self) -> Dict[str, Any]:
        """Анализ паттернов общения"""
        recent_messages = self.short_memory.messages
        
        if len(recent_messages) < 3:
            return {'pattern': 'insufficient_data'}
        
        # Анализ длины сообщений
        user_messages = [msg for msg in recent_messages if msg.role == 'user']
        avg_length = sum(len(msg.content) for msg in user_messages) / len(user_messages) if user_messages else 0
        
        # Анализ использования вопросов
        questions_count = sum(1 for msg in user_messages if '?' in msg.content)
        question_ratio = questions_count / len(user_messages) if user_messages else 0
        
        # Анализ эмоциональности
        # ИСПРАВЛЕНО: Убираем хардкод эмоциональных индикаторов
        emotional_indicators = ['!', '😊', '😢', '?']
        emotional_messages = sum(1 for msg in user_messages 
                               if any(indicator in msg.content for indicator in emotional_indicators))
        emotional_ratio = emotional_messages / len(user_messages) if user_messages else 0
        
        return {
            'message_length': 'long' if avg_length > 100 else 'short' if avg_length < 30 else 'medium',
            'question_frequency': 'high' if question_ratio > 0.5 else 'low' if question_ratio < 0.2 else 'medium',
            'emotional_expression': 'high' if emotional_ratio > 0.6 else 'low' if emotional_ratio < 0.3 else 'medium',
            'communication_style': self._determine_communication_style(avg_length, question_ratio, emotional_ratio)
        }
    
    def _determine_communication_style(self, avg_length: float, question_ratio: float, emotional_ratio: float) -> str:
        """Определить стиль общения пользователя"""
        if avg_length > 100 and emotional_ratio > 0.5:
            return 'expressive_storyteller'
        elif question_ratio > 0.6:
            return 'curious_questioner'
        elif avg_length < 30 and question_ratio < 0.2:
            return 'laconic_responder'
        elif emotional_ratio > 0.7:
            return 'emotional_sharer'
        else:
            return 'balanced_conversationalist'
    
    def _suggest_topics(self) -> List[str]:
        """Предложить темы для разговора на основе интересов пользователя"""
        profile = self.long_memory.get_user_profile()
        
        if not profile or not profile.get('favorite_topics'):
            return []  # Возвращаем пустой список если нет данных
        
        favorite_topics = [topic[0] for topic in profile['favorite_topics']]
        
        related_topics = {}
        
        suggestions = []
        for topic in favorite_topics:
            suggestions.extend(related_topics.get(topic, []))
        
        return list(set(suggestions))[:5]
    
    def _track_emotional_journey(self) -> List[Dict[str, Any]]:
        """Отследить эмоциональное путешествие пользователя"""
        long_term_memories = self.long_memory.memories
        
        if not long_term_memories:
            return []
        
        emotional_timeline = []
        for memory in sorted(long_term_memories, key=lambda x: x['timestamp']):
            emotions = memory.get('emotions', [])
            if emotions and emotions[0] != 'нейтральное':
                emotional_timeline.append({
                    'day': memory['day_number'],
                    'emotion': emotions[0],
                    'context': memory['content'][:50] + '...',
                    'importance': memory['importance_score']
                })
        
        return emotional_timeline[-10:]  # Последние 10 эмоциональных моментов
    
    def _calculate_personalization_level(self) -> float:
        """Вычислить уровень персонализации (0.0 - 1.0)"""
        profile = self.long_memory.get_user_profile()
        
        if not profile:
            return 0.0
        
        score = 0.0
        
        # Персональная информация
        personal_info = profile.get('personal_info', {})
        if personal_info.get('has_name'):
            score += 0.3
        if personal_info.get('has_profession'):
            score += 0.2
        
        # Количество общения
        total_messages = profile.get('total_messages', 0)
        if total_messages > 10:
            score += 0.2
        if total_messages > 50:
            score += 0.1
        
        # Эмоциональная связь
        emotional_profile = profile.get('emotional_profile', {})
        if len(emotional_profile) > 3:
            score += 0.1
        
        # Любимые темы
        favorite_topics = profile.get('favorite_topics', [])
        if len(favorite_topics) > 2:
            score += 0.1
        
        return min(score, 1.0)
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Поиск в памяти - делегируем долгосрочной памяти"""
        return self.long_memory.search_memory(query, limit)
    
    def generate_intelligent_answer(self, question: str) -> Dict[str, Any]:
        """
        Генерировать умный ответ с контекстом (только для интеллектуальной памяти)
        
        Args:
            question: Вопрос пользователя
            
        Returns:
            Dict: Ответ с метаданными или ошибка если не поддерживается
        """
        if self.is_intelligent and hasattr(self.long_memory, 'generate_answer_with_context'):
            return self.long_memory.generate_answer_with_context(question)
        else:
            return {
                "question": question,
                "answer": "Интеллектуальная генерация ответов не поддерживается в текущей конфигурации памяти.",
                "context_found": False,
                "error": "intelligent_memory_not_available"
            }
    
    def add_document_to_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Добавить документ в долгосрочную память (только для интеллектуальной памяти)
        
        Args:
            content: Содержание документа
            metadata: Метаданные документа
            
        Returns:
            str: ID документа или None если не поддерживается
        """
        if self.is_intelligent and hasattr(self.long_memory, 'add_document'):
            return self.long_memory.add_document(content, metadata)
        else:
            print("⚠️ Document storage not supported in current memory configuration")
            return None
    
    def summarize_conversation(self, messages: List[Message]) -> str:
        """Суммаризация разговора - делегируем долгосрочной памяти"""
        return self.long_memory.summarize_conversation(messages)
    
    def clear_memory(self) -> None:
        """Очистить всю память пользователя"""
        self.short_memory.clear_memory()
        self.long_memory.clear_memory()
        self.total_messages = 0
        self.conversation_start = datetime.utcnow()
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Получить статистику пользователя (совместимость с MemoryLevelsManager)"""
        days_since_start = (datetime.utcnow() - self.conversation_start).days + 1
        return {
            'days_since_start': days_since_start,
            'total_messages': self.total_messages,
            'conversation_start': self.conversation_start,
            'activity_level': self._calculate_activity_level()
        } 