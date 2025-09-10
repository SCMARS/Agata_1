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
    """Контроллер стейджей общения с явным контролем и логами"""
    
    def __init__(self):
        self.config = living_chat_config
        self.stage_rules = self._load_stage_rules()
        self.user_stages = {}  
        self.user_question_counts = {}  
        self.user_last_activity = {}
        self.stage_files_cache = {}  # stage_number -> full_text
        logger.info("🎯 [STAGE] StageController ініціалізовано з кешем файлів")
        
    def _load_full_stage_content(self, stage_number: int) -> str:
        """Завантажує ПОВНИЙ текст стейджу з файлу для використання в промпті"""
        if stage_number in self.stage_files_cache:
            return self.stage_files_cache[stage_number]
            
        stage_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'stages 2', f'stage_{stage_number}.txt')
        
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
        
        # Ищем секцию "Вопросы по времени суток:"
        time_section_match = re.search(r'Вопросы по времени суток:\s*\n(.*?)(?=\n\n|\n[А-Я]|\Z)', content, re.DOTALL)
        if time_section_match:
            time_text = time_section_match.group(1)
            logger.info(f"🔍 [STAGE-{stage_number}] Найдена секция временных вопросов: {repr(time_text[:100])}")
            
            # Парсим строки вида "Утро: «...», «...»"
            for line in time_text.split('\n'):
                line = line.strip()
                if ':' in line and '«' in line:
                    time_period = line.split(':')[0].strip().lower()
                    questions_text = line.split(':', 1)[1]
                    
                    logger.info(f"🔍 [STAGE-{stage_number}] Обрабатываю строку: {repr(line)}")
                    logger.info(f"🔍 [STAGE-{stage_number}] time_period: '{time_period}'")
                    
                    # Извлекаем вопросы в кавычках
                    questions = re.findall(r'«([^»]+)»', questions_text)
                    if questions:
                        time_questions[time_period] = questions
                        logger.info(f"⏰ [STAGE-{stage_number}] {time_period}: {questions}")
        else:
            logger.warning(f"⚠️ [STAGE-{stage_number}] Секция 'Вопросы по времени суток:' НЕ найдена!")
        
        logger.info(f"⏰ [STAGE-{stage_number}] Итого временных вопросов: {time_questions}")
        return time_questions

    def _parse_daily_routine_from_stage(self, content: str, stage_number: int) -> str:
        """Парсит повседневность из стейджа"""
        import re
        
        logger.info(f"🔍 [STAGE-{stage_number}] Ищу повседневность в стейдже...")
        
        # Ищем секцию "Повседневность" (может быть "Повседневность\n" или "Распорядок дня")
        patterns = [
            r'Повседневность.*?\n((?:\d{2}:\d{2}.*?\n?)+)',
            r'Распорядок дня.*?\n((?:\d{2}:\d{2}.*?\n?)+)',
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
                        "slots": ["Общее приветствие", "Причина написать", "Первое впечатление"],
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
                            "Легкие комплименты",
                            "Касание к общим интересам",
                            "Проявление заинтересованности"
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
                            "Распорядок дня",
                            "Рабочие дела",
                            "Тренировки и здоровье",
                            "Вечерние планы"
                        ],
                        "completed": False
                    },
                    "Трейдинг": {
                        "slots": [
                            "Упоминание сделки (+300$)",
                            "Объяснение про ПУ аналитика",
                            "Рассказ о доходах",
                            "Мягкое предложение попробовать"
                        ],
                        "completed": False
                    },
                    "Романтика": {
                        "slots": [
                            "Касания о совместности",
                            "Намеки на близость",
                            "Флирт и комплименты",
                            "Создание интимности"
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

        current_time = datetime.now().strftime("%H:%M:%S")
        
        if user_id not in self.user_stages:
            self.user_stages[user_id] = 1
            logger.info(f"🎯 [{current_time}] [STAGE] Пользователь {user_id} начал стейдж 1 (Знакомство)")
        
        # Логика перехода между стейджами (исправлена согласно требованиям)
        if message_count <= 5:
            stage = 1
            stage_name = "Знакомство"
        elif message_count <= 15:
            stage = 2  
            stage_name = "Дружба/флирт"
        else:
            stage = 3
            stage_name = "Вброс"
            
        if self.user_stages[user_id] != stage:
            old_stage = self.user_stages[user_id]
            old_stage_names = {1: "Знакомство", 2: "Дружба/флирт", 3: "Вброс"}
            old_stage_name = old_stage_names.get(old_stage, f"Стейдж {old_stage}")
            
            self.user_stages[user_id] = stage
            logger.info(f"🔄 [{current_time}] [STAGE] Пользователь {user_id}:")
            logger.info(f"   📊 Сообщений: {message_count}")
            logger.info(f"   ⬆️  Переход: {old_stage_name} → {stage_name}")
            logger.info(f"   🎯 Новый стейдж: {stage} ({stage_name})")
        else:
            logger.info(f"📍 [{current_time}] [STAGE] Пользователь {user_id}: стейдж {stage} ({stage_name}), сообщений: {message_count}")
        
        return stage
    
    def should_ask_question(self, user_id: str, stage: int, last_question_time: Optional[datetime] = None) -> bool:
        """Определяет, нужно ли задать вопрос на текущем стейдже"""
        rules = self.stage_rules.get(stage, {})
        question_interval = rules.get("question_interval_seconds", 30)
        
        # Проверяем интервал между вопросами
        if last_question_time:
            time_since_last = datetime.now() - last_question_time
            if time_since_last.total_seconds() < question_interval:
                logger.info(f"⏰ [STAGE] Слишком рано для вопроса (прошло {time_since_last.total_seconds():.1f}с)")
                return False
        
        # Проверяем лимит вопросов
        question_count = self.user_question_counts.get(user_id, 0)
        max_questions = rules.get("max_questions", 3)
        
        if question_count >= max_questions:
            logger.info(f"❌ [STAGE] Достигнут лимит вопросов для стейджа {stage} ({question_count}/{max_questions})")
            return False
        
        logger.info(f"✅ [STAGE] Можно задать вопрос (стейдж {stage}, вопросов {question_count}/{max_questions})")
        return True
    
    def get_stage_question(self, user_id: str, stage: int) -> str:
        """Получает подходящий вопрос для стейджа"""
        rules = self.stage_rules.get(stage, {})
        required_questions = rules.get("required_questions", [])
        
        # Увеличиваем счетчик вопросов
        if user_id not in self.user_question_counts:
            self.user_question_counts[user_id] = 0
        self.user_question_counts[user_id] += 1
        
        # Выбираем вопрос
        if required_questions:
            question = required_questions[0]  # Берем первый из списка
            logger.info(f"❓ [STAGE] Выбран вопрос для стейджа {stage}: '{question}'")
            return question
        
        return "как дела?"
    
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
    
    def mark_question_asked(self, user_id: str):
        """Отмечает, что вопрос был задан"""
        if user_id not in self.user_question_counts:
            self.user_question_counts[user_id] = 0
        self.user_question_counts[user_id] += 1
        
        logger.info(f"[STAGE] Пользователю {user_id} задан вопрос #{self.user_question_counts[user_id]}")
    
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
        """Определяет следующую тему и слот для вопроса"""
        stage_rules = self.stage_rules.get(stage_number, {})
        themes = stage_rules.get("themes", {})
        
        # Ищем темы с незакрытыми слотами
        uncompleted_themes = []
        for theme_name, theme_data in themes.items():
            if not theme_data.get("completed", False):
                uncompleted_themes.append({
                    "theme_name": theme_name,
                    "slots": theme_data.get("slots", []),
                    "uncompleted_slots": len(theme_data.get("slots", []))
                })
        
        if not uncompleted_themes:
            return None
        
        # Приоритизируем темы с наибольшим числом незакрытых слотов
        next_theme = max(uncompleted_themes, key=lambda x: x["uncompleted_slots"])
        
        return {
            "theme_name": next_theme["theme_name"],
            "next_slot": next_theme["slots"][0] if next_theme["slots"] else None,
            "remaining_slots": next_theme["uncompleted_slots"]
        }
    
    def mark_slot_completed(self, user_id: str, stage_number: int, theme_name: str, slot: str):
        """Отмечает слот как завершенный"""
        # Здесь можно добавить логику для отслеживания завершенных слотов
        # Пока просто логируем
        logger.info(f"[STAGE] Пользователь {user_id} завершил слот '{slot}' в теме '{theme_name}' (этап {stage_number})")
    
    def get_time_based_questions(self, stage_number: int) -> Dict[str, List[str]]:
        """Повертає питання базовані на часі доби для поточного стейджу"""
        current_time = datetime.now().strftime("%H:%M:%S")
        logger.info(f"⏰ [{current_time}] [STAGE-{stage_number}] === ОТРИМАННЯ ЧАСОВИХ ПИТАНЬ ===")
        
        # Завантажуємо повний текст стейджу
        stage_content = self._load_full_stage_content(stage_number)
        
        # Парсим временные вопросы из стейджа
        stage_time_questions = self._parse_time_questions_from_stage(stage_content, stage_number)
        
        # Fallback значения если в стейдже нет временных вопросов
        default_questions = {
            "утро": ["Как спалось?", "Что планируешь сегодня?", "Завтракал?"],
            "день": ["Как проходит день?", "Что ел на обед?", "Много дел?"], 
            "вечер": ["Какие планы на вечер?", "Во сколько примерно ложишься спать?"]
        }
        
        # Используем временные вопросы из стейджа или fallback
        result_questions = stage_time_questions if stage_time_questions else default_questions
        
        logger.info(f"⏰ [{current_time}] [STAGE-{stage_number}] Загружено {len(result_questions)} групп временных вопросов:")
        for period, questions in result_questions.items():
            logger.info(f"   📅 {period}: {len(questions)} вопросов - {questions[:2]}...")
        
        return result_questions
    
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
