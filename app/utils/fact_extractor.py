"""
Интеллектуальный экстрактор фактов из сообщений пользователя
Использует семантический анализ вместо хардкода ключевых слов
"""

import logging
import re
from typing import Dict, List, Optional, Any
from openai import OpenAI
from ..config.settings import settings

logger = logging.getLogger(__name__)

class FactExtractor:
    """
    Интеллектуальный экстрактор фактов из сообщений
    Определяет важность сообщений без хардкода ключевых слов
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.fact_types = [
            "personal_info",  # имя, возраст, семья
            "professional",   # работа, профессия, проекты
            "location",       # город, страна, адрес
            "interests",      # хобби, увлечения, предпочтения
            "relationships",  # отношения, друзья
            "goals",          # планы, мечты, цели
            "experiences"     # опыт, события, воспоминания
        ]
    
    def extract_facts(self, message: str, role: str = "user") -> Dict[str, Any]:
        """
        Извлекает факты из сообщения используя LLM
        
        Args:
            message: текст сообщения
            role: роль отправителя (user/assistant)
            
        Returns:
            Словарь с извлеченными фактами и метаданными
        """
        if role != "user" or len(message.strip()) < 10:
            return {"has_facts": False, "importance": 0.0, "facts": [], "categories": []}
        
        try:
            # Всегда используем LLM для анализа - никакого хардкода!
            return self._llm_extract_facts(message)
                
        except Exception as e:
            logger.error(f"Ошибка извлечения фактов: {e}")
            # Fallback на простую эвристику
            return self._simple_extract_facts(message)
    
# Функция _is_likely_factual удалена - используем только LLM для принятия решений
    
    def _llm_extract_facts(self, message: str) -> Dict[str, Any]:
        """
        Использует LLM для извлечения фактов из сообщения
        """
        prompt = f"""Проанализируй сообщение пользователя и извлеки из него факты о пользователе.

Сообщение: "{message}"

Определи:
1. Содержит ли сообщение важные факты о пользователе? (да/нет)
2. Важность сообщения (0.0-1.0, где 1.0 - очень важные личные данные)
3. Список фактов (если есть)
4. Категории фактов: personal_info, professional, location, interests, relationships, goals, experiences

Ответь в JSON формате:
{{
    "has_facts": true/false,
    "importance": 0.0-1.0,
    "facts": ["факт1", "факт2"],
    "categories": ["category1", "category2"]
}}

Примеры:
- "Привет, как дела?" → {{"has_facts": false, "importance": 0.0}}
- "Меня зовут Глеб, я программист" → {{"has_facts": true, "importance": 0.9, "facts": ["Имя: Глеб", "Профессия: программист"], "categories": ["personal_info", "professional"]}}
- "Я из Киева" → {{"has_facts": true, "importance": 0.7, "facts": ["Город: Киев"], "categories": ["location"]}}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Парсим JSON ответ
            import json
            result = json.loads(result_text)
            
            logger.info(f"LLM извлек факты: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка LLM извлечения фактов: {e}")
            return self._simple_extract_facts(message)
    
    def _simple_extract_facts(self, message: str) -> Dict[str, Any]:
        """
        Простая эвристическая система извлечения фактов (fallback)
        """
        message_lower = message.lower()
        facts = []
        categories = []
        importance = 0.0
        
        # Поиск имени
        name_match = re.search(r'меня зовут\s+(\w+)', message_lower)
        if name_match:
            facts.append(f"Имя: {name_match.group(1).capitalize()}")
            categories.append("personal_info")
            importance = max(importance, 0.9)
        
        # Поиск профессии
        if any(word in message_lower for word in ['программист', 'разработчик', 'работаю']):
            if 'программист' in message_lower:
                facts.append("Профессия: программист")
            categories.append("professional")
            importance = max(importance, 0.8)
        
        # Поиск города
        cities = ['киев', 'москва', 'варшава', 'спб', 'петербург']
        for city in cities:
            if city in message_lower:
                facts.append(f"Город: {city.capitalize()}")
                categories.append("location")
                importance = max(importance, 0.7)
                break
        
        has_facts = len(facts) > 0
        
        return {
            "has_facts": has_facts,
            "importance": importance,
            "facts": facts,
            "categories": list(set(categories))
        }
    
    def should_store_in_long_term(self, message: str, role: str = "user") -> bool:
        """
        Определяет, нужно ли сохранять сообщение в долгосрочную память
        """
        if role != "user":
            return False
            
        fact_data = self.extract_facts(message, role)
        return fact_data.get("has_facts", False) and fact_data.get("importance", 0) > 0.5
    
    def get_message_importance(self, message: str, role: str = "user") -> float:
        """
        Возвращает важность сообщения (0.0-1.0)
        """
        fact_data = self.extract_facts(message, role)
        return fact_data.get("importance", 0.0)

# Глобальный экземпляр
fact_extractor = FactExtractor()
