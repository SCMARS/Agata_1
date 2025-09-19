"""
Message Controller - управление структурой и частотой сообщений
"""
import re
import random
from typing import List, Dict, Any, Tuple
from datetime import datetime

class MessageController:
    """
    Контроллер для управления:
    - Частотой вопросов
    - Разбиением длинных сообщений
    - Добавлением пауз и задержек
    - Эмоциональной окраской
    """
    
    def __init__(self, max_message_length: int = 150, question_frequency: int = 3):
        self.max_message_length = max_message_length
        self.question_frequency = question_frequency  
        self.question_counter = 0
        self.conversation_topics = []  
        self.last_questions = []  
        
        # Паттерны для разбиения текста
        self.split_patterns = [
            r'[.!?]+\s+',  # По окончанию предложений
            r',\s+(?=\w+)',  # По запятым перед значимыми словами
            r'\s+(?=но|однако|при этом|кроме того|кстати)',  # По союзам
            r'\s+(?=\d+\.)',  # Перед нумерованными списками
        ]
        
        # Эмоциональные маркеры для пауз
        self.pause_triggers = {
            'размышление': ['хм', 'думаю', 'размышляю', 'кажется'],
            'удивление': ['ого', 'вау', 'невероятно', 'поразительно'],
            'эмоция': ['!', 'очень', 'сильно', 'невероятно'],
            'вопрос': ['?', 'интересно', 'а что если', 'может быть']
        }
    
    def process_message(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Основная функция обработки сообщения
        
        Возвращает:
        {
            'parts': List[str],  # Разбитые части сообщения
            'has_question': bool,  # Есть ли вопрос в сообщении
            'delays_ms': List[int]  # Задержки между частями в мс
        }
        """
        # Извлекаем темы из текущего сообщения
        current_topics = self._extract_conversation_topics(content)
        for topic in current_topics:
            if topic not in self.conversation_topics:
                self.conversation_topics.append(topic)
        
        # Сохраняем только последние 10 тем
        if len(self.conversation_topics) > 10:
            self.conversation_topics = self.conversation_topics[-10:]
        
        # Проверяем есть ли уже вопросы в оригинальном контенте
        has_existing_question = '?' in content
        
        # Определяем нужно ли добавить вопрос
        should_add_question = self._should_add_question(context)
        
        final_content = content
        final_has_question = has_existing_question
        
        # Добавляем вопрос только если:
        # 1. Пришло время для вопроса по счетчику
        # 2. В оригинальном тексте нет вопроса
        if should_add_question and not has_existing_question:
            contextual_question = self._generate_contextual_question(context)
            final_content = f"{content} {contextual_question}"
            final_has_question = True
            print(f"🔍 MessageController: Добавлен вопрос: {contextual_question}")
        elif has_existing_question:
            print(f"🔍 MessageController: Вопрос уже есть в тексте")
        else:
            print(f"🔍 MessageController: Вопрос НЕ добавлен (счетчик: {self.question_counter})")
        
        # Разбиваем сообщение на части если оно слишком длинное
        if len(final_content) > self.max_message_length:
            print(f"🔄 Разбиваем сообщение длиной {len(final_content)} символов")
            parts = self._split_long_message(final_content)
            print(f"🔄 Результат: {len(parts)} частей")
        else:
            parts = [final_content]
        
        # Рассчитываем задержки
        delays = self._calculate_delays(parts, context)
        
        return {
            'parts': parts,
            'has_question': final_has_question,
            'delays_ms': delays
        }
    
    def _extract_conversation_topics(self, content: str) -> List[str]:
        """Извлечь темы из контента сообщения"""
        topics = []
        content_lower = content.lower()
        
        # Определяем основные темы
        topic_keywords = {
            'работа': ['работа', 'профессия', 'карьера', 'коллеги', 'проект', 'офис', 'начальник'],
            'семья': ['семья', 'родители', 'мама', 'папа', 'жена', 'муж', 'дети', 'сын', 'дочь'],
            'хобби': ['хобби', 'увлечения', 'спорт', 'музыка', 'игры', 'чтение', 'фотография'],
            'здоровье': ['здоровье', 'самочувствие', 'болезнь', 'врач', 'лечение', 'спорт'],
            'путешествия': ['путешествие', 'отпуск', 'страна', 'город', 'поездка', 'отдых'],
            'образование': ['учеба', 'университет', 'курсы', 'изучение', 'знания', 'экзамен'],
            'отношения': ['друзья', 'отношения', 'любовь', 'свидание', 'знакомство'],
            'планы': ['планы', 'цели', 'мечты', 'будущее', 'хочу', 'собираюсь']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                topics.append(topic)
        
        return topics

    def _should_add_question(self, context: Dict[str, Any]) -> bool:
        """Определить, нужно ли добавить вопрос с учетом частоты"""
        self.question_counter += 1
        
        print(f"🔍 MessageController: Счетчик вопросов: {self.question_counter}/{self.question_frequency}")
        
        # СТРОГОЕ ПРАВИЛО: только каждые N сообщений
        if self.question_counter >= self.question_frequency:
            self.question_counter = 0
            print(f"🔍 MessageController: ВРЕМЯ для вопроса (сброс счетчика)")
            return True
        
        print(f"🔍 MessageController: НЕ время для вопроса (счетчик: {self.question_counter})")
        return False

    def _generate_contextual_question(self, context: Dict[str, Any]) -> str:
        """Сгенерировать вопрос на основе тем предыдущих разговоров"""
        recent_topics = self.conversation_topics[-3:] if self.conversation_topics else []
        user_mood = context.get('recent_mood', 'neutral')
        
        # Избегаем повторения последних вопросов
        available_questions = []
        
        # Вопросы на основе недавних тем
        if 'работа' in recent_topics:
            questions = [
                "Как дела на работе?",
                "Есть ли интересные проекты сейчас?",
                "Как складываются отношения с коллегами?"
            ]
            available_questions.extend([q for q in questions if q not in self.last_questions])
        
        if 'семья' in recent_topics:
            questions = [
                "Как дела у близких?",
                "Что нового в семье?",
                "Как проводите время вместе?"
            ]
            available_questions.extend([q for q in questions if q not in self.last_questions])
        
        if 'хобби' in recent_topics:
            questions = [
                "Чем занимаешься в свободное время?",
                "Есть ли новые увлечения?",
                "Удается ли находить время для хобби?"
            ]
            available_questions.extend([q for q in questions if q not in self.last_questions])
        
        # Общие вопросы если нет специфических тем
        if not available_questions:
            general_questions = [
                "Как прошел день?",
                "Что планируешь на выходные?",
                "Есть ли что-то интересное, чем хочешь поделиться?",
                "Как настроение сегодня?",
                "Что тебя больше всего интересует в последнее время?"
            ]
            available_questions.extend([q for q in general_questions if q not in self.last_questions])
        
        # Выбираем случайный вопрос
        if available_questions:
            selected_question = random.choice(available_questions)
            
            # Сохраняем вопрос в историю (не более 5 последних)
            self.last_questions.append(selected_question)
            if len(self.last_questions) > 5:
                self.last_questions.pop(0)
            
            return selected_question
        
        return "Как дела?"
    
    async def _add_contextual_question(self, content: str, context: Dict[str, Any]) -> str:
        """Добавить контекстуальный вопрос к сообщению"""
        user_mood = context.get('recent_mood', 'neutral')
        relationship_stage = context.get('relationship_stage', 'introduction')
        favorite_topics = context.get('favorite_topics', [])
        
        # Вопросы в зависимости от настроения
        mood_questions = {
            'positive': [
                "А что тебя сегодня больше всего порадовало?",
                "Расскажи, что подняло тебе настроение?",
                "Что планируешь делать в таком хорошем настроении?"
            ],
            'negative': [
                "Хочешь поговорить о том, что тебя беспокоит?",
                "Может, расскажешь, что случилось?",
                "Как я могу тебя поддержать?"
            ],
            'stressed': [
                "Что помогает тебе расслабиться?",
                "Хочешь отвлечься и поговорить о чем-то приятном?",
                "Может, сделаем перерыв от забот?"
            ],
            'excited': [
                "Расскажи подробнее!",
                "Что тебя так вдохновило?",
                "Поделись своими эмоциями!"
            ]
        }
        
        # Вопросы в зависимости от стадии отношений
        stage_questions = {
            'introduction': [
                "А что тебе нравится делать в свободное время?",
                "Расскажи немного о себе?",
                "Что привело тебя сюда сегодня?"
            ],
            'getting_acquainted': [
                "Что для тебя важно в жизни?",
                "Есть ли у тебя любимые места или занятия?",
                "Что тебя вдохновляет?"
            ],
            'building_trust': [
                "Как ты обычно справляешься с трудностями?",
                "Что тебе помогает чувствовать себя лучше?",
                "О чем ты мечтаешь?"
            ],
            'close_friend': [
                "Что изменилось в твоей жизни за последнее время?",
                "Есть ли что-то, чем ты хотел бы поделиться?",
                "Как дела с тем, о чем мы говорили раньше?"
            ]
        }
        
        # Вопросы по любимым темам
        topic_questions = {
            'работа': ["Как дела на работе?", "Есть ли интересные проекты?"],
            'семья': ["Как твои близкие?", "Как дела в семье?"],
            'хобби': ["Чем занимаешься в последнее время?", "Есть ли новые увлечения?"],
            'планы': ["Какие у тебя планы?", "К чему стремишься?"]
        }
        
        # Выбираем подходящий вопрос
        questions = []
        
        # Добавляем вопросы по настроению
        if user_mood in mood_questions:
            questions.extend(mood_questions[user_mood])
        
        # Добавляем вопросы по стадии отношений
        if relationship_stage in stage_questions:
            questions.extend(stage_questions[relationship_stage])
        
        # Добавляем вопросы по темам
        for topic_data in favorite_topics[:2]:  # Берем топ-2 темы
            topic = topic_data[0] if isinstance(topic_data, tuple) else topic_data
            if topic in topic_questions:
                questions.extend(topic_questions[topic])
        
        if questions:
            question = random.choice(questions)
            # Добавляем вопрос в конец с небольшой паузой
            content += f" {question}"
        
        return content
    
    def _split_long_message(self, content: str) -> List[str]:
        """Умно разбить длинное сообщение на части"""
        if len(content) <= self.max_message_length:
            return [content]
        
        print(f"🔄 Разбиваем сообщение длиной {len(content)} символов")
        
        # Простое разбиение (временно упрощено)
        parts = []
        remaining = content
        
        while remaining and len(remaining) > self.max_message_length:
            # Пытаемся найти хорошее место для разбиения
            best_split = self._find_best_split_point(remaining, self.max_message_length)
            
            if best_split > 0:
                part = remaining[:best_split].strip()
                remaining = remaining[best_split:].strip()
            else:
                # Если не найдено хорошее место, разбиваем по длине
                part = remaining[:self.max_message_length].strip()
                remaining = remaining[self.max_message_length:].strip()
            
            if part:
                parts.append(part)
        
        # Добавляем оставшуюся часть
        if remaining:
            parts.append(remaining.strip())
        
        print(f"🔄 Результат: {len(parts)} частей")
        return parts
    
    async def _split_by_semantic_blocks(self, content: str) -> List[str]:
        """Разбить по смысловым блокам"""
        try:
            # Разбиваем по абзацам и предложениям
            blocks = []
            
            # Сначала по абзацам
            paragraphs = content.split('\n\n')
            
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                    
                # Если абзац короткий, добавляем целиком
                if len(paragraph) <= self.max_message_length:
                    blocks.append(paragraph)
                else:
                    # Разбиваем длинный абзац по предложениям
                    sentences = self._split_into_sentences(paragraph)
                    current_block = ""
                    
                    for sentence in sentences:
                        if len(current_block + " " + sentence) <= self.max_message_length:
                            current_block += (" " + sentence if current_block else sentence)
                        else:
                            if current_block:
                                blocks.append(current_block.strip())
                            current_block = sentence
                    
                    if current_block:
                        blocks.append(current_block.strip())
            
            return blocks if blocks else [content]  # Fallback если нет блоков
        except Exception as e:
            print(f"🔄 Ошибка семантического разбиения: {e}")
            return [content]  # Возвращаем оригинал при ошибке
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Разбить текст на предложения"""
        try:
            import re
            # Разбиваем по точкам, восклицательным и вопросительным знакам
            sentences = re.split(r'[.!?]+', text)
            
            result = []
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    result.append(sentence)
            
            return result if result else [text]
        except Exception as e:
            print(f"🔄 Ошибка разбиения на предложения: {e}")
            return [text]
    
    async def _split_long_block(self, content: str) -> List[str]:
        """Разбить длинный блок принудительно"""
        parts = []
        remaining = content
        
        while remaining and len(remaining) > self.max_message_length:
            # Пытаемся найти хорошее место для разбиения
            best_split = self._find_best_split_point(remaining, self.max_message_length)
            
            if best_split > 0:
                part = remaining[:best_split].strip()
                remaining = remaining[best_split:].strip()
            else:
                # Если не найдено хорошее место, разбиваем по длине
                part = remaining[:self.max_message_length].strip()
                remaining = remaining[self.max_message_length:].strip()
            
            if part:
                parts.append(part)
        
        # Добавляем оставшуюся часть
        if remaining:
            parts.append(remaining.strip())
        
        return parts
    
    def _find_best_split_point(self, text: str, max_length: int) -> int:
        """Найти лучшую точку разбиения текста"""
        # Ищем в пределах разумного окна от max_length
        search_window = min(max_length, len(text))
        search_start = max(0, search_window - 50)  # Ищем в последних 50 символах
        
        search_text = text[search_start:search_window]
        
        # Пытаемся найти разбиение по паттернам
        for pattern in self.split_patterns:
            matches = list(re.finditer(pattern, search_text))
            if matches:
                # Берем последнее совпадение
                last_match = matches[-1]
                return search_start + last_match.end()
        
        # Если паттерны не найдены, ищем пробел
        last_space = text.rfind(' ', search_start, search_window)
        if last_space > search_start:
            return last_space
        
        return 0  # Не найдено хорошее место для разбиения
    
    def _calculate_delays(self, parts: List[str], context: Dict[str, Any]) -> List[int]:
        """Вычислить задержки между частями сообщения"""
        delays = []
        
        for i, part in enumerate(parts):
            if i == 0:
                # Первая часть - базовая задержка для имитации "печатания"
                base_typing_delay = min(len(part) * 30, 2000)  # 30мс на символ, макс 2 сек
                delays.append(base_typing_delay)
                continue
            
            # Базовая задержка
            base_delay = 1000  # 1 секунда
            
            # Увеличиваем задержку в зависимости от содержания
            delay_multiplier = 1.0
            
            # Проверяем эмоциональные маркеры
            part_lower = part.lower()
            for trigger_type, triggers in self.pause_triggers.items():
                if any(trigger in part_lower for trigger in triggers):
                    if trigger_type == 'размышление':
                        delay_multiplier += 0.5
                    elif trigger_type == 'удивление':
                        delay_multiplier += 0.3
                    elif trigger_type == 'эмоция':
                        delay_multiplier += 0.4
                    elif trigger_type == 'вопрос':
                        delay_multiplier += 0.6
            
            # Учитываем длину части
            if len(part) > 100:
                delay_multiplier += 0.3
            
            # Учитываем знаки препинания
            if part.endswith('...'):
                delay_multiplier += 0.8
            elif part.endswith('!'):
                delay_multiplier += 0.2
            elif part.endswith('?'):
                delay_multiplier += 0.4
            
            # Случайная вариация ±20%
            random_factor = random.uniform(0.8, 1.2)
            
            final_delay = int(base_delay * delay_multiplier * random_factor)
            delays.append(final_delay)
        
        return delays
    
    def add_emotional_coloring(self, content: str, strategy: str, mood: str) -> str:
        """Добавить эмоциональную окраску в зависимости от стратегии и настроения"""
        
        # Эмодзи для разных стратегий
        strategy_emojis = {
            'caring': ['😊', '🤗', '💕', '☺️'],
            'playful': ['😄', '😉', '🙃', '😋'],
            'mysterious': ['🤔', '😏', '👀', '✨'],
            'reserved': ['🙂', '😌', '🤍']
        }
        
        # Эмодзи для настроений
        mood_emojis = {
            'positive': ['😊', '😄', '🌟', '✨'],
            'negative': ['🤗', '💙', '🌸', '☁️'],
            'excited': ['🎉', '😍', '🔥', '⭐'],
            'neutral': ['🙂', '😌', '🤍']
        }
        
        # ОТКЛЮЧЕНО: НЕ добавляем эмодзи согласно новым правилам
        # if random.random() < 0.3:  # 30% шанс добавить эмодзи
        #     emojis = strategy_emojis.get(strategy, ['😊'])
        #     if mood in mood_emojis:
        #         emojis.extend(mood_emojis[mood])
        #     
        #     emoji = random.choice(emojis)
        #     
        #     # Добавляем эмодзи в конец или в середину
        #     if random.random() < 0.7:  # 70% в конец
        #         content += f" {emoji}"
        # ОТКЛЮЧЕНО: НЕ добавляем эмодзи в середину текста
        # else:  # 30% в подходящее место в середине
        #     sentences = content.split('. ')
        #     if len(sentences) > 1:
        #         insert_pos = random.randint(0, len(sentences) - 1)
        #         sentences[insert_pos] += f" {emoji}"
        #         content = '. '.join(sentences)
        
        return content 