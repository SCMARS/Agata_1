"""
Daily Questions Generator - генератор повседневных вопросов
"""
import random
import logging
from typing import List, Dict, Any
from datetime import datetime
from .living_chat_config_loader import living_chat_config

logger = logging.getLogger(__name__)

class DailyQuestionsGenerator:
    """Генератор повседневных вопросов для живого общения"""
    
    def __init__(self):
        self.config = living_chat_config
        self.time_greetings = self.config.get_time_greetings()
        self.time_ranges = self.config.get_time_ranges()
        self.communication_style = self.config.get_communication_style()
        
        # Инициализируем OpenAI анализатор
        import os
        from .openai_text_analyzer import OpenAITextAnalyzer
        
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.openai_analyzer = OpenAITextAnalyzer(api_key)
            logger.info("OpenAI анализатор для вопросов инициализирован")
        else:
            self.openai_analyzer = None
            logger.warning("OpenAI API ключ не найден, используется fallback режим")
    
    def get_time_based_question(self, stage: int, conversation_context: Dict[str, Any] = None) -> str:
        """Возвращает вопрос в зависимости от времени суток и этапа"""
        
        # Если есть OpenAI анализатор и контекст, используем его
        if self.openai_analyzer and conversation_context:
            try:
                logger.info(f"🤖 [OPENAI] Генерируем вопрос для этапа {stage}")
                logger.info(f"   🎭 Тон беседы: {conversation_context.get('conversation_tone', 'unknown')}")
                logger.info(f"   😊 Настроение: {conversation_context.get('user_mood', 'unknown')}")
                question = self.openai_analyzer.suggest_question(conversation_context, stage)
                logger.info(f"   💡 Сгенерирован вопрос: '{question}'")
                return question
            except Exception as e:
                logger.error(f"❌ [OPENAI] Ошибка генерации вопроса: {e}")
        
        # Fallback к конфигурации
        current_hour = datetime.now().hour
        current_weekday = datetime.now().weekday()  # 0 = Monday, 6 = Sunday
        
        # Определяем время суток
        time_of_day = self._get_time_of_day(current_hour)
        
        logger.info(f"⏰ [DAILY_QUESTIONS] Текущее время: {current_hour}:xx ({time_of_day})")
        logger.info(f"⏰ [DAILY_QUESTIONS] День недели: {current_weekday} (0=Пн, 6=Вс)")
        logger.info(f"⏰ [DAILY_QUESTIONS] Этап: {stage}")
        
        # Получаем вопросы для этапа
        stage_questions = self.config.get_daily_questions(stage)
        logger.info(f"⏰ [DAILY_QUESTIONS] Вопросов для этапа {stage}: {len(stage_questions)}")
        
        # Добавляем контекстные вопросы в зависимости от времени
        contextual_questions = self._get_contextual_questions(time_of_day, current_weekday)
        logger.info(f"⏰ [DAILY_QUESTIONS] Контекстных вопросов для {time_of_day}: {len(contextual_questions)}")
        
        # Объединяем все вопросы
        all_questions = stage_questions + contextual_questions
        logger.info(f"⏰ [DAILY_QUESTIONS] Всего доступных вопросов: {len(all_questions)}")
        
        # Выбираем случайный вопрос
        if all_questions:
            selected_question = random.choice(all_questions)
            logger.info(f"⏰ [DAILY_QUESTIONS] Выбран вопрос: '{selected_question}'")
            return selected_question
        else:
            logger.warning(f"⏰ [DAILY_QUESTIONS] Нет доступных вопросов, используем fallback")
            return "как дела?"
    
    def _get_time_of_day(self, hour: int) -> str:
        """Определяет время суток из конфигурации"""
        for time_name, (start, end) in self.time_ranges.items():
            if start <= end:  # Обычный диапазон (например, 6-12)
                if start <= hour < end:
                    return time_name
            else:  # Переход через полночь (например, 22-6)
                if hour >= start or hour < end:
                    return time_name
        return "day"  # По умолчанию
    
    def _get_contextual_questions(self, time_of_day: str, weekday: int) -> List[str]:
        """Возвращает контекстные вопросы из конфигурации"""
        questions = []
        
        # Вопросы по времени суток из конфигурации
        time_questions = self.config.get_emotions(f"{time_of_day}_questions")
        if time_questions:
            questions.extend(time_questions)
        
        # Вопросы по дню недели из конфигурации
        weekday_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        weekday_name = weekday_names[weekday]
        weekday_questions = self.config.get_emotions(f"{weekday_name}_questions")
        if weekday_questions:
            questions.extend(weekday_questions)
        
        return questions
    
    def get_greeting(self) -> str:
        """Возвращает приветствие в зависимости от времени суток"""
        current_hour = datetime.now().hour
        time_of_day = self._get_time_of_day(current_hour)
        return self.time_greetings.get(time_of_day, "привет")
    
    def get_emotional_expression(self, emotion_type: str = "positive") -> str:
        """Возвращает эмоциональное выражение из конфигурации"""
        emotions = self.config.get_emotions(emotion_type)
        if emotions:
            return random.choice(emotions)
        return "круто!"
    
    def should_use_emoji(self) -> bool:
        """Определяет, нужно ли использовать эмодзи"""
        return self.communication_style.get("use_emojis", True)
    
    def should_use_parentheses(self) -> bool:
        """Определяет, нужно ли использовать скобки"""
        return self.communication_style.get("use_parentheses", True)
    
    def should_use_contractions(self) -> bool:
        """Определяет, нужно ли использовать сокращения"""
        return self.communication_style.get("use_contractions", True)
    
    def get_max_emoji_per_message(self) -> int:
        """Возвращает максимальное количество эмодзи на сообщение"""
        return self.communication_style.get("max_emoji_per_message", 2)

# Глобальный экземпляр генератора
daily_questions_generator = DailyQuestionsGenerator()
