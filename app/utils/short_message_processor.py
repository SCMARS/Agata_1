
import re
import logging
import os
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from .living_chat_config_loader import living_chat_config
from .openai_text_analyzer import OpenAITextAnalyzer
from .dynamic_content_generator import DynamicContentGenerator

logger = logging.getLogger(__name__)

class ShortMessageProcessor:
    
    def __init__(self):
        # Загружаем конфигурацию
        self.config = living_chat_config
        self.short_messages_config = self.config.get_short_messages_config()
        self.combination_patterns_config = self.config.get_combination_patterns()
        self.connectors_config = self.config.get_connectors()
        
        # Настройки из конфигурации
        self.max_wait_seconds = self.short_messages_config.get("max_wait_seconds", 30)
        self.short_message_threshold = self.short_messages_config.get("short_message_threshold", 50)
        self.quick_sequence_threshold = self.short_messages_config.get("quick_sequence_threshold", 5)
        
        self.user_sessions = {}  
        
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.openai_analyzer = OpenAITextAnalyzer(api_key)
            self.dynamic_generator = DynamicContentGenerator()
            logger.info("OpenAI анализатор і динамічний генератор ініціалізовані")
        else:
            self.openai_analyzer = None
            self.dynamic_generator = None
            logger.warning("OpenAI API ключ не найден, используется fallback режим")
        
        # Загружаем паттерны из конфигурации (fallback)
        self.combination_patterns = self._load_combination_patterns()
    
    def _load_combination_patterns(self) -> List[Tuple[str, str, str]]:
        """Загружает паттерны объединения из конфигурации"""
        patterns = []
        for pattern_config in self.combination_patterns_config:
            pattern1 = pattern_config.get("pattern1", "")
            pattern2 = pattern_config.get("pattern2", "")
            connector = pattern_config.get("connector", ", ")
            if pattern1 and pattern2:
                patterns.append((pattern1, pattern2, connector))
        return patterns
    
    def process_user_messages(self, user_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Обрабатывает короткие сообщения пользователя и объединяет их в контекст
        
        Args:
            user_id: ID пользователя
            messages: Список сообщений пользователя
            
        Returns:
            Dict с обработанным контекстом
        """
        if not messages:
            return {"combined_text": "", "message_count": 0, "is_short_sequence": False}
        
        # Получаем или создаем сессию пользователя
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "last_activity": datetime.now(),
                "message_buffer": [],
                "total_messages": 0
            }
        
        session = self.user_sessions[user_id]
        
        # Обновляем время последней активности
        session["last_activity"] = datetime.now()
        session["total_messages"] += len(messages)
        
        # Добавляем новые сообщения в буфер
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "").strip()
                if content:
                    session["message_buffer"].append({
                        "content": content,
                        "timestamp": datetime.now()
                    })
        
        # Очищаем старые сообщения (старше max_wait_seconds)
        cutoff_time = datetime.now() - timedelta(seconds=self.max_wait_seconds)
        session["message_buffer"] = [
            msg for msg in session["message_buffer"] 
            if msg["timestamp"] > cutoff_time
        ]
        
        # Объединяем сообщения
        combined_text = self._combine_messages(session["message_buffer"])
        
        # Определяем, является ли это короткой последовательностью
        is_short_sequence = self._is_short_sequence(session["message_buffer"])
        
        logger.info(f"🔄 [SHORT_MSG] Обработано {len(session['message_buffer'])} сообщений для пользователя {user_id}")
        logger.info(f"   📝 Исходные сообщения: {[msg['content'] for msg in session['message_buffer']]}")
        logger.info(f"   🔗 Объединенный текст: '{combined_text[:100]}{'...' if len(combined_text) > 100 else ''}'")
        logger.info(f"   ⚡ Короткая последовательность: {is_short_sequence}")
        
        return {
            "combined_text": combined_text,
            "message_count": len(session["message_buffer"]),
            "is_short_sequence": is_short_sequence,
            "original_messages": [msg["content"] for msg in session["message_buffer"]]
        }
    
    def _combine_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        Объединяет короткие сообщения в логический контекст
        """
        if not messages:
            return ""
        
        if len(messages) == 1:
            return messages[0]["content"]
        
        # Извлекаем тексты сообщений
        texts = [msg["content"] for msg in messages]
        
        # Пробуем объединить по паттернам
        combined = self._try_pattern_combination(texts)
        if combined:
            return combined
        
        # Если паттерны не сработали, объединяем логически
        return self._logical_combination(texts)
    
    def _try_pattern_combination(self, texts: List[str]) -> str:
        """
        Пытается объединить сообщения по паттернам (динамічно через OpenAI)
        """
        if len(texts) < 2:
            return ""
        
        # Використовуємо динамічний генератор замість хардкоду
        if self.dynamic_generator:
            try:
                # Генеруємо з'єднувач динамічно
                connector = self.dynamic_generator.generate_conversation_connectors(texts[0], texts[1])
                
                # Об'єднуємо з згенерованою зв'язкою
                if len(texts) == 2:
                    return f"{texts[0]} {connector} {texts[1]}"
                else:
                    combined_first_two = f"{texts[0]} {connector} {texts[1]}"
                    return f"{combined_first_two}. {' '.join(texts[2:])}"
            except Exception as e:
                logger.error(f"Помилка динамічної генерації з'єднувача: {e}")
        
        # Fallback до хардкоду якщо динамічна генерація не спрацювала
        for pattern1, pattern2, connector in self.combination_patterns:
            if (re.search(pattern1, texts[0].lower()) and 
                re.search(pattern2, texts[1].lower())):
                
                # Объединяем с конфигурируемой связкой
                if len(texts) == 2:
                    return f"{texts[0]}{connector}{texts[1].lower()}"
                else:
                    return f"{texts[0]}{connector}{texts[1].lower()}. {' '.join(texts[2:])}"
        
        return ""
    
    def _logical_combination(self, texts: List[str]) -> str:
        """
        Логически объединяет сообщения с учетом их типа
        """
        if len(texts) == 1:
            return texts[0]
        
        # Анализируем тип сообщений
        message_type = self._analyze_message_types(texts)
        logger.info(f"[SHORT_MSG] Тип сообщений: {message_type}")
        
        # Выбираем стратегию объединения
        if message_type == "split_sentence":
            return self._combine_split_sentence(texts)
        elif message_type == "sequential_questions":
            return self._combine_sequential_questions(texts)
        elif message_type == "different_topics":
            return self._combine_different_topics(texts)
        else:
            return self._combine_default(texts)
    
    def _analyze_message_types(self, texts: List[str]) -> str:
        """Анализирует тип сообщений для выбора стратегии объединения"""
        
        # Проверяем, является ли это разбитым предложением
        if self._is_split_sentence(texts):
            return "split_sentence"
        
        # Проверяем, есть ли несколько вопросов
        question_count = sum(1 for text in texts if text.strip().endswith('?'))
        if question_count > 1:
            return "sequential_questions"
        
        # Проверяем, разные ли темы
        if len(texts) > 2 and self._are_different_topics(texts):
            return "different_topics"
        
        return "default"
    
    def _is_split_sentence(self, texts: List[str]) -> bool:
        """Проверяет, является ли это одним разбитым предложением"""
        if len(texts) < 2:
            return False
        
        # Если первое сообщение не заканчивается знаком препинания
        first = texts[0].strip()
        if first.endswith(('.', '!', '?', ',')):
            return False
        
        # Если объединенное предложение короткое и естественное
        combined = " ".join(texts)
        return len(combined) < 120
    
    def _are_different_topics(self, texts: List[str]) -> bool:
        """Проверяет, касаются ли сообщения разных тем"""
        # Простая эвристика на основе ключевых слов
        all_words = []
        for text in texts:
            words = [w.lower() for w in text.split() if len(w) > 3]
            all_words.extend(words)
        
        unique_words = len(set(all_words))
        total_words = len(all_words)
        
        return unique_words > total_words * 0.7  # Много уникальных слов = разные темы
    
    def _combine_split_sentence(self, texts: List[str]) -> str:
        """Объединяет разбитое предложение естественно"""
        result = " ".join(texts)
        logger.info(f"[SHORT_MSG] Объединили разбитое предложение: '{result}'")
        return result
    
    def _combine_sequential_questions(self, texts: List[str]) -> str:
        """Объединяет последовательные вопросы"""
        result = texts[0]
        
        for i, text in enumerate(texts[1:], 1):
            if text.strip().endswith('?'):
                result += f" И {text.lower()}"
            else:
                result += f" {text}"
        
        logger.info(f"[SHORT_MSG] Объединили вопросы: '{result}'")
        return result
    
    def _combine_different_topics(self, texts: List[str]) -> str:
        """Объединяет сообщения с разными темами"""
        result = texts[0]
        
        for i, text in enumerate(texts[1:], 1):
            if i == 1:
                result += f" А еще {text.lower()}"
            else:
                result += f" И {text.lower()}"
        
        logger.info(f"[SHORT_MSG] Объединили разные темы: '{result}'")
        return result
    
    def _combine_default(self, texts: List[str]) -> str:
        """Обычное объединение с коннекторами"""
        result = texts[0]
        
        for i, text in enumerate(texts[1:], 1):
            previous_text = texts[i-1] if i > 0 else ""
            connector = self._get_connector(text, i == len(texts) - 1, previous_text)
            
            if connector:
                result += f" {connector} {text.lower()}"
            else:
                result += f" {text.lower()}"
        
        logger.info(f"[SHORT_MSG] Стандартное объединение: '{result}'")
        return result
    
    def _get_connector(self, text: str, is_last: bool, previous_text: str = "") -> str:
        """
        Определяет связку для объединения сообщений с помощью OpenAI
        """
        # Если есть OpenAI анализатор, используем его
        if self.openai_analyzer and previous_text:
            try:
                logger.info(f"🤖 [OPENAI] Генерируем связку для: '{previous_text}' -> '{text}'")
                connector = self.openai_analyzer.generate_connector(previous_text, text)
                logger.info(f"   🔗 Получена связка: '{connector}'")
                return connector
            except Exception as e:
                logger.error(f"❌ [OPENAI] Ошибка анализа связки: {e}")
        
        # Fallback к конфигурации
        text_lower = text.lower()
        
        # Получаем паттерны из конфигурации
        question_words = self.config.get_emotions("question_words")
        emotion_words = self.config.get_emotions("emotion_words")
        
        # Если сообщение начинается с вопроса
        if question_words and any(text_lower.startswith(word) for word in question_words):
            return self.connectors_config.get("question_start", "А")
        
        # Если сообщение начинается с эмоции
        if emotion_words and any(text_lower.startswith(word) for word in emotion_words):
            return self.connectors_config.get("emotion_start", "Кстати")
        
        # Получаем паттерны коротких ответов из конфигурации
        short_response_words = self.config.get_emotions("short_response_words")
        
        # Если сообщение короткое (1-2 слова) или содержит короткие ответы
        if (len(text.split()) <= 2 or 
            (short_response_words and any(text_lower.startswith(word) for word in short_response_words))):
            return self.connectors_config.get("short_message", "и")
        
        # Если это последнее сообщение
        if is_last:
            return self.connectors_config.get("last_message", "Кроме того")
        
        # По умолчанию
        return self.connectors_config.get("default", "А")
    
    def _is_short_sequence(self, messages: List[Dict[str, Any]]) -> bool:
        """
        Определяет, является ли последовательность короткой (из конфигурации)
        """
        if len(messages) < 2:
            return False
        
        # Проверяем, что все сообщения короткие (из конфигурации)
        all_short = all(len(msg["content"]) < self.short_message_threshold for msg in messages)
        
        # Проверяем, что сообщения идут подряд (из конфигурации)
        if len(messages) >= 2:
            time_diffs = []
            for i in range(1, len(messages)):
                diff = (messages[i]["timestamp"] - messages[i-1]["timestamp"]).total_seconds()
                time_diffs.append(diff)
            
            all_quick = all(diff < self.quick_sequence_threshold for diff in time_diffs)
        else:
            all_quick = True
        
        return all_short and all_quick
    
    def clear_user_session(self, user_id: str):
        """
        Очищает сессию пользователя
        """
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            logger.info(f"Очищена сессия пользователя {user_id}")
    
    def get_session_info(self, user_id: str) -> Dict[str, Any]:
        """
        Возвращает информацию о сессии пользователя
        """
        if user_id not in self.user_sessions:
            return {"message_count": 0, "last_activity": None}
        
        session = self.user_sessions[user_id]
        return {
            "message_count": len(session["message_buffer"]),
            "last_activity": session["last_activity"],
            "total_messages": session["total_messages"]
        }

# Глобальный экземпляр процессора
short_message_processor = ShortMessageProcessor()
