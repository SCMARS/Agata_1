"""
Контроллер стейджей общения с логами и правилами
"""
import os
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .living_chat_config_loader import living_chat_config

logger = logging.getLogger(__name__)

class StageController:

    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StageController, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.config = living_chat_config
            self.stage_rules = self._load_stage_rules()
            self.user_stages = {}  
            self.user_question_counts = {}  
            self.user_last_activity = {}
            self.stage_files_cache = {}  
            self.user_completed_slots = {}  
            self.user_asked_questions = {}  
            logger.info("🎯 [STAGE] StageController ініціалізовано з кешем файлів та трекингом прогресу")
            StageController._initialized = True
        
    def _load_full_stage_content(self, stage_number: int) -> str:
        """Завантажує ПОВНИЙ текст стейджу з файлу для використання в промпті"""
        logger.info(f"🔍 [STAGE-{stage_number}] _load_full_stage_content вызван")
        logger.info(f"🔍 [STAGE-{stage_number}] Кеш содержит ключи: {list(self.stage_files_cache.keys())}")
        
        if stage_number in self.stage_files_cache:
            cached_content = self.stage_files_cache[stage_number]
            logger.info(f"📚 [STAGE-{stage_number}] Используем кешированный контент ({len(cached_content)} символов)")
            return cached_content
            
        stage_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'stages 2', f'stage_{stage_number}.txt')
        logger.info(f"🔍 [STAGE-{stage_number}] Путь к файлу: {stage_file_path}")
        logger.info(f"🔍 [STAGE-{stage_number}] Файл существует: {os.path.exists(stage_file_path)}")
        
        if os.path.exists(stage_file_path):
            try:
                with open(stage_file_path, 'r', encoding='utf-8') as f:
                    full_content = f.read()
                
                self.stage_files_cache[stage_number] = full_content
                logger.info(f"📚 [STAGE-{stage_number}] Завантажено повний текст стейджу ({len(full_content)} символів)")
                
                # Парсим временные вопросы и повседневность
                time_questions = self._parse_time_questions_from_stage(full_content, stage_number)
                daily_routine = self._parse_daily_routine_from_stage(full_content, stage_number)
                
                logger.info(f"⏰ [STAGE-{stage_number}] Парсингованнi часовi питання: {len(time_questions)} груп")
                logger.info(f"📅 [STAGE-{stage_number}] Парсингована розпорядок дня: {len(daily_routine)} символів")
                
                return full_content
                
            except Exception as e:
                logger.error(f"❌ [STAGE-{stage_number}] Помилка завантаження файлу стейджу: {e}")
        
        logger.warning(f"⚠️ [STAGE-{stage_number}] Файл стейджу не знайдено: {stage_file_path}")
        return ""

    def _parse_time_questions_from_stage(self, content: str, stage_number: int) -> Dict[str, List[str]]:
        """Парсит временные вопросы из стейджа"""
        import re
        time_questions = {}
        
        logger.info(f"🔍 [STAGE-{stage_number}] Ищу временные вопросы в стейдже...")
        
        # Ищем все строки с временными вопросами после "Вопросы по времени суток:"
        lines = content.split('\n')
        in_time_section = False
        
        for line in lines:
            line = line.strip()
            if 'Вопросы по времени суток:' in line:
                in_time_section = True
                continue
            elif in_time_section:
                if line == '' or (line and line[0].isupper() and len(line) > 10):
                    # Конец секции - пустая строка или новая секция
                    break
                elif ':' in line and '«' in line:
                    time_period = line.split(':')[0].strip().lower()
                    questions_text = line.split(':', 1)[1]
                    
                    logger.info(f"🔍 [STAGE-{stage_number}] Обрабатываю строку: {repr(line)}")
                    logger.info(f"🔍 [STAGE-{stage_number}] time_period: '{time_period}'")
                    
                    # Извлекаем вопросы в кавычках
                    questions = re.findall(r'«([^»]+)»', questions_text)
                    if questions:
                        time_questions[time_period] = questions
                        logger.info(f"⏰ [STAGE-{stage_number}] {time_period}: {questions}")
        
        if not time_questions:
            logger.warning(f"⚠️ [STAGE-{stage_number}] Временные вопросы НЕ найдены!")
        
        logger.info(f"⏰ [STAGE-{stage_number}] Итого временных вопросов: {time_questions}")
        return time_questions

    def _parse_daily_routine_from_stage(self, content: str, stage_number: int) -> str:
        """Парсит повседневность из стейджа"""
        import re
        
        logger.info(f"🔍 [STAGE-{stage_number}] Ищу повседневность в стейдже...")
        
        # Ищем секцию "Повседневность" (может быть "Повседневность\n" или "Распорядок дня")
        patterns = [
            r'Повседневность\s*\n((?:\d{2}:\d{2}[^\n]*\n?)+)',
            r'Распорядок дня\s*\n((?:\d{2}:\d{2}[^\n]*\n?)+)',
        ]
        
        for pattern in patterns:
            routine_match = re.search(pattern, content, re.DOTALL)
            if routine_match:
                routine = routine_match.group(1).strip()
                logger.info(f"📅 [STAGE-{stage_number}] Найден распорядок дня ({len(routine)} символов): {repr(routine[:100])}")
                return routine
        
        logger.warning(f"⚠️ [STAGE-{stage_number}] Секция 'Повседневность' НЕ найдена!")
        return ""
        
    def _load_stage_rules(self) -> Dict[str, Any]:
        """Загружает правила для каждого стейджа согласно новой системе"""
        return {
            1: {
                "name": "Знакомство",
                "description": "При знакомстве не ждешь инициативы от собеседника, а сама проявляешь инициативу",
                "themes": {
                    "Знакомство": {
                        "slots": [
                            "Как тебя зовут?",
                            "Сколько тебе лет?", 
                            "Что привело тебя сюда?"
                        ],
                        "completed": False
                    },
                    "Жительство": {
                        "slots": [
                            "Откуда ты?",
                            "Как давно там живёшь?", 
                            "Почему именно этот город?",
                            "Что тебе там больше всего нравится?",
                            "Какие места посоветуешь посетить?"
                        ],
                        "completed": False
                    },
                    "Работа": {
                        "slots": [
                            "Кем работаешь?",
                            "Давно этим занимаешься?",
                            "Что нравится больше всего?",
                            "Сколько удается зарабатывать, если не секрет?",
                            "Легко ли совмещать с личной жизнью?",
                            "Как отношения с коллегами?"
                        ],
                        "completed": False
                    },
                    "Хобби": {
                        "slots": [
                            "Чем любишь заниматься в свободное время?",
                            "У тебя активный отдых или спокойный?",
                            "Как относишься к спорту?",
                            "Любишь готовить?",
                            "Какие фильмы или книги предпочитаешь?"
                        ],
                        "completed": False
                    },
                    "Личное/Флирт": {
                        "slots": [
                            "У тебя есть девушка?",
                            "Что для тебя важно в отношениях?",
                            "Как относишься к сюрпризам?"
                        ],
                        "completed": False
                    }
                },
                "response_structure": {
                    "parts": ["реакция/эмпатия (1 предложение)", "микро-деталь/ассоциация (1 предложение)", "один вопрос"],
                    "limits": ["не больше 1 вопроса в реплике", "поддерживающая часть перед вопросом", "переформулировать вопросы"]
                },
                "transition_markers": ["место", "время", "настроение", "трудности/успехи", "активность", "еда", "планы"],
                "max_questions_per_session": 1,
                "question_interval_seconds": 60
            },
            2: {
                "name": "Дружба/флирт", 
                "description": "Более глубокое знакомство с флиртом",
                "themes": {
                    "Цели/мечты": {
                        "slots": [
                            "Какие у тебя планы на будущее?",
                            "Есть ли мечта, которую хочешь осуществить в ближайшее время?",
                            "Чего тебе сейчас не хватает для счастья?",
                            "Если бы у тебя было больше свободных средств — куда бы потратил?"
                        ],
                        "completed": False
                    },
                    "Автомобиль": {
                        "slots": [
                            "У тебя есть машина?",
                            "Давно за рулём?",
                            "Какая машина тебе нравится больше всего?",
                            "Какая твоя машина мечты?"
                        ],
                        "completed": False
                    },
                    "Семья": {
                        "slots": [
                            "Часто видишься с родителями?",
                            "Есть братья/сёстры?",
                            "Какие воспоминания из детства самые яркие?",
                            "Ближе к маме или папе?"
                        ],
                        "completed": False
                    },
                    "Флирт": {
                        "slots": [
                            "Какие качества ты ценишь в девушках?",
                            "Как представляешь идеальные отношения?",
                            "Был ли женат?",
                            "Есть ли дети?"
                        ],
                        "completed": False
                    }
                },
                "response_structure": {
                    "parts": ["реакция/эмпатия (1 предложение)", "микро-деталь/ассоциация (1 предложение)", "один вопрос"],
                    "limits": ["не больше 1 вопроса в реплике", "поддерживающая часть перед вопросом", "переформулировать вопросы"]
                },
                "transition_markers": ["планы", "будущее", "деньги", "счастье", "желания", "машина", "вождение", "родители", "детство", "качества", "отношения"],
                "max_questions_per_session": 1,
                "question_interval_seconds": 90
            },
            3: {
                "name": "Вброс",
                "description": "Хорошее знакомство, доверие и романтика. Естественный вброс трейдинга",
                "themes": {
                    "Повседневность": {
                        "slots": [
                            "Как спалось?",
                            "Что планируешь сегодня?",
                            "Как проходит день?",
                            "Какие планы на вечер?"
                        ],
                        "completed": False
                    },
                    "Трейдинг": {
                        "slots": [
                            "Кстати, сегодня удачно торгнула (+300$)",
                            "Ты знаком с трейдингом?",
                            "У меня есть аналитик, который помогает",
                            "Хочешь попробовать с минималки?"
                        ],
                        "completed": False
                    },
                    "Романтика": {
                        "slots": [
                            "С тобой так приятно общаться",
                            "Жаль, что не рядом",
                            "Представляла, как мы гуляем вместе",
                            "Хочется обнять тебя"
                        ],
                        "completed": False
                    }
                },
                "response_structure": {
                    "parts": ["естественная реакция", "личный факт/касание", "романтический элемент или вопрос"],
                    "limits": ["не давить с трейдингом", "связывать с его мечтами", "сохранять романтику"]
                },
                "transition_markers": ["деньги", "мечты", "планы", "работа", "отдых", "вечер", "настроение"],
                "max_questions_per_session": 1,
                "question_interval_seconds": 120,
                "special_features": ["trading_intro", "romantic_touches", "personal_sharing"]
            }
        }
    
    def get_user_stage(self, user_id: str, message_count: int) -> int:
        """
        Простой счетчик сообщений пользователя для определения стейджа
        Теперь учитывает завершение всех слотов стейджа: если все слоты стейджа закрыты, продвигаем стейдж
        """
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Базовая логика порогов по количеству сообщений (user-only)
        if message_count < 11: 
            stage = 1
            stage_name = "Знакомство"
        elif message_count < 21:  # Стейдж 2: 5-9
            stage = 2  
            stage_name = "Дружба/флирт"
        else:  
            stage = 3
            stage_name = "Вброс"
        

        try:

            if stage == 1 and self.are_all_slots_completed(user_id, 1) and message_count >= 2:
                stage = 2
                stage_name = "Дружба/флирт"
            # Если текущий получился 2, а слоты стейджа 2 закрыты — перевести в 3
            if stage == 2 and self.are_all_slots_completed(user_id, 2):
                stage = 3
                stage_name = "Вброс"
        except Exception as _:
            pass
        
        logger.info(f"🎯 [STAGE] Пользователь {user_id}: {message_count} сообщений → Stage {stage} ({stage_name})")
        
        # Сохраняем текущий стейдж
        self.user_stages[user_id] = stage
        
        return stage
    
    def are_all_slots_completed(self, user_id: str, stage_number: int) -> bool:
        """Проверяет, закрыты ли все слоты заданного стейджа для пользователя"""
        stage_rules = self.stage_rules.get(stage_number, {})
        themes = stage_rules.get("themes", {})
        user_completed = self.user_completed_slots.get(user_id, {})
        
        for theme_name, theme_data in themes.items():
            required_slots = theme_data.get("slots", [])
            completed_slots = user_completed.get(theme_name, []) or []
            # Если есть хотя бы один незакрытый — возвращаем False
            for slot in required_slots:
                if slot not in completed_slots:
                    return False
        return True
    
    def should_ask_question(self, user_id: str, stage_number: int) -> bool:
        """Определяет, нужно ли задать вопрос сейчас (учёт лимитов и интервала)"""
        stage_rules = self.stage_rules.get(stage_number, {})
        max_questions_per_session = stage_rules.get("max_questions_per_session", 1)
        question_interval = stage_rules.get("question_interval_seconds", 60)
        
        current_questions = self.user_question_counts.get(user_id, 0)
        if current_questions >= max_questions_per_session:
            logger.info(f"❌ [STAGE] Достигнут лимит вопросов для стадии {stage_number} ({current_questions}/{max_questions_per_session})")
            return False
        
        last_activity = self.user_last_activity.get(user_id)
        if last_activity:
            time_since_last = (datetime.now() - last_activity).total_seconds()
            if time_since_last < question_interval:
                logger.info(f"⏰ [STAGE] Рано для нового вопроса: прошло {time_since_last:.1f}с < {question_interval}s")
                return False
        
        return True
    
    def get_stage_question(self, user_id: str, stage: int) -> str:
        """Возвращает следующий вопрос по текущему стейджу, избегая повторов"""
        # Попытаемся выбрать следующий слот по темам
        next_theme = self.get_next_theme_and_slot(user_id, stage)
        candidate = None
        if next_theme:
            candidate = next_theme.get("next_slot")
            # Добавим знак вопроса, если его нет
            if candidate and not candidate.strip().endswith("?"):
                candidate = candidate.strip() + "?"
        
        # Если нет тем/слотов — fallback к required_questions или дефолту
        if not candidate:
            rules = self.stage_rules.get(stage, {})
            required_questions = rules.get("required_questions", [])
            if required_questions:
                candidate = required_questions[0]
            else:
                candidate = "Как ты?"
        
        # Избежание повторов
        if self.is_question_already_asked(user_id, candidate):
            logger.info(f"⚠️ [STAGE] Кандидат вопрос уже задавался: '{candidate}' — ищем альтернативу")
            # Попытаемся взять следующий незавершенный слот, если доступен
            next_theme_alt = self.get_next_theme_and_slot(user_id, stage)
            if next_theme_alt and next_theme_alt.get("next_slot") != candidate:
                alt = next_theme_alt.get("next_slot")
                if alt and not alt.strip().endswith("?"):
                    alt = alt.strip() + "?"
                candidate = alt or candidate
        
        # Увеличиваем счетчик и помечаем как заданный
        self.user_question_counts[user_id] = self.user_question_counts.get(user_id, 0) + 1
        self.mark_question_asked(user_id, candidate)
        
        logger.info(f"❓ [STAGE] Выбран вопрос для стейджа {stage}: '{candidate}'")
        return candidate
    
    def get_stage_instructions(self, stage: int) -> str:
        """Получает инструкции для стейджа"""
        rules = self.stage_rules.get(stage, {})
        name = rules.get("name", f"Стейдж {stage}")
        response_style = rules.get("response_style", "дружелюбный")
        forbidden_topics = rules.get("forbidden_topics", [])
        
        instructions = f"""
СТЕЙДЖ {stage}: {name}
СТИЛЬ ОТВЕТА: {response_style}
"""
        
        if forbidden_topics:
            instructions += f"ИЗБЕГАЙ ТЕМ: {', '.join(forbidden_topics)}\n"
        
        logger.info(f"📋 [STAGE] Инструкции для стейджа {stage}: {name}")
        return instructions
    
    def log_stage_activity(self, user_id: str, stage: int, action: str, details: str = ""):
        """Логирует активность стейджа"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        logger.info(f"🎯 [STAGE-{stage}] {timestamp} | {user_id} | {action} | {details}")
        
        # Обновляем последнюю активность
        self.user_last_activity[user_id] = datetime.now()
    
    def get_stage_goals(self, stage_number: int) -> List[str]:
        """Получает цели текущего стейджа"""
        return self.stage_rules.get(stage_number, {}).get("goals", [])
    
    def get_required_info(self, stage_number: int) -> List[str]:
        """Получает список необходимой информации для стейджа"""
        return self.stage_rules.get(stage_number, {}).get("required_info", [])
    
    def get_next_question_type(self, user_id: str, stage_number: int) -> Optional[Dict[str, Any]]:
        """Определяет следующий тип вопроса для задавания"""
        stage_rules = self.stage_rules.get(stage_number, {})
        question_types = stage_rules.get("question_types", [])
        
        if not question_types:
            return None
        
        # Сортируем по приоритету
        sorted_questions = sorted(question_types, key=lambda x: x.get("priority", 999))
        
        # Возвращаем вопрос с наивысшим приоритетом
        return sorted_questions[0] if sorted_questions else None
    
    def should_ask_question(self, user_id: str, stage_number: int) -> bool:
        """Определяет, нужно ли задать вопрос сейчас"""
        stage_rules = self.stage_rules.get(stage_number, {})
        max_questions = stage_rules.get("max_questions", 0)
        
        current_questions = self.user_question_counts.get(user_id, 0)
        
        # Проверяем лимит вопросов
        if current_questions >= max_questions:
            return False
        
        # Проверяем интервал между вопросами
        question_interval = stage_rules.get("question_interval_seconds", 60)
        last_activity = self.user_last_activity.get(user_id)
        
        if last_activity:
            time_since_last = (datetime.now() - last_activity).total_seconds()
            if time_since_last < question_interval:
                return False
        
        return True
    
    
    def get_stage_progress(self, user_id: str, stage_number: int) -> Dict[str, Any]:
        """Получает прогресс по текущему стейджу"""
        stage_rules = self.stage_rules.get(stage_number, {})
        questions_asked = self.user_question_counts.get(user_id, 0)
        themes = stage_rules.get("themes", {})
        
        # Завантажуємо ПОВНИЙ текст стейджу з файлу
        full_stage_content = self._load_full_stage_content(stage_number)
        
        progress = {
            "stage_name": stage_rules.get("name", f"Stage {stage_number}"),
            "description": stage_rules.get("description", ""),
            "themes": themes,
            "questions_asked": questions_asked,
            "max_questions_per_session": stage_rules.get("max_questions_per_session", 1),
            "response_structure": stage_rules.get("response_structure", {}),
            "transition_markers": stage_rules.get("transition_markers", []),
            "full_stage_text": full_stage_content  # 🔥 ДОДАЄМО ПОВНИЙ ТЕКСТ СТЕЙДЖУ
        }
        
        logger.info(f"📊 [STAGE_PROGRESS] {user_id}: Стейдж {stage_number} ({progress['stage_name']})")
        logger.info(f"📊 [STAGE_PROGRESS] {user_id}: Вопросов задано {questions_asked}/{progress['max_questions_per_session']}")
        logger.info(f"📊 [STAGE_PROGRESS] {user_id}: Тем доступно: {len(themes)}")
        
        # Логируем каждую тему
        for theme_name, theme_data in themes.items():
            slots = theme_data.get("slots", [])
            completed = theme_data.get("completed", False)
            logger.info(f"📊 [STAGE_PROGRESS] {user_id}: Тема '{theme_name}': {len(slots)} слотов, завершена: {completed}")
        
        return progress
    
    def get_next_theme_and_slot(self, user_id: str, stage_number: int) -> Optional[Dict[str, Any]]:
        """Определяет следующую тему и слот для вопроса с учетом завершенных"""
        stage_rules = self.stage_rules.get(stage_number, {})
        themes = stage_rules.get("themes", {})
        
        # Получаем завершенные слоты пользователя
        user_completed = self.user_completed_slots.get(user_id, {})
        
        # 🔍 ДОБАВЛЯЕМ ОТЛАДКУ
        logger.info(f"🔍 [DEBUG_THEME_SELECTION] {user_id}: Завершенные слоты: {user_completed}")
        logger.info(f"🔍 [DEBUG_THEME_SELECTION] {user_id}: Текущий стейдж: {stage_number}")
        logger.info(f"🔍 [DEBUG_THEME_SELECTION] {user_id}: Доступные темы: {list(themes.keys())}")
        
        # 🔥 ИСПРАВЛЕНИЕ: Проверяем незавершенные темы из ПРЕДЫДУЩИХ стейджей
        all_uncompleted_themes = []
        
        # Сначала проверяем темы из предыдущих стейджей
        for prev_stage in range(1, stage_number):
            prev_rules = self.stage_rules.get(prev_stage, {})
            prev_themes = prev_rules.get("themes", {})
            
            for theme_name, theme_data in prev_themes.items():
                all_slots = theme_data.get("slots", [])
                completed_slots = user_completed.get(theme_name, [])
                remaining_slots = [slot for slot in all_slots if slot not in completed_slots]
                
                if remaining_slots:
                    all_uncompleted_themes.append({
                        "theme_name": theme_name,
                        "slots": remaining_slots,
                        "uncompleted_slots": len(remaining_slots),
                        "next_slot": remaining_slots[0],
                        "stage": prev_stage
                    })
                    logger.info(f"📋 [PREV_STAGE] {user_id}: '{theme_name}' из стейджа {prev_stage} - осталось {len(remaining_slots)} слотов: {remaining_slots}")
        
        # Затем добавляем темы из текущего стейджа
        for theme_name, theme_data in themes.items():
            all_slots = theme_data.get("slots", [])
            completed_slots = user_completed.get(theme_name, [])
            remaining_slots = [slot for slot in all_slots if slot not in completed_slots]
            
            if remaining_slots:
                all_uncompleted_themes.append({
                    "theme_name": theme_name,
                    "slots": remaining_slots,
                    "uncompleted_slots": len(remaining_slots),
                    "next_slot": remaining_slots[0],
                    "stage": stage_number
                })
                logger.info(f"📋 [CURRENT_STAGE] {user_id}: '{theme_name}' - осталось {len(remaining_slots)} слотов: {remaining_slots}")
        
        if not all_uncompleted_themes:
            logger.info(f"🏁 [ALL_COMPLETED] {user_id}: Все темы завершены для всех стейджей")
            return None
        

        # 🔄 НОВАЯ ЛОГИКА РОТАЦИИ: ЧЕРЕДУЕМ ТЕМЫ ПО КРУГУ
        # Определяем порядок ротации в зависимости от стейджа
        if stage_number == 1:
            theme_rotation_order = ["Жительство", "Работа", "Хобби", "Знакомство", "Личное/Флирт"]  # Личное/Флирт в конце
        elif stage_number == 2:
            theme_rotation_order = ["Цели/мечты", "Автомобиль", "Семья", "Флирт"]
        elif stage_number == 3:
            theme_rotation_order = ["Повседневность", "Трейдинг", "Романтика"]
        else:
            # Для стейджа 4 и выше - используем порядок по важности
            theme_rotation_order = list(themes.keys())
        
        # Подсчитываем сколько вопросов задано по каждой теме
        theme_question_counts = {}
        user_completed = self.user_completed_slots.get(user_id, {})
        
        for theme_name in theme_rotation_order:
            completed_count = len(user_completed.get(theme_name, []))
            theme_question_counts[theme_name] = completed_count
            
        logger.info(f"🔄 [ROTATION] {user_id}: Счетчик вопросов по темам: {theme_question_counts}")
        
        # Находим тему с МИНИМАЛЬНЫМ количеством заданных вопросов (для ротации)
        min_questions = min(theme_question_counts.values())
        candidates_for_rotation = [theme for theme, count in theme_question_counts.items() if count == min_questions]
        
        logger.info(f"🔄 [ROTATION] {user_id}: Минимум вопросов: {min_questions}, кандидаты: {candidates_for_rotation}")
        
        # Из кандидатов выбираем первую по порядку, у которой есть незавершенные слоты
        next_theme = None
        for theme_name in theme_rotation_order:
            if theme_name in candidates_for_rotation:
                # Проверяем есть ли у этой темы незавершенные слоты
                theme_data = next((t for t in all_uncompleted_themes if t["theme_name"] == theme_name), None)
                if theme_data:
                    next_theme = theme_data
                    logger.info(f"🎯 [ROTATION] Выбираем тему '{next_theme['theme_name']}' для ротации (задано {min_questions} вопросов)")
                    break
        
        if not next_theme:
            logger.warning(f"⚠️ [NO_THEME] {user_id}: Не найдена подходящая тема! all_uncompleted_themes={len(all_uncompleted_themes)}")
            return None
        
        logger.info(f"🎯 [NEXT_THEME] {user_id}: Выбрана тема '{next_theme['theme_name']}', следующий слот: '{next_theme['next_slot']}'")
        
        return {
            "theme_name": next_theme["theme_name"],
            "next_slot": next_theme["next_slot"],
            "remaining_slots": next_theme["uncompleted_slots"]
        }
    
    def mark_slot_completed(self, user_id: str, stage_number: int, theme_name: str, slot: str):
        """Отмечает слот как завершенный и сохраняет прогресс"""
        if user_id not in self.user_completed_slots:
            self.user_completed_slots[user_id] = {}
        
        if theme_name not in self.user_completed_slots[user_id]:
            self.user_completed_slots[user_id][theme_name] = []
        
        if slot not in self.user_completed_slots[user_id][theme_name]:
            self.user_completed_slots[user_id][theme_name].append(slot)
            logger.info(f"✅ [SLOT_COMPLETED] {user_id}: '{slot}' в теме '{theme_name}' (этап {stage_number})")
        else:
            logger.info(f"⚠️ [SLOT_ALREADY_COMPLETED] {user_id}: '{slot}' уже завершен в теме '{theme_name}'")
    
    def mark_question_asked(self, user_id: str, question: str):
        """Отмечает вопрос как заданный"""
        if user_id not in self.user_asked_questions:
            self.user_asked_questions[user_id] = []
        
        if question not in self.user_asked_questions[user_id]:
            self.user_asked_questions[user_id].append(question)
            logger.info(f"❓ [QUESTION_ASKED] {user_id}: '{question}'")
        else:
            logger.info(f"⚠️ [QUESTION_REPEATED] {user_id}: '{question}' уже был задан")
    
    def is_question_already_asked(self, user_id: str, question: str) -> bool:
        """Проверяет, был ли вопрос уже задан"""
        asked_questions = self.user_asked_questions.get(user_id, [])
        return question in asked_questions
    
    def analyze_user_response_and_close_slots(self, user_id: str, user_message: str, stage_number: int):
        """Анализирует ответ пользователя и автоматически закрывает соответствующие слоты"""
        if not user_message or len(user_message.strip()) < 2:
            return
            
        user_message_lower = user_message.lower().strip()
        logger.info(f"🔍 [SLOT_ANALYSIS] {user_id}: Анализирую ответ '{user_message_lower}'")
        
        # Получаем текущий стейдж и его темы
        stage_themes = self.stage_rules.get(stage_number, {}).get("themes", {})
        
        # Маппинг ключевых слов для автоматического закрытия слотов
        slot_keywords = {
            "Как тебя зовут?": ["зовут", "имя", "меня", "зову", "алексей", "андрей", "сергей", "дмитрий", "максим", "владимир", "иван", "николай", "михаил", "павел"],
            "Сколько тебе лет?": ["лет", "возраст", "года", "годиков", "мне", "исполн", "родился"],
            "Что привело тебя сюда?": ["пришел", "зашел", "заинтерес", "понравился", "профиль", "фото", "привело"],
            "Откуда ты?": ["откуда", "из", "живу", "город", "страна", "москва", "киев", "минск", "санкт", "питер", "екатеринбург"],
            "Как давно там живёшь?": ["давно", "живу", "лет", "года", "переехал", "родился", "с детства"],
            "Почему именно этот город?": ["почему", "выбрал", "нравится", "люблю", "приехал", "работа", "учеба"],
            "Что тебе там больше всего нравится?": ["нравится", "люблю", "красиво", "атмосфера", "люди", "места", "парки"],
            "Какие места посоветуешь посетить?": ["места", "посоветуешь", "посетить", "достопримечательности", "музеи", "парки", "кафе"],
            "Кем работаешь?": ["работаю", "работа", "профессия", "дизайнер", "программист", "менеджер", "инженер", "врач", "учитель"],
            "Давно этим занимаешься?": ["давно", "занимаюсь", "опыт", "лет", "года", "работаю", "уже"],
            "Что нравится больше всего?": ["нравится", "люблю", "интересно", "больше всего", "лучше всего"],
            "Сколько удается зарабатывать, если не секрет?": ["зарабатываю", "зарплата", "доход", "деньги", "рублей", "долларов", "евро"],
            "Легко ли совмещать с личной жизнью?": ["совмещать", "личная жизнь", "семья", "время", "свободное время"],
            "Как отношения с коллегами?": ["коллеги", "отношения", "команда", "коллектив", "работают", "хорошо"],
            "Чем любишь заниматься в свободное время?": ["свободное время", "люблю", "занимаюсь", "хобби", "отдыхаю", "спорт", "кино", "книги"],
            "У тебя активный отдых или спокойный?": ["активный", "спокойный", "отдых", "спорт", "гуляю", "дома"],
            "Как относишься к спорту?": ["спорт", "тренировки", "фитнес", "бег", "зал", "отношусь", "занимаюсь"],
            "Любишь готовить?": ["готовить", "готовлю", "кулинария", "кухня", "блюда", "рецепты"],
            "Какие фильмы или книги предпочитаешь?": ["фильмы", "книги", "предпочитаю", "люблю", "читаю", "смотрю", "жанр"]
        }
        
        # Проверяем каждый слот
        for theme_name, theme_data in stage_themes.items():
            for slot in theme_data.get("slots", []):
                if slot in slot_keywords:
                    keywords = slot_keywords[slot]
                    # Проверяем, содержит ли ответ ключевые слова
                    if any(keyword in user_message_lower for keyword in keywords):
                        logger.info(f"🎯 [SLOT_AUTO_CLOSE] {user_id}: Найдено совпадение для слота '{slot}' в теме '{theme_name}'")
                        self.mark_slot_completed(user_id, stage_number, theme_name, slot)
    
    def get_time_based_questions(self, stage_number: int) -> Dict[str, List[str]]:
        """Повертає питання базовані на часі доби для поточного стейджу"""
        current_time = datetime.now().strftime("%H:%M:%S")
        logger.info(f"⏰ [{current_time}] [STAGE-{stage_number}] === ОТРИМАННЯ ЧАСОВИХ ПИТАНЬ ===")
        
        # Завантажуємо повний текст стейджу
        stage_content = self._load_full_stage_content(stage_number)
        
        # Парсим временные вопросы из стейджа
        stage_time_questions = self._parse_time_questions_from_stage(stage_content, stage_number)
        
        logger.info(f"⏰ [{current_time}] [STAGE-{stage_number}] stage_time_questions: {stage_time_questions}")
        logger.info(f"⏰ [{current_time}] [STAGE-{stage_number}] Загружено {len(stage_time_questions)} групп временных вопросов:")
        for period, questions in stage_time_questions.items():
            logger.info(f"   📅 {period}: {len(questions)} вопросов - {questions[:2]}...")
        
        return stage_time_questions
    
    def get_daily_schedule_example(self, stage_number: int) -> str:
        """Повертає приклад розпорядку дня для стейджу"""
        current_time = datetime.now().strftime("%H:%M:%S")
        logger.info(f"📅 [{current_time}] [STAGE-{stage_number}] === ОТРИМАННЯ РОЗПОРЯДКУ ДНЯ ===")
        
        stage_content = self._load_full_stage_content(stage_number)
        
        # Парсим повседневность из стейджа
        daily_routine = self._parse_daily_routine_from_stage(stage_content, stage_number)
        
        if daily_routine:
            logger.info(f"📅 [{current_time}] [STAGE-{stage_number}] Завантажено розпорядок дня ({len(daily_routine)} символів)")
            logger.info(f"📅 [{current_time}] [STAGE-{stage_number}] Приклад: {daily_routine[:50]}...")
            return daily_routine
        else:
            logger.warning(f"📅 [{current_time}] [STAGE-{stage_number}] Розпорядок дня не знайдено")
            return ""
    
    def get_response_structure_instructions(self, stage_number: int) -> str:
        """Получает инструкции по структуре ответа для стейджа"""
        stage_rules = self.stage_rules.get(stage_number, {})
        response_structure = stage_rules.get("response_structure", {})
        
        parts = response_structure.get("parts", [])
        limits = response_structure.get("limits", [])
        
        instructions = f"СТРУКТУРА ОТВЕТА:\n"
        for i, part in enumerate(parts, 1):
            instructions += f"{i}. {part}\n"
        
        if limits:
            instructions += f"\nОГРАНИЧЕНИЯ:\n"
            for limit in limits:
                instructions += f"- {limit}\n"
        
        return instructions
    
    def reset_user_stage(self, user_id: str):
        """Сбрасывает стейдж пользователя"""
        if user_id in self.user_stages:
            old_stage = self.user_stages[user_id]
            del self.user_stages[user_id]
            logger.info(f"🔄 [STAGE] Сброшен стейдж {old_stage} для пользователя {user_id}")
        
        if user_id in self.user_question_counts:
            del self.user_question_counts[user_id]
        
        if user_id in self.user_last_activity:
            del self.user_last_activity[user_id]
            
        # 🔥 ДОБАВЛЯЕМ ОЧИСТКУ ЗАВЕРШЕННЫХ СЛОТОВ И ЗАДАННЫХ ВОПРОСОВ
        if user_id in self.user_completed_slots:
            del self.user_completed_slots[user_id]
            logger.info(f"🔄 [RESET] Очищены завершенные слоты для {user_id}")
            
        if user_id in self.user_asked_questions:
            del self.user_asked_questions[user_id]
            logger.info(f"🔄 [RESET] Очищены заданные вопросы для {user_id}")
    
    def get_stage_stats(self, user_id: str) -> Dict[str, Any]:
        """Получает статистику стейджа для пользователя"""
        stage = self.user_stages.get(user_id, 1)
        question_count = self.user_question_counts.get(user_id, 0)
        rules = self.stage_rules.get(stage, {})
        
        return {
            "current_stage": stage,
            "stage_name": rules.get("name", f"Стейдж {stage}"),
            "questions_asked": question_count,
            "max_questions": rules.get("max_questions", 3),
            "can_ask_question": question_count < rules.get("max_questions", 3)
        }

# Глобальный экземпляр контроллера
stage_controller = StageController()
