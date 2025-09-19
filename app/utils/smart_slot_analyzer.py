"""
Розумний аналізатор слотів через LLM
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class SmartSlotAnalyzer:
    """Розумний аналізатор відповідей користувача через LLM"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        
    async def analyze_user_response(self, user_message: str, available_questions: List[str]) -> Dict[str, Any]:
        if not user_message or len(user_message.strip()) < 2:
            return {"answered_questions": [], "confidence": 0.0}
            
        try:
            # Створюємо промпт для аналізу
            analysis_prompt = self._create_analysis_prompt(user_message, available_questions)
            
            # Викликаємо LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты эксперт по анализу диалогов. Определяешь, на какие вопросы был дан ответ."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            # Парсимо відповідь
            result = self._parse_llm_response(response.choices[0].message.content)
            
            logger.info(f"🧠 [SMART_ANALYSIS] Аналіз: '{user_message[:50]}...' → {len(result.get('answered_questions', []))} питань")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [SMART_ANALYSIS] Помилка аналізу: {e}")
            return {"answered_questions": [], "confidence": 0.0, "error": str(e)}
    
    def _create_analysis_prompt(self, user_message: str, available_questions: List[str]) -> str:
        """Створює промпт для аналізу відповіді користувача"""
        
        questions_text = "\n".join([f"- {q}" for q in available_questions])
        
        prompt = f"""
Проанализируй ответ пользователя и определи, на какие из доступных вопросов был дан ответ.

ОТВЕТ ПОЛЬЗОВАТЕЛЯ: "{user_message}"

ДОСТУПНЫЕ ВОПРОСЫ:
{questions_text}

ИНСТРУКЦИИ:
1. Определи, на какие вопросы пользователь дал конкретный ответ
2. Учитывай не только прямые ответы, но и косвенные упоминания
3. Если пользователь упомянул имя - это ответ на "Как тебя зовут?"
4. Если упомянул город - это ответ на "Откуда ты?"
5. Если упомянул работу - это ответ на "Кем работаешь?"
6. Если упомянул машину - это ответ на "У тебя есть машина?"
7. И так далее для всех вопросов

ФОРМАТ ОТВЕТА (строго JSON):
{{
    "answered_questions": [
        "Как тебя зовут?",
        "Откуда ты?"
    ],
    "confidence": 0.85,
    "reasoning": "Пользователь назвал имя 'Максим' и упомянул город 'Киев'"
}}

Верни ТОЛЬКО JSON, без дополнительного текста.
"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Парсить відповідь LLM"""
        try:
            # Очищуємо відповідь від зайвих символів
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # Парсимо JSON
            result = json.loads(response)
            
            # Валідуємо структуру
            if "answered_questions" not in result:
                result["answered_questions"] = []
            if "confidence" not in result:
                result["confidence"] = 0.0
            if "reasoning" not in result:
                result["reasoning"] = "Аналіз виконано"
                
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ [SMART_ANALYSIS] Помилка парсингу JSON: {e}")
            logger.error(f"❌ [SMART_ANALYSIS] Відповідь LLM: {response}")
            return {"answered_questions": [], "confidence": 0.0, "error": "JSON parse error"}
        except Exception as e:
            logger.error(f"❌ [SMART_ANALYSIS] Загальна помилка парсингу: {e}")
            return {"answered_questions": [], "confidence": 0.0, "error": str(e)}
    
    async def analyze_with_fallback(self, user_message: str, available_questions: List[str]) -> Dict[str, Any]:
        """
        Аналізує з fallback на простий аналіз ключових слів
        """
        try:
            # Спочатку пробуємо розумний аналіз
            smart_result = await self.analyze_user_response(user_message, available_questions)
            
            if smart_result.get("confidence", 0) > 0.5:
                return smart_result
            else:
                # Fallback на простий аналіз
                logger.info(f"🔄 [SMART_ANALYSIS] Fallback на простий аналіз для: '{user_message[:30]}...'")
                return self._simple_keyword_analysis(user_message, available_questions)
                
        except Exception as e:
            logger.error(f"❌ [SMART_ANALYSIS] Помилка розумного аналізу: {e}")
            return self._simple_keyword_analysis(user_message, available_questions)
    
    def _simple_keyword_analysis(self, user_message: str, available_questions: List[str]) -> Dict[str, Any]:
        """Простий аналіз ключових слів як fallback"""
        user_message_lower = user_message.lower()
        answered_questions = []
        
        # Базові ключові слова
        keyword_map = {
            "Как тебя зовут?": ["зовут", "имя", "меня", "зову"],
            "Откуда ты?": ["откуда", "из", "живу", "город", "родом"],
            "Кем работаешь?": ["работаю", "работа", "программист", "дизайнер"],
            "У тебя есть машина?": ["машина", "авто", "bmw", "мерседес", "есть", "нет"],
            "Сколько тебе лет?": ["лет", "возраст", "года", "мне"],
            "У тебя активный отдых или спокойный?": ["активный", "спокойный", "спорт", "отдых"],
        }
        
        for question in available_questions:
            if question in keyword_map:
                keywords = keyword_map[question]
                if any(keyword in user_message_lower for keyword in keywords):
                    answered_questions.append(question)
        
        return {
            "answered_questions": answered_questions,
            "confidence": 0.3,  # Низька впевненість для fallback
            "reasoning": "Простий аналіз ключових слів",
            "method": "fallback"
        }

# Глобальний екземпляр
smart_analyzer = SmartSlotAnalyzer()
