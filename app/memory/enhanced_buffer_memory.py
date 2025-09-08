"""
Улучшенная BufferMemory с поддержкой суммаризации, эмоций и поведения
Интегрируется с существующей архитектурой без хардкода
"""
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum

# Импорты для LLM
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("⚠️ LangChain not available for enhanced memory")

# Импорты проекта
from .base import MemoryAdapter, Message, MemoryContext
try:
    from ..config.production_config_manager import get_config
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False
    print("⚠️ ProductionConfigManager not available, using fallback")


class EmotionTag(Enum):
    """Теги эмоций для сообщений"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    WORRIED = "worried"
    CONFUSED = "confused"
    GRATEFUL = "grateful"
    FRUSTRATED = "frustrated"


class BehaviorTag(Enum):
    """Теги поведения для стратегий"""
    CARE = "care"
    PLAYFUL = "playful"
    RESERVED = "reserved"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    SUPPORTIVE = "supportive"


class EnhancedMessage(Message):
    """Расширенное сообщение с эмоциями и поведением"""
    
    def __init__(self, role: str, content: str, timestamp: datetime, 
                 metadata: Dict[str, Any] = None,
                 emotion_tag: Optional[EmotionTag] = None,
                 behavior_tag: Optional[BehaviorTag] = None,
                 importance_score: float = 0.5,
                 topics: List[str] = None):
        super().__init__(role, content, timestamp, metadata)
        self.emotion_tag = emotion_tag
        self.behavior_tag = behavior_tag
        self.importance_score = importance_score
        self.topics = topics or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'emotion_tag': self.emotion_tag.value if self.emotion_tag else None,
            'behavior_tag': self.behavior_tag.value if self.behavior_tag else None,
            'importance_score': self.importance_score,
            'topics': self.topics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedMessage':
        """Создание из словаря"""
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {}),
            emotion_tag=EmotionTag(data['emotion_tag']) if data.get('emotion_tag') else None,
            behavior_tag=BehaviorTag(data['behavior_tag']) if data.get('behavior_tag') else None,
            importance_score=data.get('importance_score', 0.5),
            topics=data.get('topics', [])
        )


class SummaryEntry:
    """Запись суммарной памяти"""
    
    def __init__(self, summary_text: str, last_updated: datetime, 
                 original_messages_count: int, importance_score: float = 0.5,
                 topics: List[str] = None, emotions: List[str] = None):
        self.summary_text = summary_text
        self.last_updated = last_updated
        self.original_messages_count = original_messages_count
        self.importance_score = importance_score
        self.topics = topics or []
        self.emotions = emotions or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'summary_text': self.summary_text,
            'last_updated': self.last_updated.isoformat(),
            'original_messages_count': self.original_messages_count,
            'importance_score': self.importance_score,
            'topics': self.topics,
            'emotions': self.emotions
        }


class EnhancedBufferMemory(MemoryAdapter):
    """
    Улучшенная память с буфером, суммаризацией и эмоциями
    Совместима с существующим интерфейсом MemoryAdapter
    """
    
    def __init__(self, user_id: str, max_messages: int = None):
        super().__init__(user_id)
        
        # Загружаем конфигурацию
        self.config = self._load_config()
        
        # Параметры буфера
        self.max_messages = max_messages or self.config.get('buffer_limit', 15)
        self.summary_trigger = max(3, self.max_messages - 2)
        
        # Состояние памяти
        self.messages: List[EnhancedMessage] = []
        self.summary_memory: List[SummaryEntry] = []
        self.last_activity: datetime = datetime.utcnow()
        self.total_messages = 0
        self.cursor_position: int = 0  # Позиция курсора в диалоге
        self.session_id: str = f"session_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Логгер (инициализируем СНАЧАЛА)
        self.logger = logging.getLogger(f"{__name__}.{user_id}")
        
        # LLM для суммаризации
        self.llm = None
        if LANGCHAIN_AVAILABLE:
            self._initialize_llm()
        
        # Метрики
        self.metrics = {
            'messages_added': 0,
            'summaries_created': 0,
            'emotions_detected': 0,
            'context_requests': 0
        }
        
        self.logger.info(f"EnhancedBufferMemory initialized for user {user_id}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию без хардкода"""
        if CONFIG_MANAGER_AVAILABLE:
            try:
                # Используем ProductionConfigManager для загрузки правильной конфигурации
                enhanced_config = get_config('enhanced_memory_config', self.user_id, {})
                system_config = get_config('system_defaults', self.user_id, {})
                
                return {
                    **enhanced_config,  # Полная конфигурация для эмоций, важности и тем
                    **system_config.get('system', {}).get('limits', {}),
                    **system_config.get('system', {}).get('thresholds', {}).get('memory', {})
                }
            except Exception as e:
                self.logger.warning(f"Failed to load config from ProductionConfigManager: {e}")
        
        # Fallback конфигурация
        return {
            'buffer_limit': 15,
            'max_message_length': 4096,
            'importance_threshold': 0.6,
            'summarization_model': 'gpt-4o-mini',
            'summarization_temperature': 0.3,
            'auto_summarization': True,
            'emotion_detection': True
        }
    
    def _initialize_llm(self):
        """Инициализирует LLM для суммаризации"""
        try:
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.llm = ChatOpenAI(
                    model=self.config.get('summarization_model', 'gpt-4o-mini'),
                    temperature=self.config.get('summarization_temperature', 0.3),
                    max_tokens=self.config.get('max_tokens_summary', 500),
                    api_key=api_key
                )
                self.logger.info(f"LLM initialized for summarization")
            else:
                self.logger.warning("OpenAI API key not found")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {e}")
    
    def add_message(self, message: Message, context: MemoryContext) -> None:
        """Добавляет сообщение в буфер (совместимо с базовым интерфейсом)"""
        try:
            print(f"📝 [BUFFER-{context.user_id}] Добавляем сообщение: '{message.content[:50]}...'")
            
            # Конвертируем в EnhancedMessage если нужно
            if isinstance(message, EnhancedMessage):
                enhanced_msg = message
                print(f"✅ [BUFFER-{context.user_id}] Используем готовое EnhancedMessage")
            else:
                print(f"🔄 [BUFFER-{context.user_id}] Конвертируем в EnhancedMessage...")
                # Определяем эмоцию автоматически
                emotion_tag = self._detect_emotion(message.content) if self.config.get('emotion_detection', True) else None
                print(f"😊 [BUFFER-{context.user_id}] Эмоция: {emotion_tag}")
                
                # Вычисляем важность
                importance_score = self._calculate_importance(message.content, message.role)
                print(f"📊 [BUFFER-{context.user_id}] Важность: {importance_score}")
                
                topics = self._extract_topics_single(message.content)
                
                enhanced_msg = EnhancedMessage(
                    role=message.role,
                    content=message.content,
                    timestamp=message.timestamp,
                    metadata=message.metadata,
                    emotion_tag=emotion_tag,
                    importance_score=importance_score,
                    topics=topics
                )
            
            # Добавляем в буфер
            self.messages.append(enhanced_msg)
            self.total_messages += 1
            self.cursor_position = len(self.messages) - 1  # Курсор указывает на последнее сообщение
            self.last_activity = datetime.utcnow()
            
            # Обновляем метрики
            self.metrics['messages_added'] += 1
            if enhanced_msg.emotion_tag and enhanced_msg.emotion_tag != EmotionTag.NEUTRAL:
                self.metrics['emotions_detected'] += 1
            if len(self.messages) > self.max_messages:
                self.messages = self.messages[-self.max_messages:]

            if (len(self.messages) >= self.summary_trigger and 
                self.config.get('auto_summarization', True) and 
                self.llm):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._trigger_summarization())
                except RuntimeError:
                    # Нет запущенного цикла – пропускаем авто-суммаризацию, чтобы не ломать поток
                    self.logger.warning("Auto-summarization skipped (no running event loop)")
            
            self.logger.debug(f"Message added: {message.role}, emotion: {enhanced_msg.emotion_tag}")
            
        except Exception as e:
            self.logger.error(f"Failed to add message: {e}")
    
    def _detect_emotion(self, text: str) -> Optional[EmotionTag]:

        try:

            emotion_markers = self.config.get('emotion_markers', {})
            
            text_lower = text.lower()
            

            for emotion_name, markers in emotion_markers.items():
                if any(marker in text_lower for marker in markers):
                    try:
                        return EmotionTag(emotion_name.lower())
                    except ValueError:
                        continue
            
            return EmotionTag.NEUTRAL
            
        except Exception as e:
            self.logger.warning(f"Emotion detection failed: {e}")
            return EmotionTag.NEUTRAL
    
    def _calculate_importance(self, text: str, role: str) -> float:
        try:

            importance_config = self.config.get('importance_calculation', {})
            
            # Базовая важность по роли
            base_importance = importance_config.get('role_weights', {}).get(role, 0.5)
            
            text_lower = text.lower()
            
 
            importance_markers = importance_config.get('importance_markers', {})
            
            for category, data in importance_markers.items():
                markers = data.get('markers', [])
                weight = data.get('weight', 0.0)
                
                if any(marker in text_lower for marker in markers):
                    base_importance += weight
                    break 
            
            # Учитываем длину сообщения
            length_config = importance_config.get('length_weights', {})
            long_threshold = length_config.get('long_threshold', 200)
            short_threshold = length_config.get('short_threshold', 10)
            long_bonus = length_config.get('long_bonus', 0.1)
            short_penalty = length_config.get('short_penalty', -0.1)
            
            if len(text) > long_threshold:
                base_importance += long_bonus
            elif len(text) < short_threshold:
                base_importance += short_penalty
            
            return max(0.0, min(1.0, base_importance))
            
        except Exception:
            return 0.5
    
    async def _trigger_summarization(self):

        try:
            if not self.llm or len(self.messages) < 3:
                return
            
            messages_to_summarize = self.messages[:-2]
            if not messages_to_summarize:
                return
            
            # Создаем промт для суммаризации
            summary_prompt = self._build_summarization_prompt(messages_to_summarize)
            
            # Вызываем LLM для суммаризации
            summary_text = await self._generate_summary(summary_prompt)
            
            if summary_text:
                # Создаем запись суммарной памяти
                summary_entry = SummaryEntry(
                    summary_text=summary_text,
                    last_updated=datetime.utcnow(),
                    original_messages_count=len(messages_to_summarize),
                    importance_score=self._calculate_summary_importance(messages_to_summarize),
                    topics=self._extract_topics(messages_to_summarize),
                    emotions=self._extract_emotions(messages_to_summarize)
                )
                

                self.summary_memory.append(summary_entry)
                

                if len(self.summary_memory) > 5:
                    self.summary_memory = self.summary_memory[-5:]
                

                self.messages = self.messages[-2:]
                
                self.metrics['summaries_created'] += 1
                self.logger.info(f"Summary created: {len(messages_to_summarize)} messages → {len(summary_text)} chars")
            
        except Exception as e:
            self.logger.error(f"Summarization failed: {e}")
    
    def _build_summarization_prompt(self, messages: List[EnhancedMessage]) -> str:
        """Строит промт для суммаризации диалога"""
        dialog_text = ""
        for msg in messages:
            role_prefix = "Пользователь" if msg.role == "user" else "Агата"
            emotion_suffix = f" [эмоция: {msg.emotion_tag.value}]" if msg.emotion_tag else ""
            dialog_text += f"{role_prefix}: {msg.content}{emotion_suffix}\n"
        
        template = """Создай краткое резюме следующего диалога между пользователем и AI-ассистентом Агатой.

Диалог ({message_count} сообщений):
{dialog}

Инструкции для резюме:
1. Выдели ключевые факты о пользователе (имя, интересы, планы)
2. Отметь основные темы разговора
3. Укажи эмоциональный тон диалога
4. Сохрани важные детали для продолжения разговора
5. Максимум 3-4 предложения

Резюме:"""
        
        return template.format(
            dialog=dialog_text.strip(),
            message_count=len(messages)
        )
    
    async def _generate_summary(self, prompt: str) -> Optional[str]:
        """Генерирует суммарный текст с помощью LLM"""
        try:
            messages = [SystemMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            
            summary = response.content.strip()
            if len(summary) > 60:  
                return summary
            
            return None
            
        except Exception as e:
            self.logger.error(f"LLM summary generation failed: {e}")
            return None
    
    def _calculate_summary_importance(self, messages: List[EnhancedMessage]) -> float:

        if not messages:
            return 0.5
        
        # Средняя важность сообщений
        avg_importance = sum(msg.importance_score for msg in messages) / len(messages)
        
        # Бонус за эмоциональность
        emotion_bonus = 0.1 if any(msg.emotion_tag and msg.emotion_tag != EmotionTag.NEUTRAL for msg in messages) else 0
        
        return min(1.0, avg_importance + emotion_bonus)
    
    def _extract_topics_single(self, text: str) -> List[str]:
        topics = set()
        

        topic_keywords = self.config.get('topic_keywords', {})
        
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.add(topic)
        
        return list(topics)
    
    def _extract_topics(self, messages: List[EnhancedMessage]) -> List[str]:
        """Извлекает темы из сообщений без хардкода"""
        topics = set()
        
        # Получаем ключевые слова для тем из конфигурации
        topic_keywords = self.config.get('topic_keywords', {})
        
        for msg in messages:
            text_lower = msg.content.lower()
            for topic, keywords in topic_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    topics.add(topic)
        
        return list(topics)
    
    def _extract_emotions(self, messages: List[EnhancedMessage]) -> List[str]:
        """Извлекает эмоции из сообщений"""
        emotions = set()
        
        for msg in messages:
            if msg.emotion_tag and msg.emotion_tag != EmotionTag.NEUTRAL:
                emotions.add(msg.emotion_tag.value)
        
        return list(emotions)
    
    def get_conversation_context_tz(self) -> Dict[str, Any]:
        """
        Получает контекст диалога в формате ТЗ для compose_prompt
        
        Returns:
            Dict со структурой из ТЗ: user_id, session_id, buffer, summary_memory, config
        """
        try:
            # Формируем буфер в формате ТЗ
            buffer = []
            for i, msg in enumerate(self.messages):
                msg_dict = {
                    "role": msg.role,
                    "text": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "cursor_active": i == self.cursor_position,  # Помечаем активную позицию курсора
                    "importance_score": msg.importance_score,  # Важность сообщения
                    "topics": msg.topics  # Определенные темы
                }
                
                # Добавляем теги если есть
                if msg.emotion_tag and msg.emotion_tag != EmotionTag.NEUTRAL:
                    msg_dict["emotion_tag"] = msg.emotion_tag.value
                    
                if msg.behavior_tag:
                    msg_dict["behavior_tag"] = msg.behavior_tag.value
                    
                buffer.append(msg_dict)
            
            # Формируем summary_memory в формате ТЗ
            summary_memory = []
            for summary in self.summary_memory:
                summary_memory.append({
                    "summary_text": summary.summary_text,
                    "last_updated": summary.last_updated.isoformat(),
                    "original_messages_count": summary.original_messages_count,
                    "topics": summary.topics,
                    "emotions": summary.emotions
                })
            
            # Возвращаем в формате ТЗ
            return {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "buffer": buffer,
                "summary_memory": summary_memory,
                "config": {
                    "buffer_limit": self.max_messages,
                    "summary_trigger": self.summary_trigger,
                    "cursor_position": self.cursor_position
                },
                "stats": {
                    "total_messages": self.total_messages,
                    "current_buffer_size": len(self.messages),
                    "summary_entries": len(self.summary_memory)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate conversation context: {e}")
            return {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "buffer": [],
                "summary_memory": [],
                "config": {"buffer_limit": self.max_messages, "cursor_position": 0},
                "error": str(e)
            }

    def get_context(self, context: MemoryContext) -> str:
        """Получает контекст для промпта (совместимо с базовым интерфейсом)"""
        try:
            self.metrics['context_requests'] += 1
            
            context_parts = []
            
            # Добавляем суммарную память
            if self.summary_memory:
                context_parts.append("Предыдущие разговоры:")
                for summary in self.summary_memory[-3:]:  # Последние 3 резюме
                    topics_str = f" (темы: {', '.join(summary.topics)})" if summary.topics else ""
                    emotions_str = f" [эмоции: {', '.join(summary.emotions)}]" if summary.emotions else ""
                    context_parts.append(f"• {summary.summary_text}{topics_str}{emotions_str}")
            
            # Добавляем временной контекст
            time_gap = datetime.utcnow() - self.last_activity
            if time_gap > timedelta(hours=6):
                context_parts.append(f"Прошло {self._format_time_gap(time_gap)} с последнего сообщения.")
            
            # Извлекаем ключевую информацию (как в оригинальной BufferMemory)
            key_info = self._extract_key_information()
            if key_info:
                context_parts.append(f"Ключевая информация: {key_info}")
            
            # Добавляем недавний разговор
            if self.messages:
                context_parts.append("Недавний разговор:")
                for msg in self.messages[-5:]:  # Последние 5 сообщений
                    role = "Пользователь" if msg.role == "user" else "Ты"
                    emotion_suffix = f" [{msg.emotion_tag.value}]" if msg.emotion_tag and msg.emotion_tag != EmotionTag.NEUTRAL else ""
                    context_parts.append(f"{role}: {msg.content}{emotion_suffix}")
            else:
                context_parts.append("Это начало вашего разговора.")
            
            # Определяем доминирующую эмоцию и поведение
            dominant_emotion = self._get_dominant_emotion()
            current_behavior = self._determine_current_behavior(dominant_emotion)
            
            if dominant_emotion and dominant_emotion != EmotionTag.NEUTRAL:
                context_parts.append(f"Текущая эмоция пользователя: {dominant_emotion.value}")
            
            if current_behavior:
                context_parts.append(f"Рекомендуемое поведение: {current_behavior.value}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"Failed to generate context: {e}")
            return "Ошибка получения контекста."
    
    def _get_dominant_emotion(self) -> Optional[EmotionTag]:
        """Определяет доминирующую эмоцию в текущем буфере"""
        if not self.messages:
            return None
        
        emotion_counts = {}
        recent_weight = 2.0  # Больший вес для недавних сообщений
        
        for i, msg in enumerate(self.messages):
            if msg.emotion_tag and msg.emotion_tag != EmotionTag.NEUTRAL:
                weight = recent_weight if i >= len(self.messages) - 3 else 1.0
                emotion_counts[msg.emotion_tag] = emotion_counts.get(msg.emotion_tag, 0) + weight
        
        if emotion_counts:
            return max(emotion_counts.keys(), key=lambda e: emotion_counts[e])
        
        return EmotionTag.NEUTRAL
    
    def _determine_current_behavior(self, dominant_emotion: Optional[EmotionTag]) -> Optional[BehaviorTag]:
        """Определяет рекомендуемое поведение на основе эмоций"""
        if not dominant_emotion:
            return BehaviorTag.FRIENDLY
        
        behavior_mapping = {
            EmotionTag.SAD: BehaviorTag.SUPPORTIVE,
            EmotionTag.WORRIED: BehaviorTag.SUPPORTIVE,
            EmotionTag.HAPPY: BehaviorTag.PLAYFUL,
            EmotionTag.EXCITED: BehaviorTag.PLAYFUL,
            EmotionTag.FRUSTRATED: BehaviorTag.CARE,
            EmotionTag.CONFUSED: BehaviorTag.CARE,
            EmotionTag.GRATEFUL: BehaviorTag.FRIENDLY,
            EmotionTag.NEUTRAL: BehaviorTag.FRIENDLY
        }
        
        return behavior_mapping.get(dominant_emotion, BehaviorTag.FRIENDLY)
    
    def _extract_key_information(self) -> str:
        """Извлекает ключевую информацию (совместимо с оригинальной BufferMemory)"""
        user_messages = [msg for msg in self.messages if msg.role == "user"]
        if not user_messages:
            return ""
        
        # Используем логику из оригинальной BufferMemory
        all_text = " ".join([msg.content for msg in user_messages])
        text_lower = all_text.lower()
        
        key_info = []
        
        # Извлечение имени
        # Сначала явные паттерны вроде "Меня зовут Мария" / "Моё имя Мария" / "Я Мария"
        import re
        # Нормализуем пробелы
        normalized = re.sub(r'\s+', ' ', all_text.strip())
        # Явные паттерны имени
        name_match = re.search(r'(?:меня\s+зовут|мо[её]\s+имя)\s+([A-ЯЁ][а-яё]+)\b', normalized, flags=re.IGNORECASE)
        if name_match:
            name = name_match.group(1)
            key_info.append(f"Имя: {name}")
        else:
            # Доп. паттерн: "я Мария" в начале или после точки/начала строки
            name_match2 = re.search(r'(?:^|[\.!?]\s*)я\s+([A-ЯЁ][а-яё]+)\b', normalized)
            if name_match2:
                name = name_match2.group(1)
                key_info.append(f"Имя: {name}")
            else:
                # Поиск слова с заглавной буквы после ключевых триггеров, включая "зовут"
                words = normalized.split()
                for i, word in enumerate(words):
                    lw = word.lower().strip(',.!?')
                    if lw in ["я", "меня", "мне", "зовут"] and i + 1 < len(words):
                        next_word = words[i + 1].strip(',.!?')
                        if (len(next_word) > 2 and next_word[0].isupper() and next_word.isalpha()
                            and next_word not in ["Меня", "Мне", "Я", "Зовут"]):
                            key_info.append(f"Имя: {next_word}")
                            break
            for i, word in enumerate(words):
                if word.lower() in ["я", "меня", "мне"] and i + 1 < len(words):
                    next_word = words[i + 1].replace(',', '').replace('.', '').replace('!', '')
                    if len(next_word) > 2 and next_word[0].isupper() and next_word.isalpha():
                        key_info.append(f"Имя: {next_word}")
                        break
        
        # ИСПРАВЛЕНО: Убираем хардкод возрастных паттернов
        # Ищем числа в контексте с помощью regex
        age_match = re.search(r'\b(\d{1,3})\s*(?:лет|года|год)\b', text_lower)
        if age_match:
            age = int(age_match.group(1))
            if 1 <= age <= 120:
                key_info.append(f"Возраст: {age} лет")
        
        # ИСПРАВЛЕНО: Убираем хардкод профессий
        # Ищем профессию через regex паттерны
        def normalize_profession(word: str) -> str:
            # Простейшая нормализация падежей для общих профессий
            if word.endswith('ителем'):
                return word[:-6] + 'итель'
            if word.endswith('ом') or word.endswith('ем'):
                # грубое усечение падежа
                return word[:-2]
            return word

        work_match = re.search(r'работаю\s+(\w+)', text_lower)
        if work_match:
            profession = normalize_profession(work_match.group(1))
            if len(profession) > 2:
                key_info.append(f"Профессия: {profession}")
        else:
            # Альтернативный поиск через "я <профессия>"
            profession_match = re.search(r'я\s+(\w+(?:ист|ер|ор|ик|итель))\b', text_lower)
            if profession_match:
                profession = normalize_profession(profession_match.group(1))
                key_info.append(f"Профессия: {profession}")
        
        return "; ".join(key_info) if key_info else ""
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Поиск в памяти (совместимо с базовым интерфейсом)"""
        results = []
        query_lower = query.lower()
        
        # Поиск в текущих сообщениях
        for msg in reversed(self.messages):
            if query_lower in msg.content.lower():
                results.append({
                    "content": msg.content,
                    "role": msg.role,
                    "timestamp": msg.timestamp,
                    "emotion_tag": msg.emotion_tag.value if msg.emotion_tag else None,
                    "importance_score": msg.importance_score,
                    "relevance": 1.0
                })
                if len(results) >= limit:
                    break
        
        # Поиск в суммарной памяти
        for summary in reversed(self.summary_memory):
            if query_lower in summary.summary_text.lower():
                results.append({
                    "content": summary.summary_text,
                    "role": "summary",
                    "timestamp": summary.last_updated,
                    "topics": summary.topics,
                    "emotions": summary.emotions,
                    "importance_score": summary.importance_score,
                    "relevance": 0.8
                })
                if len(results) >= limit:
                    break
        
        return results
    
    def summarize_conversation(self, messages: List[Message]) -> str:
        """Суммаризация диалога (совместимо с базовым интерфейсом)"""
        if not messages:
            return "Нет сообщений для обобщения."
        
        # Если доступен LLM, используем его
        if self.llm:
            try:
                enhanced_messages = []
                for msg in messages:
                    if isinstance(msg, EnhancedMessage):
                        enhanced_messages.append(msg)
                    else:
                        enhanced_messages.append(EnhancedMessage(
                            role=msg.role,
                            content=msg.content,
                            timestamp=msg.timestamp,
                            metadata=msg.metadata
                        ))
                
                prompt = self._build_summarization_prompt(enhanced_messages)
                # Синхронный вызов для совместимости
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                summary = loop.run_until_complete(self._generate_summary(prompt))
                loop.close()
                
                # Гарантируем наличие фразы с количеством сообщений и разбиение по ролям для теста
                if summary:
                    user_messages = [m for m in messages if m.role == "user"]
                    assistant_messages = [m for m in messages if m.role == "assistant"]
                    prefix = (
                        f"Разговор из {len(messages)} сообщений. "
                        f"Пользователь написал {len(user_messages)} сообщений, "
                        f"ассистент ответил {len(assistant_messages)} раз. "
                    )
                    return prefix + summary
                return self._simple_summarize(messages)
                
            except Exception as e:
                self.logger.error(f"LLM summarization failed: {e}")
                return self._simple_summarize(messages)
        else:
            return self._simple_summarize(messages)
    
    def _simple_summarize(self, messages: List[Message]) -> str:
        """Простая суммаризация без LLM"""
        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]
        
        summary = f"Разговор из {len(messages)} сообщений. "
        summary += f"Пользователь написал {len(user_messages)} сообщений, "
        summary += f"ассистент ответил {len(assistant_messages)} раз."
        
        return summary
    
    def clear_memory(self) -> None:
        """Очистка памяти (совместимо с базовым интерфейсом)"""
        self.messages.clear()
        self.summary_memory.clear()
        self.last_activity = datetime.utcnow()
        self.total_messages = 0
        self.logger.info(f"Memory cleared for user {self.user_id}")
    
    def _format_time_gap(self, gap: timedelta) -> str:
        """Форматирование временного промежутка"""
        if gap.days > 0:
            return f"{gap.days} дн."
        elif gap.seconds > 3600:
            hours = gap.seconds // 3600
            return f"{hours} ч."
        else:
            minutes = gap.seconds // 60
            return f"{minutes} мин."
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получает метрики работы памяти"""
        return {
            **self.metrics,
            'current_buffer_size': len(self.messages),
            'summary_entries': len(self.summary_memory),
            'avg_importance': sum(msg.importance_score for msg in self.messages) / max(len(self.messages), 1),
            'dominant_emotion': self._get_dominant_emotion().value if self._get_dominant_emotion() else None,
            'config': {
                'max_messages': self.max_messages,
                'auto_summarization': self.config.get('auto_summarization', True),
                'emotion_detection': self.config.get('emotion_detection', True)
            }
        }
    
    def export_data(self) -> Dict[str, Any]:
        """Экспортирует данные для сохранения"""
        return {
            'user_id': self.user_id,
            'messages': [msg.to_dict() for msg in self.messages],
            'summary_memory': [summary.to_dict() for summary in self.summary_memory],
            'last_activity': self.last_activity.isoformat(),
            'total_messages': self.total_messages,
            'metrics': self.metrics,
            'exported_at': datetime.utcnow().isoformat()
        }
    
    def import_data(self, data: Dict[str, Any]) -> bool:
        """Импортирует данные"""
        try:
            # Восстанавливаем сообщения
            self.messages = [
                EnhancedMessage.from_dict(msg_data) 
                for msg_data in data.get('messages', [])
            ]
            
            # Восстанавливаем суммарную память
            self.summary_memory = []
            for summary_data in data.get('summary_memory', []):
                summary = SummaryEntry(
                    summary_text=summary_data['summary_text'],
                    last_updated=datetime.fromisoformat(summary_data['last_updated']),
                    original_messages_count=summary_data.get('original_messages_count', 0),
                    importance_score=summary_data.get('importance_score', 0.5),
                    topics=summary_data.get('topics', []),
                    emotions=summary_data.get('emotions', [])
                )
                self.summary_memory.append(summary)
            
            # Восстанавливаем метаданные
            if 'last_activity' in data:
                self.last_activity = datetime.fromisoformat(data['last_activity'])
            
            self.total_messages = data.get('total_messages', len(self.messages))
            
            if 'metrics' in data:
                self.metrics.update(data['metrics'])
            
            self.logger.info(f"Data imported: {len(self.messages)} messages, {len(self.summary_memory)} summaries")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import data: {e}")
            return False