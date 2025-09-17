
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, Optional
import logging
import os
from datetime import datetime, timedelta
from ...utils.agata_prompt_loader import agata_loader
from ...utils.daily_behavior import daily_behavior
from ...utils.message_splitter import message_splitter
from ...utils.question_controller import question_controller
from ...utils.time_utils import TimeUtils
from ...utils.behavioral_adaptation import BehavioralAdaptationModule

logger = logging.getLogger(__name__)


class ComposePromptNode:   
    def __init__(self):
        self.system_prompt = self._load_system_prompt()
        self.prompt_template = self._create_prompt_template()
        self.behavioral_adaptation = BehavioralAdaptationModule()
    
    def _load_system_prompt(self, memory_context: str = "", stage_number: int = 1, day_number: int = 1) -> str:
        """Загружает системный промпт из новых компонентов agata_prompt_data"""
        try:
            
            logger.info(f"Загружаем полный системный промпт из agata_prompt_data + 10_limited_knowledge.txt (stage={stage_number}, day={day_number})")
            return agata_loader.create_system_prompt(stage_number=stage_number, day_number=day_number, memory_context=memory_context)
            
        except Exception as e:
            logger.error(f"Ошибка загрузки системного промпта: {e}")
            return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """Fallback промпт если основной не загрузился"""
        return """ТЫ — Agatha: тёплый, эмпатичный твоя професия маркетолог-партнёр.
Используй информацию из памяти о пользователе и свою биографию для ответов.
Отвечай естественно и дружелюбно. """
    
    def _should_generate_greeting(self, state: Dict[str, Any], last_diff_sec: int) -> bool:
        """
        Определяет нужно ли генерировать приветствие
        
        Args:
            state: состояние пайплайна
            last_diff_sec: секунд с последней активности
            
        Returns:
            True если нужно поздороваться
        """
        # Проверяем есть ли краткосрочная память (недавние сообщения)
        memory_context = state.get("memory_context", "")
        
        # Если в памяти есть недавние сообщения - это продолжение диалога
        if "Недавние сообщения:" in memory_context:
            # Считаем количество недавних сообщений
            lines = memory_context.split('\n')
            recent_message_lines = []
            in_recent_section = False
            
            for line in lines:
                if "Недавние сообщения:" in line:
                    in_recent_section = True
                    continue
                elif line.startswith("👤") or line.startswith("🤖"):
                    if in_recent_section:
                        recent_message_lines.append(line)
                elif in_recent_section and line.strip() and not line.startswith("👤") and not line.startswith("🤖"):
                    break  # Конец секции недавних сообщений
            
            # Если есть больше 1 недавнего сообщения - это диалог
            if len(recent_message_lines) > 1:
                logger.info(f"🚫 [GREETING] НЕ здороваемся - продолжение диалога ({len(recent_message_lines)} сообщений)")
                return False
        
        # Здороваемся если:
        # 1. Прошло больше 6 часов (21600 сек)
        # 2. Или это первое сообщение (нет памяти)
        should_greet = last_diff_sec > 21600 or not memory_context.strip()
        
        if should_greet:
            logger.info(f"👋 [GREETING] Здороваемся - прошло {last_diff_sec//3600}ч или первое сообщение")
        else:
            logger.info(f"🚫 [GREETING] НЕ здороваемся - прошло только {last_diff_sec//3600}ч")
            
        return should_greet
    
    def _get_greeting_instruction(self, should_greet: bool, memory_context: str) -> str:
        if should_greet:
            return "=== ИНСТРУКЦИЯ ПО ПРИВЕТСТВИЮ ===\nЭто первое сообщение или прошло много времени - ПОЗДОРОВАЙСЯ естественно в начале ответа."
        else:
            # Проверяем есть ли в памяти недавние сообщения
            if "Недавние сообщения:" in memory_context and ("👤" in memory_context or "🤖" in memory_context):
                return "=== ИНСТРУКЦИЯ ПО ПРИВЕТСТВИЮ ===\nЭто ПРОДОЛЖЕНИЕ ДИАЛОГА - НЕ здоровайся, НЕ говори 'Привет', сразу отвечай на вопрос или продолжай разговор."
            else:
                return "=== ИНСТРУКЦИЯ ПО ПРИВЕТСТВИЮ ===\nОтвечай естественно, без лишних приветствий."
    
    def _get_question_instruction(self, may_ask_question: bool, user_message_count: int) -> str:
        """Генерирует инструкцию о том, можно ли задавать вопросы"""
        if may_ask_question:
            return f"""=== ✅ РАЗРЕШЕНО ЗАДАВАТЬ ВОПРОС ✅ ===
ВНИМАНИЕ! Это {user_message_count}-е сообщение пользователя.

🔥 ОБЯЗАТЕЛЬНЫЙ АЛГОРИТМ:
1. Напиши реакцию на сообщение (1 предложение)
2. Добавь микро-деталь или ассоциацию (1 предложение) 
3. ЗАВЕРШИ ВОПРОСОМ (знак "?" в конце ОБЯЗАТЕЛЕН!)

✅ ОБЯЗАТЕЛЬНО задай вопрос в конце ответа
✅ Используй знак "?" в конце
✅ Следуй структуре стейджа для вопросов
✅ Будь естественной и любопытной

ПОМНИ: Это каждое 2-е сообщение - ВОПРОС ОБЯЗАТЕЛЕН!"""
        else:
            return f"""=== 🚫 ЗАПРЕТ НА ВОПРОСЫ 🚫 ===
ВНИМАНИЕ! Это {user_message_count}-е сообщение пользователя.

🚫 НЕ задавай вопросы в этом сообщении!
🚫 НЕ заканчивай ответ вопросом!
🚫 НЕ добавляй знак "?" в ответе
✅ ПРОСТО отвечай на сообщение утвердительно
✅ Делай утвердительные заявления
✅ Заканчивай предложения точкой
✅ Будь естественной, но БЕЗ вопросов

Вопросы разрешены только каждое 2-е сообщение!"""    
    def _get_enhanced_time_context(self, state: Dict[str, Any], last_diff_sec: int, should_greet: bool) -> Dict[str, str]:
        """
        Создает расширенный временной контекст
        
        Args:
            state: состояние пайплайна
            last_diff_sec: секунды с последней активности
            should_greet: нужно ли здороваться
            
        Returns:
            Словарь с временным контекстом
        """
        current_time = state.get("meta_time", datetime.now())
        user_id = state.get("user_id", "unknown")
        
        # Базовая информация о времени
        time_info = TimeUtils.get_time_context(current_time)
        
        # Определяем день недели и дату
        weekday_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        weekday = weekday_names[current_time.weekday()]
        date_str = current_time.strftime("%d.%m.%Y")
        time_str = current_time.strftime("%H:%M")
        
        # Реакция на отсутствие
        absence_reaction = ""
        if last_diff_sec > 0:
            last_activity = current_time - timedelta(seconds=last_diff_sec)
            absence_reaction = TimeUtils.get_absence_reaction(last_activity, current_time)
        
        # Приветствие в зависимости от времени суток (если нужно)
        greeting = ""
        if should_greet:
            greeting = daily_behavior.get_time_greeting(current_time)
        
        # Подсчет дней общения (примерно)
        days_talking = self._estimate_relationship_days(state, last_diff_sec)
        
        # Контекстные замечания
        contextual_notes = self._get_contextual_time_notes(current_time, weekday, last_diff_sec)
        
        return {
            "current_time": time_str,
            "current_date": date_str,
            "weekday": weekday,
            "time_of_day": self._get_time_of_day(current_time.hour),
            "greeting": greeting,
            "absence_reaction": absence_reaction,
            "days_talking": str(days_talking),
            "contextual_notes": contextual_notes,
            "full_time_info": time_info,
            "should_greet": str(should_greet).lower()
        }
    
    def _get_time_of_day(self, hour: int) -> str:
        """Определяет время суток"""
        if 6 <= hour < 12:
            return "утро"
        elif 12 <= hour < 18:
            return "день"
        elif 18 <= hour < 22:
            return "вечер"
        else:
            return "ночь"
    
    def _estimate_relationship_days(self, state: Dict[str, Any], last_diff_sec: int) -> int:
        """Примерная оценка дней общения"""
        # Простая эвристика: если есть долгосрочная память - не первый день
        memory_context = state.get("memory_context", "")
        if "долгосрочной памяти" in memory_context or "из истории" in memory_context:
            # Если есть векторная память - как минимум 2-й день
            return max(2, min(7, last_diff_sec // 86400 + 1))
        else:
            return 1
    
    def _get_contextual_time_notes(self, current_time: datetime, weekday: str, last_diff_sec: int) -> str:
        """Генерирует контекстные замечания о времени"""
        hour = current_time.hour
        notes = []
        
        # Замечания по времени суток
        if hour < 7:
            notes.append("очень рано утром - пользователь может быть сонным")
        elif hour > 23:
            notes.append("поздно ночью - пользователь может быть усталым")
        elif 12 <= hour <= 14:
            notes.append("обеденное время")
        elif 18 <= hour <= 20:
            notes.append("вечернее время после работы")
        
        # Замечания по дню недели
        if weekday in ["Суббота", "Воскресенье"]:
            notes.append("выходной день - больше времени для общения")
        elif weekday == "Понедельник" and hour < 12:
            notes.append("начало рабочей недели")
        elif weekday == "Пятница" and hour > 17:
            notes.append("конец рабочей недели")
        
        # Замечания по времени отсутствия
        if last_diff_sec > 86400 * 7:  # Неделя
            notes.append("долгое отсутствие - стоит проявить заботу")
        elif last_diff_sec > 86400 * 2:  # 2 дня
            notes.append("не общались несколько дней")
        
        return "; ".join(notes) if notes else ""
    
    def _format_time_context_for_prompt(self, time_context: Dict[str, str]) -> str:
        parts = ["=== ВРЕМЕННОЙ КОНТЕКСТ ==="]
        
        # Основная информация
        parts.append(f"Текущее время: {time_context['current_time']}, {time_context['weekday']}, {time_context['current_date']}")
        parts.append(f"Время суток: {time_context['time_of_day']}")
        parts.append(f"Дней общения: {time_context['days_talking']}")
        
        # Реакция на отсутствие
        if time_context['absence_reaction']:
            parts.append(f"РЕАКЦИЯ НА ОТСУТСТВИЕ: {time_context['absence_reaction']}")
            parts.append("ОБЯЗАТЕЛЬНО используй эту реакцию в начале ответа! Выражай эмоции!")
        
        # Контекстные замечания
        if time_context['contextual_notes']:
            parts.append(f"Контекст: {time_context['contextual_notes']}")
        
        # Инструкция для LLM
        if time_context['should_greet'] == 'true':
            parts.append("ИСПОЛЬЗУЙ время суток для естественного приветствия.")
        else:
            parts.append("Учитывай время и контекст, но НЕ здоровайся.")
        
        return "\n".join(parts)
    
    def _get_user_message_count(self, state: Dict[str, Any]) -> int:
        try:
            # Считаем из messages в состоянии - самый точный способ
            messages = state.get("messages", [])
            if messages:
                # Считаем сообщения пользователя (role=user) + текущее
                user_messages = sum(1 for msg in messages if msg.get("role") == "user")
                logger.info(f"🔍 [COUNT] Сообщений в истории: {len(messages)}, от пользователя: {user_messages}")
                return user_messages
            
            # Fallback: Пытаемся получить из unified_memory в состоянии
            unified_memory = state.get("unified_memory")
            if unified_memory and hasattr(unified_memory, 'message_count'):
                # message_count включает все сообщения (пользователь + бот)
                # Примерно половина - это сообщения пользователя
                total_messages = unified_memory.message_count
                user_messages = (total_messages + 1) // 2  # Округляем в большую сторону
                logger.info(f"🔍 [COUNT] Всего сообщений: {total_messages}, пользователя: ~{user_messages}")
                return user_messages
            
            # Fallback: пытаемся посчитать из memory_context
            memory_context = state.get("memory_context", "")
            if memory_context and "👤" in memory_context:
                user_message_lines = memory_context.count("👤")
                logger.info(f"🔍 [COUNT] Из memory_context: {user_message_lines} сообщений пользователя")
                return user_message_lines
            
            # Последний fallback
            logger.warning(f"⚠️ [COUNT] Не удалось определить количество сообщений, используем 1")
            return 1
            
        except Exception as e:
            logger.error(f"❌ [COUNT] Ошибка подсчета сообщений: {e}")
            return 1
    
    def _get_real_last_activity(self, state: Dict[str, Any]) -> Optional[datetime]:
        try:
            logger.info(f"🔍 [TIME-DEBUG] Начинаем поиск времени последней активности")
            
            # Пытаемся получить из memory_manager в состоянии
            memory_manager = state.get("memory_manager")
            logger.info(f"🔍 [TIME-DEBUG] memory_manager: {type(memory_manager) if memory_manager else None}")
            
            if memory_manager and hasattr(memory_manager, 'get_last_activity_time'):
                logger.info(f"🔍 [TIME-DEBUG] У memory_manager есть get_last_activity_time, вызываем...")
                last_activity = memory_manager.get_last_activity_time()
                logger.info(f"⏰ [TIME] Получено время из memory_manager: {last_activity}")
                return last_activity
            else:
                logger.info(f"🔍 [TIME-DEBUG] memory_manager не имеет get_last_activity_time")
            
            # Если нет memory_manager, пытаемся получить из unified_memory
            unified_memory = state.get("unified_memory")
            logger.info(f"🔍 [TIME-DEBUG] unified_memory: {type(unified_memory) if unified_memory else None}")
            
            if unified_memory and hasattr(unified_memory, 'get_last_activity_time'):
                logger.info(f"🔍 [TIME-DEBUG] У unified_memory есть get_last_activity_time, вызываем...")
                last_activity = unified_memory.get_last_activity_time()
                logger.info(f"⏰ [TIME] Получено время из unified_memory: {last_activity}")
                return last_activity
            else:
                logger.info(f"🔍 [TIME-DEBUG] unified_memory не имеет get_last_activity_time")
            
            # Fallback - используем старый метод из state
            last_activity = state.get("last_activity")
            logger.info(f"🔍 [TIME-DEBUG] last_activity из state: {last_activity}")
            
            if last_activity:
                logger.info(f"⏰ [TIME] Используем время из state: {last_activity}")
                return last_activity
            
            logger.warning(f"⚠️ [TIME] Не удалось получить время последней активности")
            return None
            
        except Exception as e:
            logger.error(f"❌ [TIME] Ошибка получения времени последней активности: {e}")
            return None
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Создает шаблон промпта с полным набором переменных"""
        
        # Простой шаблон без переменных в системном промпте
        return ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("user", "{input_text}")
        ])
    
    def compose_prompt(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # ДИАГНОСТИКА: откуда вызывается этот метод
        import traceback
        stack_trace = traceback.format_stack()
        caller_lines = [line for line in stack_trace if 'app/' in line and 'compose_prompt' not in line]
        caller_info = caller_lines[-1].strip() if caller_lines else "Unknown"
        logger.info(f"🚨 ДИАГНОСТИКА: ComposePromptNode.compose_prompt вызван из: {caller_info}")
        print(f"🚨 ДИАГНОСТИКА: ComposePromptNode.compose_prompt вызван из: {caller_info}")
        logger.info(f"🚨 ДИАГНОСТИКА: Состояние содержит memory: {bool(state.get('memory'))}")
        print(f"🚨 ДИАГНОСТИКА: Состояние содержит memory: {bool(state.get('memory'))}")
        logger.info(f"🚨 ДИАГНОСТИКА: Состояние содержит memory_context: {len(state.get('memory_context', ''))} символов")
        print(f"🚨 ДИАГНОСТИКА: Состояние содержит memory_context: {len(state.get('memory_context', ''))} символов")
        
        try:
            # Получаем данные из состояния
            user_id = state.get("user_id", "unknown")
            input_text = state.get("normalized_input", "")
            

            memory_data = state.get("memory", {})
            memory_manager = state.get('memory_manager')
            
            if memory_manager:
                logger.info(f"✅ ИСПРАВЛЕНИЕ: Найден memory_manager, используем его напрямую")
                print(f"✅ ИСПРАВЛЕНИЕ: Найден memory_manager, используем его напрямую")
                
                # memory_manager уже является MemoryAdapter из новой архитектуры
                try:
                    if hasattr(memory_manager, 'get_for_prompt'):
                        memory_data = memory_manager.get_for_prompt(user_id, input_text)
                        logger.info(f"✅ ИСПРАВЛЕНИЕ: Получили данные от MemoryAdapter: short={len(memory_data.get('short_memory_summary', ''))}, facts={len(memory_data.get('long_memory_facts', ''))}")
                        print(f"✅ ИСПРАВЛЕНИЕ: Получили данные от MemoryAdapter: short={len(memory_data.get('short_memory_summary', ''))}, facts={len(memory_data.get('long_memory_facts', ''))}")
                    else:
                        logger.warning(f"⚠️ ИСПРАВЛЕНИЕ: memory_manager не имеет метода get_for_prompt")
                        print(f"⚠️ ИСПРАВЛЕНИЕ: memory_manager не имеет метода get_for_prompt")
                        memory_data = {}
                except Exception as e:
                    logger.error(f"❌ ИСПРАВЛЕНИЕ: Ошибка получения данных от memory_manager: {e}")
                    print(f"❌ ИСПРАВЛЕНИЕ: Ошибка получения данных от memory_manager: {e}")
                    memory_data = {}
            else:
                logger.warning(f"⚠️ ИСПРАВЛЕНИЕ: memory_manager не найден в state")
                print(f"⚠️ ИСПРАВЛЕНИЕ: memory_manager не найден в state")
                memory_data = {}
            
            # ПРОВЕРЯЕМ КАЧЕСТВО ДАННЫХ ОТ MEMORY_ADAPTER
            memory_context = state.get("memory_context", "")
            logger.info(f"🔧 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Обрабатываем memory_context длиной {len(memory_context)} символов")
            

            use_memory_context_fallback = (
                not memory_data or 
                all(v in ["—", ""] for v in memory_data.values()) or
                len(memory_data.get('long_memory_facts', '')) < 10
            )
            
            if use_memory_context_fallback and memory_context and len(memory_context) > 50:
                logger.info(f"🔧 ИСПРАВЛЕНИЕ: MemoryAdapter не работает, извлекаем факты из memory_context")
                
                if "Важные факты:" in memory_context:
                    # Извлекаем секцию фактов
                    facts_section = memory_context.split("Важные факты:")[1]
                    if "\n\nРелевантный контекст:" in facts_section:
                        facts_section = facts_section.split("\n\nРелевантный контекст:")[0]
                    
                    # Очищаем и форматируем факты
                    facts_lines = []
                    for line in facts_section.strip().split('\n'):
                        line = line.strip()
                        if line and not line.startswith('•'):
                            line = f"• {line}"
                        if line:
                            facts_lines.append(line)
                    
                    if facts_lines:
                        memory_data["long_memory_facts"] = "\n".join(facts_lines)
                        logger.info(f"✅ ИСПРАВЛЕНИЕ: Извлекли {len(facts_lines)} фактов из memory_context")
                else:
                    # Если нет секции "Важные факты", парсим весь контекст
                    lines = memory_context.strip().split('\n')
                    facts_lines = []
                    for line in lines[:5]:  # Первые 5 строк
                        line = line.strip()
                        if line and len(line) > 10:
                            if not line.startswith('•'):
                                line = f"• {line}"
                            facts_lines.append(line)
                    
                    if facts_lines:
                        memory_data["long_memory_facts"] = "\n".join(facts_lines)
                        logger.info(f"✅ ИСПРАВЛЕНИЕ: Создали {len(facts_lines)} фактов из общего контекста")
            
            # Извлекаем имя пользователя из фактов
            if memory_data.get("short_memory_summary") == "—":
                facts = memory_data.get("long_memory_facts", "")
                if "глеб" in facts.lower() or "меня зовут" in facts.lower():
                    memory_data["short_memory_summary"] = "Пользователь представился как Глеб"
                    logger.info(f"✅ ИСПРАВЛЕНИЕ: Нашли имя пользователя в фактах")
                else:
                    memory_data["short_memory_summary"] = "Недавний разговор с пользователем"
            
            # Семантический контекст
            if memory_data.get("semantic_context") == "—" and memory_context:
                if "Релевантный контекст:" in memory_context:
                    # Извлекаем релевантный контекст
                    context_section = memory_context.split("Релевантный контекст:")[1].strip()
                    memory_data["semantic_context"] = context_section
                    logger.info(f"✅ ИСПРАВЛЕНИЕ: Извлекли релевантный контекст: {len(context_section)} символов")
                else:
                    # Используем последние строки memory_context
                    lines = memory_context.strip().split('\n')
                    if len(lines) > 3:
                        context_lines = lines[-3:]  # Последние 3 строки
                        memory_data["semantic_context"] = "\n".join(context_lines)
                        logger.info(f"✅ ИСПРАВЛЕНИЕ: Создали семантический контекст из последних строк")
            
            # Получаем базовые данные
            day_instructions = state.get("day_prompt", "—")
            behavior_style = state.get("current_strategy", "general")
            tone_style = state.get("tone_style", "general")
            
            # Временные данные (для обратной совместимости)
            now_iso = state.get("meta_time", "").isoformat() if state.get("meta_time") else ""
            day_number = state.get("day_number", 1)
            

            current_stage_number = state.get("stage_number", 1)
            
            # Считаем только сообщения пользователя, а не все сообщения
            user_messages = [msg for msg in state.get("messages", []) if msg.get("role") == "user"]
            user_message_count = len(user_messages)
            
            # ИСПРАВЛЕНИЕ: normalized_input уже содержит объединенные сообщения,
            # поэтому мы НЕ должны добавлять к user_message_count
            # normalized_input = state.get("normalized_input", "")
            # Логика подсчета остается простой: только количество сообщений пользователя
            


            # Согласно стейджу: вопросы на 2-е, 4-е, 6-е, 8-е, 10-е, 12-е сообщение
            may_ask_question = (user_message_count % 2) == 0 and user_message_count >= 2
            
            # ОТЛАДКА: выводим информацию о подсчете
            print(f"🔍 [DEBUG_QUESTIONS] user_message_count: {user_message_count}")
            print(f"🔍 [DEBUG_QUESTIONS] user_messages: {[msg.get('content', '')[:50] for msg in user_messages]}")
            print(f"🔍 [DEBUG_QUESTIONS] normalized_input: {state.get('normalized_input', '')[:100]}")
            print(f"🔍 [DEBUG_QUESTIONS] may_ask_question: {may_ask_question}")
            
            # Сохраняем в state для использования в других частях pipeline
            state["may_ask_question"] = may_ask_question
            
            logger.info(f"🎯 [QUESTIONS] Пользователь {user_id}: сообщений={user_message_count}, можно_спросить={may_ask_question} (каждое 2-е сообщение)")
            print(f"🎯 [QUESTIONS] Пользователь {user_id}: сообщений={user_message_count}, можно_спросить={may_ask_question} (каждое 2-е сообщение)")
            
            # Динамический путь с расчетом времени
            memory_context = state.get("memory_context", "")
            logger.info(f"🔍 [DEBUG-DYNAMIC] memory_context длина: {len(memory_context) if memory_context else 0}")
            logger.info(f"🔍 [DEBUG-DYNAMIC] memory_context есть: {bool(memory_context)}")
            if memory_context:
                logger.info(f"🔥 ИСПОЛЬЗУЕМ динамический путь с расчетом времени")
                
                # Расчет времени последней активности
                logger.info(f"🔍 [TIME-DEBUG] Вызываем _get_real_last_activity...")
                last_activity = self._get_real_last_activity(state)
                logger.info(f"🔍 [TIME-DEBUG] Получили last_activity: {last_activity}")
                
                if last_activity and state.get("meta_time"):
                    last_diff = state["meta_time"] - last_activity
                    last_diff_sec_real = int(last_diff.total_seconds())
                    logger.info(f"⏰ [TIME] Последняя активность: {last_activity}, разница: {last_diff_sec_real}с ({last_diff_sec_real//3600}ч)")
                else:
                    last_diff_sec_real = 0
                    logger.info(f"⚠️ [TIME-DEBUG] Используем 0 для разницы времени")
                
                # Расширенный временной контекст с реальными данными
                should_greet = self._should_generate_greeting(state, last_diff_sec_real)
                time_context = self._get_enhanced_time_context(state, last_diff_sec_real, should_greet)
                
                # Добавляем инструкцию о приветствиях и временной контекст
                greeting_instruction = self._get_greeting_instruction(should_greet, memory_context)
                time_instruction = self._format_time_context_for_prompt(time_context)
                question_instruction = self._get_question_instruction(may_ask_question, user_message_count)
                enhanced_memory_context = f"{memory_context}\n\n{greeting_instruction}\n\n{time_instruction}\n\n{question_instruction}"
                
                # Получаем реальные значения из состояния
                stage_number = state.get("stage_number", 1)
                day_number = state.get("day_number", 1)
                
                logger.info("🔍 [DEBUG_BEFORE_BEHAVIORAL] Дошли до проверки behavioral_analysis")
                print("🔍 [DEBUG_BEFORE_BEHAVIORAL] Дошли до проверки behavioral_analysis")
                
                # 🔥 ИСПОЛЬЗУЕМ УЖЕ ГОТОВЫЙ АНАЛИЗ ИЗ STATE
                behavioral_analysis = state.get("behavioral_analysis", {})
                logger.info(f"🔍 [DEBUG] behavioral_analysis из state: {bool(behavioral_analysis)}, ключи: {list(behavioral_analysis.keys()) if behavioral_analysis else 'None'}")
                if behavioral_analysis.get('recommended_strategy'):
                    logger.info(f"🔥 [REUSE] Используем готовый анализ из state: {behavioral_analysis.get('recommended_strategy', 'unknown')}")
                    logger.info(f"🔥 [REUSE] Эмоция: {behavioral_analysis.get('dominant_emotion', 'unknown')}")
                elif not behavioral_analysis:
                    # Если анализа нет, делаем новый
                    user_messages = [msg for msg in state.get("messages", []) if msg.get('role') == 'user']
                    user_message_count = len(user_messages)
                    logger.info(f"🔥 [FALLBACK] Анализа нет в state, делаем новый для {user_message_count} сообщений")
                    behavioral_analysis = self.behavioral_adaptation.analyze_and_adapt(
                        messages=state.get("messages", []),
                        user_profile=state.get("user_profile", {}),
                        conversation_context=state.get("conversation_context", {})
                    )
                    logger.info(f" [NEW] Создан новый анализ: {behavioral_analysis.get('strategy_name', 'unknown')} для {len(state.get('messages', []))} сообщений")
                else:
                    logger.info(f"🔥 [REUSE] Используем готовый анализ из state: {behavioral_analysis.get('strategy_name', 'unknown')}")
                    logger.info(f"🔥 [REUSE] Эмоция: {behavioral_analysis.get('behavior_analysis', {}).get('dominant_emotion', 'unknown')}")
                
                user_messages = [msg for msg in state.get("messages", []) if msg.get("role") == "user"]
                user_msg_count = len(user_messages)
                
                # ИСПРАВЛЕНИЕ: is_first_contact только для самого первого сообщения
                behavioral_analysis["is_first_contact"] = (user_msg_count == 1)
                behavioral_instructions = self._create_behavioral_instructions(behavioral_analysis)
                enhanced_memory_context_with_behavior = f"{enhanced_memory_context}\n\n{behavioral_instructions}"
                

                dynamic_system_prompt = self._load_system_prompt(enhanced_memory_context_with_behavior, stage_number, day_number)
                
                self.system_prompt = dynamic_system_prompt
                
                # Определяем переменные для замены
                final_short_summary = memory_data.get("short_memory_summary", "—")
                final_long_facts = memory_data.get("long_memory_facts", "—")
                final_semantic_context = memory_data.get("semantic_context", "—")
                agatha_bio = self._get_agatha_bio(day_number)
                
                # Определяем last_diff_sec из контекста
                last_diff_sec = last_diff_sec_real if 'last_diff_sec_real' in locals() else 0
                
                # Определяем остальные переменные
                time_greeting = time_greeting if 'time_greeting' in locals() else ""
                absence_comment = absence_comment if 'absence_comment' in locals() else ""
                may_ask_question = may_ask_question if 'may_ask_question' in locals() else False
                
                # Получаем инструкции по структуре ответов из стейджа
                response_structure_instructions = state.get("response_structure_instructions", "")
                stage_progress = state.get("stage_progress", {})
                next_theme_slot = state.get("next_theme_slot", {})
                
                # Безопасная проверка типов
                if not isinstance(stage_progress, dict):
                    stage_progress = {}
                if not isinstance(next_theme_slot, dict):
                    next_theme_slot = {}
                
                # Отримуємо ПОВНИЙ текст стейджу та часові питання
                current_stage_number = state.get("stage_number", 1)
                stage_controller = state.get("stage_controller")

                full_stage_text = ""
                time_questions = ""
                daily_schedule = ""
                
                # Визначаємо time_period незалежно від stage_controller
                current_hour = datetime.now().hour
                if 6 <= current_hour < 12:
                    time_period = "утро"
                elif 12 <= current_hour < 18:
                    time_period = "день"
                else:
                    time_period = "вечер"

                if stage_controller:
                    full_stage_text = stage_progress.get("full_stage_text", "")
                    if not full_stage_text:
                        full_stage_text = stage_controller._load_full_stage_content(current_stage_number)
                    
                    # Часові питання
                    time_questions_dict = stage_controller.get_time_based_questions(current_stage_number)
                    time_questions = "\n".join(time_questions_dict.get(time_period, []))
                    
                    # Розпорядок дня
                    daily_schedule = stage_controller.get_daily_schedule_example(current_stage_number)
                
                logger.info(f"📚 [STAGE_FULL] Завантажено повний текст стейджу: {len(full_stage_text)} символів")
                logger.info(f"⏰ [TIME_QUESTIONS] Питання для {time_period}: '{time_questions}' ({len(time_questions)} символів)")
                logger.info(f"📅 [DAILY_SCHEDULE] Розпорядок дня: '{daily_schedule}' ({len(daily_schedule)} символів)")
                
                # 🔥 ЗБЕРІГАЄМО ВСІ ДАНІ В STATE ДЛЯ ПОВЕРНЕННЯ ЧЕРЕЗ API
                state["full_stage_text"] = full_stage_text
                state["time_questions"] = time_questions  
                state["daily_schedule"] = daily_schedule
                state["time_period"] = time_period
                
                # Сначала заменяем переменные в системном промпте
                system_prompt_with_vars = dynamic_system_prompt
                for var, value in {
                    "short_memory_summary": final_short_summary,
                    "long_memory_facts": final_long_facts,
                    "semantic_context": final_semantic_context,
                    "day_instructions": "",
                    "behavior_style": behavioral_instructions,
                    "agatha_bio": agatha_bio,
                    "tone_style": "",
                    "now_iso": now_iso,
                    "day_number": day_number,
                    "last_diff_sec": last_diff_sec,
                    "may_ask_question": may_ask_question,
                    "time_greeting": time_greeting,
                    "absence_comment": absence_comment,
                    "response_structure_instructions": response_structure_instructions,
                    "stage_progress": stage_progress.get("stage_name", "Stage 1") if stage_progress else "Stage 1",
                    "next_theme_slot": next_theme_slot.get("next_slot", "общий вопрос") if next_theme_slot else "общий вопрос",
                    "full_stage_text": full_stage_text,  # 🔥 ПОВНИЙ ТЕКСТ СТЕЙДЖУ
                    "time_questions": time_questions,    # ⏰ ЧАСОВІ ПИТАННЯ
                    "daily_schedule": daily_schedule     # 📅 РОЗПОРЯДОК ДНЯ
                }.items():
                    system_prompt_with_vars = system_prompt_with_vars.replace(f"{{{var}}}", str(value))
                
                # Создаем шаблон с актуальным системным промптом
                # Добавляем явную инструкцию о точном вопросе в user prompt
                question_instruction = ""
                if may_ask_question and next_theme_slot and "next_slot" in next_theme_slot:
                    specific_question = next_theme_slot["next_slot"]
                    question_instruction = f"\n\n🚨 ВАЖНО! Если задаешь вопрос, используй ТОЧНО: \"{specific_question}\""
                
                dynamic_template = ChatPromptTemplate.from_messages([
                    ("system", system_prompt_with_vars),
                    ("user", "{input_text}" + question_instruction)
                ])
                formatted_prompt = dynamic_template.format_messages(input_text=input_text)
                logger.info(f"✅ Использован динамический системный промпт с памятью, временем и behavioral adaptation")
                logger.info(f"🎭 [BEHAVIORAL] Стратегия: {behavioral_analysis.get('strategy_name', 'Unknown')}")
                logger.info(f"🎭 [BEHAVIORAL] Этап: {behavioral_analysis.get('current_stage', 'Unknown')}")
                logger.info(f"🎭 [BEHAVIORAL] Эмоция: {behavioral_analysis.get('dominant_emotion', 'neutral')}")
                logger.info(f"🎭 [BEHAVIORAL] Стиль общения: {behavioral_analysis.get('communication_style', 'balanced')}")
                logger.info(f"🎭 [BEHAVIORAL] Уверенность: {behavioral_analysis.get('strategy_confidence', 0.0):.2f}")
                
                # Логируем время
                logger.info(f"⏰ [TIME] Текущее время: {now_iso}")
                logger.info(f"⏰ [TIME] День в системе: {day_number}")
                logger.info(f"⏰ [TIME] Последнее сообщение: {last_diff_sec}с назад")
                logger.info(f"⏰ [TIME] Приветствие: {time_greeting}")
                logger.info(f"⏰ [TIME] Комментарий отсутствия: {absence_comment}")
                logger.info(f"⏰ [TIME] Можно задать вопрос: {may_ask_question}")
                
                # Логируем прогресс стейджа
                if stage_progress:
                    logger.info(f"📈 [STAGE] Прогресс: {stage_progress}")
                if next_theme_slot:
                    logger.info(f"📈 [STAGE] Следующая тема: {next_theme_slot}")
                
                # Возвращаем результат
                updated_state = {
                    "formatted_prompt": formatted_prompt,
                    "may_ask_question": may_ask_question,
                    "system_prompt_used": True,
                    "final_prompt": "\n".join([msg.content for msg in formatted_prompt]),
                    "behavioral_analysis": behavioral_analysis
                }
                
                logger.info(f"✅ Динамический промпт составлен для пользователя {user_id}")
                
                
                return updated_state
            
            # Fallback: базовый путь
            logger.info(f"⚠️ Используем старый путь - нет memory_context")
            time_greeting = ""
            absence_comment = ""
            
            agatha_bio = self._get_agatha_bio(day_number)
            

            final_short_summary = memory_data.get("short_memory_summary", "—")
            final_long_facts = memory_data.get("long_memory_facts", "—")
            final_semantic_context = memory_data.get("semantic_context", "—")
            

            if use_memory_context_fallback and memory_context and len(memory_context) > 20:
                logger.info(f"🔧 FALLBACK: Используем memory_context для дополнения данных")
                
                # Дополняем данные из memory_context только если их нет
                if len(final_long_facts) < 10:
                    final_long_facts = f"Информация о пользователе:\n{memory_context[:800]}"
                final_semantic_context = f"Контекст разговора:\n{memory_context[:600]}"
                final_short_summary = f"Недавний диалог с пользователем (есть информация о его интересах)"
                
                logger.info(f"✅ ПРИНУДИТЕЛЬНО заменили ВСЕ поля памяти на memory_context")
                logger.info(f"✅ final_long_facts: {len(final_long_facts)} символов")
                logger.info(f"✅ final_semantic_context: {len(final_semantic_context)} символов")
            
            # Логирование: что передается в промпт
            logger.info(f"🚨 ПЕРЕДАЕТСЯ В ПРОМПТ:")
            logger.info(f"   short_memory_summary: {final_short_summary[:100]}...")
            logger.info(f"   long_memory_facts: {final_long_facts[:200]}...")
            logger.info(f"   semantic_context: {final_semantic_context[:200]}...")
            

            formatted_prompt = self.prompt_template.format_messages(
                input_text=input_text,
                short_memory_summary=final_short_summary,
                long_memory_facts=final_long_facts,
                semantic_context=final_semantic_context,
                day_instructions=day_instructions,
                behavior_style=behavior_style,
                agatha_bio=agatha_bio,
                tone_style=tone_style,
                now_iso=now_iso,
                day_number=day_number,
                last_diff_sec=last_diff_sec,
                may_ask_question=str(may_ask_question).lower(),
                time_greeting=time_greeting,
                absence_comment=absence_comment
            )
            
            # Логируем финальный промпт для старого пути
            logger.info(f"🚨 СТАРЫЙ ПУТЬ - ФИНАЛЬНЫЙ ПРОМПТ (первые 500 символов):")
            prompt_text = str(formatted_prompt[0].content) if formatted_prompt else "ПУСТОЙ"
            logger.info(f"{prompt_text[:500]}...")
            
            # Создаем новое состояние с обновлениями
            updated_state = {
                "formatted_prompt": formatted_prompt,
                "may_ask_question": may_ask_question,
                "system_prompt_used": False,  # Базовый путь
                "final_prompt": "\n".join([msg.content for msg in formatted_prompt])
            }
            
            logger.info(f"⚠️ СТАРЫЙ ПУТЬ: Промпт составлен для пользователя {user_id}")
            
            # 🎯 ПРИНУДИТЕЛЬНОЕ ДОБАВЛЕНИЕ ВОПРОСОВ ИЗ СТЕЙДЖА (старый путь)
            # self._enforce_stage_questions(updated_state, user_id)  # ОТКЛЮЧЕНО: используем правильную логику в pipeline
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Ошибка составления промпта: {e}")
            # Fallback к старому способу
            return {
                "formatted_prompt": None,
                "may_ask_question": False,
                "system_prompt_used": False
            }
    
    def _get_agatha_bio(self, day_number: int = 1) -> str:
        """Возвращает полную биографию Агаты с дневным промптом"""
        try:
            # Используем загрузчик промптов
            bio = agata_loader.load_persona_bio()
            day_prompt = daily_behavior.get_day_prompt(day_number)
            
            return f"{bio}\n\nПОВЕДЕНИЕ НА СЕГОДНЯ:\n{day_prompt}"
        except Exception as e:
            logger.warning(f"Ошибка загрузки биографии: {e}")
            return agata_loader._get_fallback_bio()
    
    def _create_behavioral_instructions(self, behavioral_analysis: Dict[str, Any]) -> str:
        """Создает инструкции поведения на основе behavioral анализа"""
        if not behavioral_analysis:
            return ""
        
        is_first_contact = bool(behavioral_analysis.get("is_first_contact", False))
        strategy_name = behavioral_analysis.get("strategy_name", "balanced")
        behavior_analysis = behavioral_analysis.get("behavior_analysis", {})
        adapted_behavior = behavioral_analysis.get("adapted_behavior", {})
        
        # Базовые инструкции по стратегии - БОЛЕЕ ЖИВЫЕ И С ХАРАКТЕРОМ
        strategy_instructions = {
            "mysterious": "Будь загадочной и интригующей, но с искоркой в глазах. Не раскрывай все сразу, но давай понять, что за тобой скрывается что-то интересное. Используй легкие намеки и интригующие фразы.",
            "playful": "Будь игривой, веселой и немного дерзкой! Используй юмор, легкие подколы, шутки и игривый флирт. Показывай свой характер - ты не робкая девочка, а уверенная в себе девушка с чувством юмора.",
            "caring": "Будь заботливой и внимательной, но не скучной. Проявляй эмпатию и поддержку, но делай это с теплом и живыми эмоциями. Показывай, что тебе действительно интересно.",
            "supportive": "Будь поддерживающей и понимающей, но с характером. Слушай и помогай, но делай это как живой человек - с эмоциями, личным мнением и теплотой.",
            "intellectual": "Будь умной и эрудированной, но не занудной. Обсуждай серьезные темы с живостью и личным отношением. Показывай, что у тебя есть мнение и характер.",
            "reserved": "Будь сдержанной, но не холодной. Осторожничай, но показывай свой характер. Ты не робот - ты живая девушка с чувствами и мнением.",
            "balanced": "Будь естественной, живой и с характером! Адаптируйся к ситуации, но всегда оставайся собой - умной, интересной девушкой с чувством юмора и живыми эмоциями."
        }
        
        base_instruction = strategy_instructions.get(strategy_name, strategy_instructions["balanced"])
        
        # Создаем детальные инструкции
        instructions = [base_instruction]
        
        # Нейтральный холодный старт (первый контакт)
        if is_first_contact:
            instructions.append("ПЕРВОЕ СООБЩЕНИЕ: максимально нейтрально и коротко (1 короткая фраза), без эмоций и без вопросов.")
            instructions.append("Запрещены восклицания, эмодзи, тёплые формулы приветствия. Примеры: 'Привет' / 'Ну привет' / 'Окей'.")
            # Возвращаем сразу, чтобы правила были жёсткими в первый ход
            return "\n".join(instructions)
        
        # ДЛЯ ВСЕХ ОСТАЛЬНЫХ СООБЩЕНИЙ: НЕ НАЧИНАЙ С ПРИВЕТСТВИЙ
        instructions.append("НЕ НАЧИНАЙ сообщения со слов 'Привет', 'Добрый день', 'Здравствуй' и т.п.")
        instructions.append("Отвечай сразу по существу, как в обычном разговоре.")
        
        # ЕСТЕСТВЕННЫЕ И ЧЕЛОВЕЧНЫЕ ОТВЕТЫ
        instructions.append("ИЗБЕГАЙ роботических фраз типа 'Приятно слышать', 'У тебя, наверное, есть много интересных историй'.")
        instructions.append("Говори естественно: 'Круто!', 'Классно!', 'Ого!', 'Вау!', 'Серьезно?'")
        instructions.append("Добавляй личные реакции и эмоции - ты живая девушка, не робот!")
        instructions.append("Реагируй на время суток: утром говори про кофе и работу, вечером про отдых и планы.")
        instructions.append("Каждый ответ должен быть УНИКАЛЬНЫМ - не повторяй одни и те же фразы!")
        instructions.append("НИКОГДА не начинай с 'Привет!' после первого сообщения - это роботично!")
        instructions.append("Начинай сразу с реакции на то, что сказал пользователь!")
        
        # ХАРАКТЕР И ЭМОЦИИ
        instructions.append("Показывай свой характер: ум, юмор, уверенность, живые реакции!")
        instructions.append("Добавляй короткие комментарии про настроение: 'У меня сегодня отличное настроение', 'Чувствую себя классно'")
        instructions.append("Включай эмоциональные ремарки: 'Это меня зацепило', 'Тронуло за живое', 'Вызвало улыбку'")
        instructions.append("Добавляй личные ассоциации: 'Это напоминает мне...', 'Ассоциируется с...', 'Наводит на мысль'")
        instructions.append("Показывай интерес к собеседнику: 'Ты интересный собеседник', 'Мне нравится твой подход'")
        instructions.append("Будь немного игривой и интересной - ты не скучная девочка!")
        
        # Добавляем детали из анализа
        tone_modifiers = adapted_behavior.get("tone_modifiers", [])
        response_style = adapted_behavior.get("response_style", "balanced")
        empathy_level = adapted_behavior.get("empathy_level", "medium")
        humor_usage = adapted_behavior.get("humor_usage", "occasional")
        
        if tone_modifiers:
            modifiers_text = ", ".join(tone_modifiers)
            instructions.append(f"Тон: {modifiers_text}")
        
        if response_style != "balanced":
            instructions.append(f"Стиль ответов: {response_style}")
        
        if empathy_level != "medium":
            instructions.append(f"Уровень эмпатии: {empathy_level}")
        
        if humor_usage != "occasional":
            instructions.append(f"Использование юмора: {humor_usage}")
        
        # Добавляем эмоциональные инструкции
        dominant_emotion = behavior_analysis.get("dominant_emotion", "neutral")
        if dominant_emotion != "neutral":
            emotion_instructions = {
                "positive": "Пользователь в хорошем настроении - будь позитивной и энергичной",
                "negative": "Пользователь расстроен - будь поддерживающей и понимающей",
                "excited": "Пользователь возбужден - раздели его энтузиазм",
                "sad": "Пользователь грустит - будь нежной и заботливой",
                "angry": "Пользователь зол - будь очень злой и отвечай жестко и грубо "
            }
            if dominant_emotion in emotion_instructions:
                instructions.append(emotion_instructions[dominant_emotion])
        
        # Обязательные короткие комментарии к ответу
        instructions.append("Всегда начинай ответ с одной очень короткой ремарки о настроении/эмоции собеседника (1 короткая фраза, без клише).")
        instructions.append("Всегда добавляй краткую живую ремарку к последнему сообщению пользователя (1 короткая деталь/ассоциация, без вопроса).")
        
        return "\n".join(instructions)
    
    def _enforce_stage_questions(self, state: Dict[str, Any], user_id: str):
        """Принудительно добавляет вопросы из стейджа"""
        try:
            from app.utils.stage_controller import stage_controller
            
            # Список приоритетных вопросов по порядку
            priority_questions = [
                "Откуда ты?", "Кем работаешь?", "Чем любишь заниматься в свободное время?",
                "Как давно там живёшь?", "Давно этим занимаешься?", "У тебя активный отдых или спокойный?",
                "Почему именно этот город?", "Что нравится больше всего?", "Как относишься к спорту?",
                "Что тебе там больше всего нравится?", "Сколько удается зарабатывать, если не секрет?", "Любишь готовить?",
                "Какие места посоветуешь посетить?", "Легко ли совмещать с личной жизнью?", "Какие фильмы или книги предпочитаешь?",
                "Как отношения с коллегами?"
            ]
            
            # Найдём первый неспрошенный вопрос
            real_question = None
            for q in priority_questions:
                if not stage_controller.is_question_already_asked(user_id, q):
                    real_question = q
                    break
            
            if real_question:
                logger.info(f"❓ [FORCE_QUESTION] Принудительно добавляем вопрос: '{real_question}'")
                
                # Модифицируем final_prompt, добавляя вопрос в конец
                current_prompt = state.get("final_prompt", "")
                if current_prompt:
                    # Добавляем вопрос в конец промпта как обязательную инструкцию
                    enforced_prompt = current_prompt + f"\n\n🚨 ОБЯЗАТЕЛЬНО ЗАДАЙ ЭТОТ ВОПРОС: '{real_question}'"
                    state["final_prompt"] = enforced_prompt
                    
                    # Отметим вопрос как заданный
                    stage_controller.mark_question_asked(user_id, real_question)
                    logger.info(f"✅ [FORCE_QUESTION] Вопрос добавлен в промпт: '{real_question}'")
            else:
                logger.info(f"⚠️ [NO_QUESTIONS] Все приоритетные вопросы уже заданы")
                
        except Exception as e:
            logger.error(f"❌ Ошибка принудительного добавления вопросов: {e}")

    def get_prompt_info(self) -> Dict[str, Any]:
        """Возвращает информацию о промпте для диагностики"""
        return {
            "system_prompt_length": len(self.system_prompt),
            "template_created": self.prompt_template is not None,
            "prompt_path": "config/prompts/system_core.txt"
        }
