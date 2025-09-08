"""
Система контроля частоты вопросов Агаты
"""
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class QuestionController:
    """Контроллер частоты задаваемых вопросов"""
    
    def __init__(self, max_frequency: int = 3):
        """
        Args:
            max_frequency: Максимальная частота вопросов (каждое N-е сообщение)
        """
        self.max_frequency = max_frequency
        self.user_counters = {}  # user_id -> question_count
        self.user_history = {}   # user_id -> список последних тем
        
    def should_avoid_question(self, user_id: str) -> bool:
        """
        Проверяет, следует ли избегать вопросов (слишком часто задавались)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если следует избегать вопросов
        """
        if user_id not in self.user_counters:
            self.user_counters[user_id] = 0
            
        current_count = self.user_counters[user_id]
        
        # Избегаем вопросов, если недавно задавали (не каждое сообщение)
        should_avoid = (current_count % self.max_frequency) != (self.max_frequency - 1)
        
        logger.info(f"Вопросы для {user_id}: счетчик {current_count}, избегать={should_avoid}")
        return should_avoid
    
    def increment_counter(self, user_id: str):
        """Увеличивает счетчик сообщений для пользователя"""
        if user_id not in self.user_counters:
            self.user_counters[user_id] = 0
        self.user_counters[user_id] += 1
    
    def reset_counter(self, user_id: str):
        """Сбрасывает счетчик для пользователя (например, при новом цикле)"""
        self.user_counters[user_id] = 0
        logger.info(f"Счетчик вопросов сброшен для {user_id}")
    
    def generate_contextual_question(self, user_id: str, conversation_context: str, user_message: str) -> Optional[str]:
        """
        Генерирует контекстуальный вопрос на основе истории общения
        
        Args:
            user_id: ID пользователя
            conversation_context: Контекст разговора
            user_message: Последнее сообщение пользователя
            
        Returns:
            Вопрос или None если не удалось сгенерировать
        """
        # Анализируем контекст для выбора темы вопроса
        topics = self._extract_topics(conversation_context, user_message)
        
        # Получаем историю тем для этого пользователя
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        
        user_topics = self.user_history[user_id]
        
        # Выбираем тему, которую еще не обсуждали
        new_topics = [topic for topic in topics if topic not in user_topics[-5:]]  # Последние 5 тем
        
        if not new_topics and not topics:
            # Если нет тем, используем общие вопросы
            return self._get_general_question()
        
        topic = new_topics[0] if new_topics else topics[0]
        
        # Генерируем вопрос по теме
        question = self._generate_question_for_topic(topic, user_message)
        
        # Сохраняем тему в историю
        if topic not in user_topics:
            user_topics.append(topic)
            # Ограничиваем историю
            if len(user_topics) > 20:
                user_topics = user_topics[-20:]
            self.user_history[user_id] = user_topics
        
        return question
    
    def _extract_topics(self, context: str, user_message: str) -> List[str]:
        """Извлекает темы из контекста разговора"""
        topics = []
        
        # Объединяем контекст и сообщение
        full_text = f"{context} {user_message}".lower()
        
        # Словарь тем и ключевых слов
        topic_keywords = {
            'работа': ['работ', 'карьер', 'офис', 'коллег', 'проект', 'начальник', 'зарплат'],
            'хобби': ['хобби', 'увлеч', 'свободн', 'досуг', 'интерес', 'любл'],
            'семья': ['семь', 'родител', 'мама', 'папа', 'брат', 'сестр', 'жена', 'муж', 'дети'],
            'путешествия': ['путешеств', 'поездк', 'отпуск', 'страна', 'город', 'море', 'горы'],
            'спорт': ['спорт', 'тренировк', 'зал', 'бег', 'футбол', 'плаван', 'фитнес'],
            'еда': ['еда', 'готов', 'ресторан', 'кухн', 'рецепт', 'вкусн'],
            'здоровье': ['здоровь', 'врач', 'болен', 'лечен', 'самочувств'],
            'планы': ['план', 'будущ', 'мечт', 'цел', 'хоч', 'собираюсь'],
            'настроение': ['настроен', 'чувств', 'эмоци', 'радост', 'грустн', 'устал'],
            'учеба': ['учеб', 'универ', 'курс', 'экзамен', 'знания', 'изуча']
        }
        
        # Ищем совпадения
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in full_text:
                    topics.append(topic)
                    break
        
        return list(set(topics))  # Убираем дубликаты
    
    def _generate_question_for_topic(self, topic: str, user_message: str) -> str:
        """Генерирует вопрос для конкретной темы"""
        
        questions_by_topic = {
            'работа': [
                "Как дела на работе?",
                "Что интересного на работе происходит?",
                "Как складываются отношения с коллегами?",
                "Есть какие-то новые проекты?",
                "Нравится ли тебе то, чем занимаешься?"
            ],
            'хобби': [
                "Какие у тебя хобби?",
                "Чем увлекаешься в свободное время?",
                "Есть ли что-то новое, что хотел бы попробовать?",
                "Что приносит тебе радость?",
                "Как проводишь выходные?"
            ],
            'семья': [
                "Как дела у семьи?",
                "Часто ли видишься с родными?",
                "Расскажи о своей семье",
                "Какие у вас семейные традиции?",
                "Как родители?"
            ],
            'путешествия': [
                "Куда хотел бы поехать?",
                "Какое самое запоминающееся путешествие было?",
                "Планируешь куда-то съездить?",
                "Что больше нравится - море или горы?",
                "В какой стране хотел бы побывать?"
            ],
            'спорт': [
                "Каким спортом занимаешься?",
                "Часто ли тренируешься?",
                "Что мотивирует заниматься спортом?",
                "Есть спортивные цели?",
                "Какой вид спорта нравится больше всего?"
            ],
            'планы': [
                "Какие планы на будущее?",
                "О чем мечтаешь?",
                "Что хотел бы изменить в жизни?",
                "Какие цели ставишь перед собой?",
                "Что планируешь на ближайшее время?"
            ],
            'настроение': [
                "Как настроение?",
                "Что радует в последнее время?",
                "Как дела с самочувствием?",
                "Что поднимает тебе настроение?",
                "Как справляешься со стрессом?"
            ]
        }
        
        import random
        questions = questions_by_topic.get(topic, self._get_general_questions())
        return random.choice(questions)
    
    def _get_general_question(self) -> str:
        """Возвращает общий вопрос"""
        general_questions = self._get_general_questions()
        import random
        return random.choice(general_questions)
    
    def _get_general_questions(self) -> List[str]:
        """Список общих вопросов"""
        return [
            "Как дела?",
            "Что нового?",
            "Как проводишь время?",
            "Что интересного происходит?",
            "Как настроение?",
            "Чем занимаешься?",
            "Что планируешь на выходные?",
            "Есть что-то, чем хотел бы поделиться?",
            "Как прошел день?",
            "Что радует в последнее время?"
        ]
    
    def get_question_stats(self, user_id: str) -> Dict:
        """Возвращает статистику вопросов для пользователя"""
        return {
            'question_count': self.user_counters.get(user_id, 0),
            'topics_discussed': len(self.user_history.get(user_id, [])),
            'recent_topics': self.user_history.get(user_id, [])[-5:]
        }

# Глобальный экземпляр контроллера
question_controller = QuestionController()
