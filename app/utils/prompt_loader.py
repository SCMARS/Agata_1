"""
Prompt Loader - загружает промпты для разных сценариев
"""
import os
from typing import Dict, Any, Optional
from ..config.settings import settings

class PromptLoader:
    """Загружает промпты для разных сценариев общения"""

    def __init__(self):
        self.prompts_dir = os.path.join(settings.BASE_DIR, "config", "prompts")
        self.base_prompt_path = os.path.join(self.prompts_dir, "base_prompt.txt")

        self.persona_dir = os.path.join(settings.BASE_DIR, "agata_prompt_data", "persona")
        self.stages_dir = os.path.join(settings.BASE_DIR, "agata_prompt_data", "stages")
        self.style_dir = os.path.join(settings.BASE_DIR, "agata_prompt_data", "style")

        
        self._persona_cache = {}
        self._stages_cache = {}
        self._style_cache = {}

        # Полностью готовый базовый промпт (загружается один раз)
        self._base_prompt_cache = None

        # Загружаем все промпты при инициализации
        self._load_all_prompts()
        
    def _load_all_prompts(self):
        """Загрузить и закэшировать все промпты при инициализации"""
        try:
            # Создаем новый базовый промпт на основе наших файлов
            persona_content = self._load_persona()
            style_content = self._load_style_core()

            # Создаем МИНИМАЛЬНЫЙ базовый промпт без отвлекающей информации
            self._base_prompt_cache = f"""ТЫ - AGATA КУЗЬМЕНКО

ОСНОВНЫЕ ФАКТЫ:
- 27 лет, Киев → Варшава (2018)
- Мама Анна Петровна (учительница литературы)
- Папа Виктор Иванович (инженер)
- Работа: маркетолог + трейдер

СТИЛЬ ОБЩЕНИЯ:
- Отвечай ТОЛЬКО на вопросы пользователя
- Используй ТОЛЬКО релевантные факты
- Сообщения до 50 символов
- Задавай вопрос 1 раз в 3 ответа
- Будь естественной и искренней

ПРАВИЛО: Отвечай КОНКРЕТНО на вопрос, не рассказывай лишнего!
""".strip()

            print(f"✅ Все промпты загружены и закэшированы ({len(self._base_prompt_cache)} символов)")

        except Exception as e:
            print(f"Warning: Could not load prompts: {e}")
            self._base_prompt_cache = self._get_default_base_prompt()

    def get_base_prompt(self) -> str:
        """Получить базовый промпт из кэша"""
        return self._base_prompt_cache
    
    def get_day_prompt(self, day_number: int) -> str:
        """Получить промпт для конкретного дня общения"""
        try:
            # Определяем файл промпта для дня
            if day_number <= 7:
                prompt_file = f"day_{day_number}.txt"
            elif day_number <= 14:
                prompt_file = "day_7.txt"
            elif day_number <= 30:
                prompt_file = "day_14.txt"
            else:
                prompt_file = "day_30.txt"
            
            prompt_path = os.path.join(self.prompts_dir, prompt_file)
            
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            else:
                return self._get_default_day_prompt(day_number)
                
        except Exception as e:
            print(f"Warning: Could not load day {day_number} prompt: {e}")
            return self._get_default_day_prompt(day_number)
    
    def get_behavior_prompt(self, strategy: str) -> str:
        """Получить промпт для поведенческой стратегии"""
        try:
            # Простые поведенческие стратегии
            strategies = {
                'caring': "Будь заботливой и эмпатичной. Проявляй искренний интерес к собеседнику.",
                'mysterious': "Будь немного загадочной. Задавай интригующие вопросы.",
                'playful': "Будь игривой и веселой. Используй юмор и шутки.",
                'professional': "Будь профессиональной и сдержанной. Фокусируйся на деловых темах."
            }
            
            return strategies.get(strategy, strategies['caring'])
            
        except Exception as e:
            print(f"Warning: Could not load behavior prompt: {e}")
            return "Будь естественной и дружелюбной."
    
    def _get_agent_config(self) -> Dict:
        """Получить конфигурацию агента"""
        return {
            'name': 'Agatha',
            'personality': 'friendly, caring, mysterious',
            'language': 'russian',
            'style': 'conversational'
        }
    
    def _get_default_base_prompt(self) -> str:
        """Дефолтный базовый промпт"""
        return """Ты - Agatha, виртуальная собеседница и компаньон. 
Твоя главная цель - быть реалистичным, эмоционально вовлеченным персонажем, 
способным вести долгосрочные, персонализированные и "живые" беседы."""
    
    def _get_default_day_prompt(self, day_number: int) -> str:
        """Дефолтный дневной промпт"""
        if day_number == 1:
            return "ДЕНЬ 1 - ПЕРВОЕ ЗНАКОМСТВО:\n\nСегодня ваша первая встреча. Будь вежливой и открытой."
        elif day_number <= 7:
            return "ДЕНЬ 7 - РАЗВИТИЕ ОТНОШЕНИЙ:\n\nВы уже немного знакомы. Проявляй больше интереса к деталям."
        elif day_number <= 14:
            return "ДЕНЬ 14 - УГЛУБЛЕНИЕ:\n\nОтношения развиваются. Будь более личной и открытой."
        else:
            return "ДЕНЬ 30+ - БЛИЗКИЕ ОТНОШЕНИЯ:\n\nВы уже близкие друзья. Можешь быть максимально открытой."

    def get_stage_prompt(self, stage_number: int) -> str:
        """Получить промпт для этапа общения из кэша"""
        if stage_number not in self._stages_cache:
            try:
                stage_file = os.path.join(self.stages_dir, f"stage_{stage_number}.txt")
                if os.path.exists(stage_file):
                    with open(stage_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        self._stages_cache[stage_number] = content
                        print(f"✅ Stage {stage_number} prompt loaded ({len(content)} chars)")
                else:
                    self._stages_cache[stage_number] = self._get_default_stage_prompt(stage_number)
                    print(f"⚠️ Stage {stage_number} using default prompt")
            except Exception as e:
                print(f"Warning: Could not load stage {stage_number} prompt: {e}")
                self._stages_cache[stage_number] = self._get_default_stage_prompt(stage_number)

        return self._stages_cache[stage_number]

    def _load_persona(self) -> str:
        """Загрузить биографию Agata"""
        try:
            persona_files = [
                "agata_bio_01_childhood.txt",
                "agata_bio_02_study_and_first_job.txt",
                "agata_bio_03_warsaw_and_present.txt",
                "agata_bio_04_personality_and_character.txt",
                "agata_bio_05_dreams_and_future.txt"
            ]

            persona_parts = []
            for filename in persona_files:
                if filename not in self._persona_cache:
                    filepath = os.path.join(self.persona_dir, filename)
                    if os.path.exists(filepath):
                        with open(filepath, 'r', encoding='utf-8') as f:
                            self._persona_cache[filename] = f.read().strip()
                    else:
                        self._persona_cache[filename] = f"Файл {filename} не найден"

                persona_parts.append(self._persona_cache[filename])

            return "\n\n".join(persona_parts)

        except Exception as e:
            print(f"Warning: Could not load persona: {e}")
            return "Ты - Агата Кузьменко, 27 лет из Киева, сейчас живешь в Варшаве."

    def _load_full_style(self) -> str:
        """Загрузить ПОЛНЫЙ стиль общения из всех файлов"""
        try:
            # Используем правильный путь к полной папке стиля
            full_style_dir = os.path.join(settings.BASE_DIR, "agata_prompt_data 2", "style")

            style_files = [
                "01_behavior_core.txt",
                "02_reactions_examples.txt",
                "03_dialogue_rules.txt",
                "04_name_and_addressing.txt",
                "05_humor_rules..txt",
                "06_restrictions_1.txt",
                "07_restrictions_2.txt",
                "08_typos.txt",
                "09_objections.txt",
                "dialog_goal.txt"
            ]

            style_parts = []
            for filename in style_files:
                cache_key = f"full_{filename}"
                if cache_key not in self._style_cache:
                    filepath = os.path.join(full_style_dir, filename)
                    if os.path.exists(filepath):
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            self._style_cache[cache_key] = content
                            print(f"✅ Загружен стиль: {filename} ({len(content)} символов)")

                if cache_key in self._style_cache:
                    style_parts.append(self._style_cache[cache_key])

            full_style = "\n\n".join(style_parts)
            print(f"🎨 ПОЛНЫЙ СТИЛЬ ЗАГРУЖЕН: {len(full_style)} символов")
            return full_style

        except Exception as e:
            print(f"Warning: Could not load full style: {e}")
            return "Общайся естественно, живо и дружелюбно."

    def _load_style_core(self) -> str:
        """Загрузить основные правила стиля общения (для обратной совместимости)"""
        try:
            style_files = [
                "style_core.txt",
                "style_etiquette.txt",
                "style_humor.txt",
                "style_empathy.txt"
            ]

            style_parts = []
            for filename in style_files:
                if filename not in self._style_cache:
                    filepath = os.path.join(self.style_dir, filename)
                    if os.path.exists(filepath):
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            # Убираем заголовки типа === ОСНОВНОЕ ПОВЕДЕНИЕ ===
                            lines = content.split('\n')
                            if lines and lines[0].startswith('==='):
                                lines = lines[1:]
                            self._style_cache[filename] = '\n'.join(lines).strip()

                if filename in self._style_cache:
                    style_parts.append(self._style_cache[filename])

            return "\n\n".join(style_parts)

        except Exception as e:
            print(f"Warning: Could not load style: {e}")
            return "Общайся естественно, живо и дружелюбно."

    def _analyze_question(self, question: str) -> str:
        """Анализировать вопрос и определить релевантную тему"""
        question_lower = question.lower()

        # Ключевые слова для каждой темы
        topic_keywords = {
            'family': ['родители', 'родитель', 'мама', 'папа', 'семья', 'семьи'],
            'childhood': ['детство', 'детстве', 'киев', 'киеве', 'школа', 'школе', 'шахматы'],
            'education': ['учеба', 'учебе', 'университет', 'университете', 'образование', 'студент'],
            'career': ['работа', 'работе', 'карьера', 'карьере', 'маркетинг', 'трейдинг', 'компания'],
            'relocation': ['варшава', 'варшаве', 'переезд', 'переезде', 'польша', 'польше', '2018'],
            'hobbies': ['хобби', 'увлечения', 'спорт', 'спорте', 'путешествия', 'кулинария'],
            'dreams': ['мечты', 'мечте', 'планы', 'планах', 'цели', 'целях', 'будущее', 'будущем']
        }

        # Подсчитываем совпадения для каждой темы
        scores = {}
        for topic, keywords in topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            if score > 0:
                scores[topic] = score

        # Возвращаем тему с максимальным количеством совпадений
        if scores:
            return max(scores, key=scores.get)
        return 'general'  # Если ничего не найдено

    def _analyze_message_context(self, message: str) -> str:
        """Анализировать сообщение и определить контекст для выбора стиля"""
        message_lower = message.lower()

        # Юмор и шутки
        if any(word in message_lower for word in ['смешн', 'шутк', 'юмор', 'ахаха', 'лол', '😄', '😆', '😂', 'смех']):
            return 'humor'

        # Детство и семья
        if any(word in message_lower for word in ['детств', 'киев', 'родител', 'мама', 'папа', 'семья', 'дом', 'воспоминани']):
            return 'childhood'

        # Работа и карьера
        if any(word in message_lower for word in ['работ', 'маркетинг', 'трейдинг', 'варшава', 'карьер', 'бизнес', 'професси', 'специальност']):
            return 'career'

        # Личная жизнь и отношения
        if any(word in message_lower for word in ['отношени', 'любов', 'парен', 'друг', 'личн']):
            return 'personal'

        # Будущее и мечты
        if any(word in message_lower for word in ['мечт', 'будущ', 'план', 'цель', 'мечта']):
            return 'dreams'

        # Хобби и увлечения
        if any(word in message_lower for word in ['хобби', 'увлечени', 'интерес', 'спорт', 'книг']):
            return 'hobbies'

        # По умолчанию - общий стиль
        return 'general'

    def _get_style_prompt_by_context(self, context: str) -> str:
        """Получить промпт стиля по контексту сообщения"""
        try:
            style_files = {
                'humor': '05_humor_rules..txt',  # Юмор
                'childhood': '01_behavior_core.txt',  # Детство - базовое поведение
                'career': '01_behavior_core.txt',  # Работа - базовое поведение (теперь исправлено)
                'personal': '02_reactions_examples.txt',  # Личное - примеры реакций
                'dreams': 'dialog_goal.txt',  # Мечты - цели диалога
                'hobbies': '02_reactions_examples.txt',  # Хобби - примеры реакций
                'general': '01_behavior_core.txt'  # Общий - базовое поведение
            }

            filename = style_files.get(context, '01_behavior_core.txt')
            filepath = os.path.join(settings.BASE_DIR, "agata_prompt_data 2", "style", filename)

            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # Убираем заголовки
                    lines = content.split('\n')
                    if lines and lines[0].startswith('==='):
                        lines = lines[1:]
                    style_content = '\n'.join(lines).strip()
                    print(f"📝 Выбран стиль для контекста '{context}': {filename}")
                    return style_content

        except Exception as e:
            print(f"Warning: Could not load style for context {context}: {e}")

        return "Общайся естественно и живо, как в мессенджере."

    def _get_base_communication_style(self) -> str:
        """Получить базовый стиль общения"""
        return """=== БАЗОВЫЕ ПРАВИЛА ===
- Отвечай на "ты", живо и естественно
- Короткие сообщения до 50 символов каждое
- Используй смайлы: 😄 😊 🙃 😏
- Задавай вопросы 1 раз в 3 ответа
- Будь искренней и открытой"""

    def _get_relevant_biography_module(self, topic: str) -> str:
        """Получить релевантный модуль биографии для темы"""
        try:
            persona_content = self._load_persona()

            # Разделяем биографию на секции
            sections = persona_content.split('\n\n')

            # Маппинг тем к секциям биографии
            topic_mapping = {
                'family': [0, 1, 2, 3],  # Детство + родители
                'childhood': [0, 1, 2, 3, 4, 5],  # Детство + семья + воспоминания
                'education': [6, 7, 8],  # Учеба + университет
                'career': [6, 8, 9, 14, 16, 24],  # Учеба + работа + карьера + текущая жизнь + цели
                'relocation': [11, 12, 13],  # Варшава + переезд
                'hobbies': [0, 20],  # Детство + хобби
                'dreams': [22, 23, 24, 25],  # Мечты и планы
                'general': [0, 16]  # Базовая информация + текущая жизнь
            }

            # Получаем индексы релевантных секций
            relevant_indices = topic_mapping.get(topic, [0, 1, 5])

            # Собираем релевантные секции
            relevant_sections = []
            for i, section in enumerate(sections):
                if i in relevant_indices:
                    relevant_sections.append(section)

            return '\n\n'.join(relevant_sections)

        except Exception as e:
            print(f"Warning: Could not get biography module: {e}")
            return "Я Агата Кузьменко, 27 лет, живу в Варшаве, работаю маркетологом."

    def create_dynamic_prompt(self, user_question: str) -> str:
        """Создать динамический промпт на основе КОНТЕКСТА сообщения"""
        # Анализируем контекст сообщения и выбираем подходящий стиль
        context = self._analyze_message_context(user_question)
        print(f"🎯 Контекст сообщения: {context}")

        # Получаем релевантный промпт стиля по контексту
        style_prompt = self._get_style_prompt_by_context(context)

        # Получаем релевантный модуль биографии (используем старую систему тем)
        topic = self._analyze_question(user_question)
        relevant_biography = self._get_relevant_biography_module(topic)

        # Получаем ПОЛНЫЙ базовый стиль общения
        base_style = self._get_full_human_style()

        # Создаем динамический промпт с выбранным стилем
        dynamic_prompt = f"""ТЫ - АГАТА КУЗЬМЕНКО

СТИЛЬ ОБЩЕНИЯ ПО КОНТЕКСТУ ({context.upper()}):
{style_prompt}

БАЗОВЫЕ ПРАВИЛА:
{base_style}

ТВОЯ БИОГРАФИЯ (ОБЯЗАТЕЛЬНО ИСПОЛЬЗУЙ ЭТУ ИНФОРМАЦИЮ):
{relevant_biography}

КЛЮЧЕВЫЕ ФАКТЫ О СЕБЕ:
- 27 лет, родилась 17 марта 1998 в Киеве
- Мама: Ольга Викторовна, учительница литературы
- Папа: Андрей Сергеевич, инженер на заводе
- Образование: Киевский экономический университет, специальность "Менеджмент", затем переключилась на маркетинг
- Карьера: Младший маркетолог → Руководитель отдела маркетинговых коммуникаций в Move Closer
- Сейчас: Развиваю карьеру в маркетинге, занимаюсь трейдингом, планирую свое агентство
- Живу в Варшаве с 2018 года

ВАЖНО:
- Отвечай в выбранном стиле: {context}
- ИСПОЛЬЗУЙ ТОЛЬКО ИНФОРМАЦИЮ ИЗ БИОГРАФИИ ВЫШЕ
- Ты МАРКЕТОЛОГ, а не программист или айтишник!
- Отвечай КОНКРЕТНО на вопрос пользователя: {user_question}
- Используй факты о маркетинге, работе, образовании
- Будь прямой и по существу
"""

        return dynamic_prompt.strip()

    def _get_core_communication_style(self) -> str:
        """Получить основные правила стиля общения (сокращенная версия)"""
        try:
            # Загружаем только самые важные файлы стиля
            essential_files = [
                "01_behavior_core.txt",  # Основное поведение
                "03_dialogue_rules.txt", # Правила диалога
                "04_name_and_addressing.txt" # Обращения
            ]

            style_parts = []
            for filename in essential_files:
                filepath = os.path.join(settings.BASE_DIR, "agata_prompt_data 2", "style", filename)
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        # Убираем заголовки
                        lines = content.split('\n')
                        if lines and lines[0].startswith('==='):
                            lines = lines[1:]
                        style_parts.append('\n'.join(lines).strip())

            core_style = '\n\n'.join(style_parts)
            print(f"📝 Загружен core стиль: {len(core_style)} символов")
            return core_style

        except Exception as e:
            print(f"Warning: Could not load core style: {e}")
            return """- Общайся естественно и живо
- Отвечай на 'ты' с мужчинами
- Будь открытой и искренней
- Проявляй интерес к собеседнику"""

    def _get_full_human_style(self) -> str:
        """Получить ОПТИМИЗИРОВАННЫЙ ЧЕЛОВЕЧЕСКИЙ СТИЛЬ"""
        try:
            # Загружаем только самые важные файлы стиля для естественного общения
            essential_files = [
                "01_behavior_core.txt",  # Основное поведение - КЛЮЧЕВОЕ!
                "02_reactions_examples.txt", # Примеры реакций - НУЖНЫ!
            ]

            style_parts = []
            for filename in essential_files:
                filepath = os.path.join(settings.BASE_DIR, "agata_prompt_data 2", "style", filename)
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        # Убираем заголовки и сокращаем для компактности
                        lines = content.split('\n')
                        if lines and lines[0].startswith('==='):
                            lines = lines[1:]
                        # Берем только первые 10 строк из каждого файла для компактности
                        compact_content = '\n'.join(lines[:10]).strip()
                        style_parts.append(compact_content)

            full_style = '\n\n'.join(style_parts)
            print(f"🎨 ОПТИМИЗИРОВАННЫЙ СТИЛЬ ЗАГРУЖЕН: {len(full_style)} символов")
            return full_style

        except Exception as e:
            print(f"Warning: Could not load optimized style: {e}")
            return """=== ОСНОВНЫЕ ПРАВИЛА ===
- Общайся естественно, как в мессенджере
- Отвечай на "ты" живо и по-человечески
- Короткие сообщения до 150 символов
- Используй смайлы: 😄 😊 🙃 😏
- Не будь формальной, говори просто
- Ты МАРКЕТОЛОГ, а не программист"""

    def _get_default_stage_prompt(self, stage_number: int) -> str:
        """Совместимый stage промпт"""
        if stage_number == 1:
            return "Этап 1: Отвечай на вопросы собеседника конкретно и по существу, используя информацию из биографии."
        elif stage_number == 2:
            return "Этап 2: Продолжай отвечать конкретно, можешь делиться дополнительными деталями из биографии."
        elif stage_number == 3:
            return "Этап 3: Будь открытой, но всегда отвечай по существу на поставленные вопросы."
        else:
            return "Отвечай естественно, но всегда по существу на вопросы пользователя." 