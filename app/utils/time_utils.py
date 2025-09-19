from datetime import datetime, timedelta
from typing import Dict, Any, List

class TimeUtils:
    """Utilities for time-aware context generation"""
    
    @staticmethod
    def get_time_context(current_time: datetime, should_include_greeting: bool = False) -> str:
        """Generate time-aware context string"""
        hour = current_time.hour
        
        if 6 <= hour < 12:
            time_of_day = "утро"
            greeting = "Доброе утро"
        elif 12 <= hour < 18:
            time_of_day = "день"
            greeting = "Добрый день"
        elif 18 <= hour < 22:
            time_of_day = "вечер"
            greeting = "Добрый вечер"
        else:
            time_of_day = "ночь"
            greeting = "Доброй ночи" if hour >= 22 else "Ночь..."
        
        # Format current time
        time_str = current_time.strftime("%H:%M")
        date_str = current_time.strftime("%d.%m.%Y")
        
        context_parts = [
            f"Сейчас {time_of_day}, {time_str}, {date_str}"
        ]
        
        # Добавляем приветствие только если это нужно
        if should_include_greeting:
            context_parts.append(f"Подходящее приветствие: {greeting}")
        
        # Add contextual notes
        if hour < 6 or hour > 23:
            context_parts.append("Очень поздно или очень рано - пользователь может быть усталым")
        elif 12 <= hour <= 14:
            context_parts.append("Обеденное время")
        elif 18 <= hour <= 20:
            context_parts.append("Время после работы/учебы")
        
        return "\n".join(context_parts)
    
    @staticmethod
    def get_daily_questions(current_time: datetime) -> Dict[str, Any]:
        """Генерирует контекст для динамических вопросов времени дня"""
        hour = current_time.hour
        weekday = current_time.weekday()  # 0=понедельник, 6=воскресенье
        
        # Определяем период дня
        if 6 <= hour < 12:
            time_period = "утро"
            context = "Утреннее время - начало дня, планирование, завтрак, энергия"
        elif 12 <= hour < 18:
            time_period = "день"  
            context = "Дневное время - работа, обед, активность, дела"
        elif 18 <= hour < 22:
            time_period = "вечер"
            context = "Вечернее время - отдых, ужин, подведение итогов дня"
        else:
            time_period = "ночь"
            context = "Позднее время - сон, отдых, интимная атмосфера"
        
        # Определяем день недели  
        if weekday < 5:  # Будни
            week_context = "рабочий день"
        elif weekday == 5:  # Суббота
            week_context = "суббота, выходной"
        else:  # Воскресенье
            week_context = "воскресенье, последний день выходных"
        
        return {
            "time_period": time_period,
            "hour": hour,
            "context": context,
            "week_context": week_context,
            "question_themes": TimeUtils._get_question_themes(time_period, week_context),
            "should_generate_dynamic": True  # Флаг для динамической генерации
        }
    
    @staticmethod
    def _get_question_themes(time_period: str, week_context: str) -> List[str]:
        """Возвращает темы для генерации вопросов"""
        base_themes = {
            "утро": ["настроение", "планы на день", "завтрак", "сон", "энергия"],
            "день": ["работа", "обед", "дела", "прогресс", "самочувствие"],
            "вечер": ["итоги дня", "планы на вечер", "ужин", "отдых", "настроение"],
            "ночь": ["причина бодрствования", "планы на завтра", "усталость", "сон"]
        }
        
        themes = base_themes.get(time_period, ["общие вопросы"])
        
        # Добавляем контекст дня недели
        if "выходной" in week_context:
            themes.extend(["отдых", "хобби", "развлечения"])
        elif "рабочий день" in week_context:
            themes.extend(["работа", "коллеги", "задачи"])
            
        return themes
    
    @staticmethod 
    def get_emotional_reactions(current_time: datetime, days_communicating: int) -> Dict[str, Any]:
        """Генерирует эмоциональные реакции с учетом времени и дней общения - БЕЗ хардкода"""
        hour = current_time.hour
        
        # Базовые параметры для LLM генерации
        time_context = TimeUtils._get_time_period_context(hour)
        relationship_context = TimeUtils._get_relationship_context(days_communicating)
        
        return {
            "hour": hour,
            "time_period": time_context["period"],
            "energy_suggestion": time_context["energy_level"],
            "mood_suggestion": time_context["mood_tone"],
            "days_communicating": days_communicating,
            "relationship_stage": relationship_context["stage"],
            "communication_style": relationship_context["style"],
            "should_generate_dynamic_reaction": True,  # Флаг для LLM генерации
            "context_for_llm": f"Время: {time_context['period']} ({hour}:00), День общения: {days_communicating}, Стадия отношений: {relationship_context['stage']}"
        }
    
    @staticmethod
    def _get_time_period_context(hour: int) -> Dict[str, str]:
        """Определяет базовый контекст времени без хардкода комментариев"""
        if 6 <= hour < 12:
            return {"period": "утро", "energy_level": "gentle_to_active", "mood_tone": "fresh"}
        elif 12 <= hour < 18:
            return {"period": "день", "energy_level": "stable_to_steady", "mood_tone": "focused"}
        elif 18 <= hour < 22:
            return {"period": "вечер", "energy_level": "relaxed", "mood_tone": "warm"}
        else:
            return {"period": "ночь", "energy_level": "low", "mood_tone": "intimate_or_concerned"}
    
    @staticmethod  
    def _get_relationship_context(days: int) -> Dict[str, str]:
        """Определяет стадию отношений без хардкода"""
        if days == 1:
            return {"stage": "first_contact", "style": "curious"}
        elif days <= 7:
            return {"stage": "getting_acquainted", "style": "interested"}
        elif days <= 30:
            return {"stage": "comfortable", "style": "familiar"}
        else:
            return {"stage": "established", "style": "close"}
    
    @staticmethod
    def get_absence_reaction(last_activity: datetime, current_time: datetime) -> Dict[str, Any]:
        """Генерирует контекст для реакции на отсутствие - БЕЗ хардкода текста"""
        time_diff = current_time - last_activity
        hours = time_diff.total_seconds() / 3600
        days = time_diff.days
        
        # Возвращаем только данные для LLM генерации
        if time_diff < timedelta(hours=1):
            return {"should_react": False, "reason": "too_recent"}
        elif time_diff < timedelta(hours=6):
            return {"should_react": False, "reason": "still_recent"}
        elif time_diff < timedelta(days=1):
            return {
                "should_react": True,
                "absence_type": "hours",
                "absence_duration": f"{int(hours)} часов",
                "intensity": "mild" if hours < 12 else "moderate",
                "context_for_llm": f"Пользователь не писал {int(hours)} часов"
            }
        elif days <= 14:
            return {
                "should_react": True,
                "absence_type": "days",
                "absence_duration": f"{days} дней",
                "intensity": "high" if days > 7 else "moderate",
                "context_for_llm": f"Пользователь не писал {days} дней"
            }
        else:
            return {
                "should_react": True,
                "absence_type": "long_term",
                "absence_duration": f"{days} дней",
                "intensity": "very_high",
                "context_for_llm": f"Пользователь не писал очень долго - {days} дней"
            }
    
    @staticmethod
    def calculate_day_number(first_interaction: datetime, current_time: datetime) -> int:
        """Calculate which day of relationship this is"""
        days_diff = (current_time.date() - first_interaction.date()).days
        return max(1, days_diff + 1)
    
    @staticmethod
    def get_weekly_context(current_time: datetime) -> Dict[str, Any]:
        weekday = current_time.weekday()  # 0 = Monday, 6 = Sunday
        
        weekday_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
        day_name = weekday_names[weekday]
        
        # Определяем тип дня
        if weekday < 5:
            day_type = "workday"
            week_phase = "weekdays"
        elif weekday == 5:
            day_type = "saturday"
            week_phase = "weekend_start"
        else:
            day_type = "sunday"  
            week_phase = "weekend_end"
        
        return {
            "day_name": day_name,
            "weekday_number": weekday,
            "day_type": day_type,
            "week_phase": week_phase,
            "should_generate_dynamic_comment": True,
            "context_for_llm": f"Сегодня {day_name}, это {day_type}"
        } 