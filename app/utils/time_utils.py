from datetime import datetime, timedelta
from typing import Dict, Any

class TimeUtils:
    """Utilities for time-aware context generation"""
    
    @staticmethod
    def get_time_context(current_time: datetime) -> str:
        """Generate time-aware context string"""
        hour = current_time.hour
        
        # Determine time of day
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
            f"Сейчас {time_of_day}, {time_str}, {date_str}",
            f"Подходящее приветствие: {greeting}"
        ]
        
        # Add contextual notes
        if hour < 6 or hour > 23:
            context_parts.append("Очень поздно или очень рано - пользователь может быть усталым")
        elif 12 <= hour <= 14:
            context_parts.append("Обеденное время")
        elif 18 <= hour <= 20:
            context_parts.append("Время после работы/учебы")
        
        return "\n".join(context_parts)
    
    @staticmethod
    def get_absence_reaction(last_activity: datetime, current_time: datetime) -> str:
        """Generate reaction based on time since last activity"""
        time_diff = current_time - last_activity
        hours = time_diff.total_seconds() / 3600
        days = time_diff.days
        
        def days_phrase(n: int) -> str:
            if n % 10 == 1 and n % 100 != 11:
                return f"{n} день"
            if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
                return f"{n} дня"
            return f"{n} дней"

        if time_diff < timedelta(hours=1):
            return ""  # No special reaction
        elif time_diff < timedelta(hours=6):
            return ""  # Still recent, no reaction needed
        elif time_diff < timedelta(days=1):
            if hours > 12:
                return "Здорово, что написал! Как дела?"
            else:
                return "Привет! Как дела?"
        elif days == 1:
            return "Ты не писал 1 день! Где пропадал?"
        elif days == 2:
            return "Ты не писал 2 дня! Что случилось?"
        elif days <= 14:
            # Унифицированная строгая формулировка с правильным склонением
            return f"Ты не писал {days_phrase(days)}! Где пропадал?"
        else:
            return f"Ты не писал {days_phrase(days)}! Давай наверстаем, как ты?"
    
    @staticmethod
    def calculate_day_number(first_interaction: datetime, current_time: datetime) -> int:
        """Calculate which day of relationship this is"""
        days_diff = (current_time.date() - first_interaction.date()).days
        return max(1, days_diff + 1)
    
    @staticmethod
    def get_weekly_context(current_time: datetime) -> str:
        """Get context based on day of week"""
        weekday = current_time.weekday()  # 0 = Monday, 6 = Sunday
        
        weekday_names = {
            0: "понедельник",
            1: "вторник", 
            2: "среда",
            3: "четверг",
            4: "пятница",
            5: "суббота",
            6: "воскресенье"
        }
        
        weekday_contexts = {
            0: "Начало рабочей недели",
            1: "Вторник - день набирает обороты",
            2: "Середина недели",
            3: "Четверг - почти выходные",
            4: "Пятница - конец рабочей недели!",
            5: "Выходные! Суббота",
            6: "Воскресенье - последний день выходных"
        }
        
        day_name = weekday_names.get(weekday, "")
        context = weekday_contexts.get(weekday, "")
        
        return f"Сегодня {day_name}. {context}" 