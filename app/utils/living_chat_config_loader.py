"""
Living Chat Config Loader - загрузчик конфигурации живого общения
"""
import yaml
import os
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class LivingChatConfigLoader:
    """Загрузчик конфигурации для живого общения"""
    
    def __init__(self, config_path: str = "app/config/living_chat_config.yml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из YAML файла"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Загружена конфигурация живого общения из {self.config_path}")
                    return config
            else:
                logger.warning(f"Файл конфигурации не найден: {self.config_path}")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию"""
        return {
            "living_chat": {
                "message_splitting": {
                    "max_length": 150,
                    "force_split_threshold": 100,
                    "min_delay_ms": 500,
                    "max_delay_ms": 2000,
                    "max_parts": 3
                },
                "short_messages": {
                    "max_wait_seconds": 30,
                    "short_message_threshold": 50,
                    "quick_sequence_threshold": 5
                },
                "combination_patterns": [],
                "connectors": {
                    "question_start": "А",
                    "emotion_start": "Кстати",
                    "short_message": "и",
                    "last_message": "Кроме того",
                    "default": "А"
                },
                "daily_questions": {
                    "stage_1": ["как дела?", "что делаешь?"],
                    "stage_2": ["как прошел день?", "что интересного?"],
                    "stage_3": ["как дела?", "что планируешь?"]
                },
                "time_greetings": {
                    "morning": "доброе утро",
                    "day": "добрый день",
                    "evening": "добрый вечер",
                    "night": "доброй ночи"
                },
                "emotions": {
                    "positive": ["круто!", "вау!", "ого!"],
                    "neutral": ["понятно", "ок"],
                    "surprise": ["ого!", "вау!"],
                    "thinking": ["хм", "думаю"]
                },
                "communication_style": {
                    "use_emojis": True,
                    "use_parentheses": True,
                    "use_contractions": True,
                    "max_emoji_per_message": 2,
                    "casual_expressions": True
                }
            }
        }
    
    def get_message_splitting_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию разбиения сообщений"""
        return self.config.get("living_chat", {}).get("message_splitting", {})
    
    def get_short_messages_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию коротких сообщений"""
        return self.config.get("living_chat", {}).get("short_messages", {})
    
    def get_combination_patterns(self) -> List[Dict[str, str]]:
        """Возвращает паттерны объединения сообщений"""
        return self.config.get("living_chat", {}).get("combination_patterns", [])
    
    def get_connectors(self) -> Dict[str, str]:
        """Возвращает слова-связки"""
        return self.config.get("living_chat", {}).get("connectors", {})
    
    def get_daily_questions(self, stage: int) -> List[str]:
        """Возвращает повседневные вопросы для этапа"""
        stage_key = f"stage_{stage}"
        return self.config.get("living_chat", {}).get("daily_questions", {}).get(stage_key, [])
    
    def get_time_greetings(self) -> Dict[str, str]:
        """Возвращает приветствия по времени"""
        return self.config.get("living_chat", {}).get("time_greetings", {})
    
    def get_emotions(self, emotion_type: str) -> List[str]:
        """Возвращает эмоциональные выражения"""
        return self.config.get("living_chat", {}).get("emotions", {}).get(emotion_type, [])
    
    def get_communication_style(self) -> Dict[str, Any]:
        """Возвращает стиль общения"""
        return self.config.get("living_chat", {}).get("communication_style", {})
    
    def get_time_ranges(self) -> Dict[str, List[int]]:
        """Возвращает временные диапазоны"""
        return self.config.get("living_chat", {}).get("time_ranges", {})
    
    def reload_config(self):
        """Перезагружает конфигурацию"""
        self.config = self._load_config()
        logger.info("Конфигурация живого общения перезагружена")

# Глобальный экземпляр загрузчика
living_chat_config = LivingChatConfigLoader()
