"""
OpenAI Text Analyzer - анализ текста с помощью OpenAI API
"""
import openai
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class OpenAITextAnalyzer:
    """Анализатор текста с использованием OpenAI API"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo"
    
    def analyze_message_type(self, text: str) -> Dict[str, Any]:
        """
        Анализирует тип сообщения и его характеристики
        
        Returns:
            Dict с анализом сообщения
        """
        try:
            prompt = f"""
Проанализируй это сообщение и определи его характеристики:

Сообщение: "{text}"

Верни JSON с полями:
{{
    "message_type": "greeting|question|emotion|short_response|statement|other",
    "sentiment": "positive|neutral|negative",
    "emotion": "happy|sad|excited|calm|surprised|thinking|other",
    "intent": "ask_question|share_info|express_feeling|greet|respond|other",
    "urgency": "low|medium|high",
    "formality": "casual|neutral|formal",
    "needs_response": true/false,
    "suggested_connector": "А|Кстати|и|Кроме того|Но|Однако",
    "is_short": true/false,
    "confidence": 0.0-1.0
}}

Анализируй как живой человек, учитывай контекст и эмоции.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты эксперт по анализу человеческого общения. Анализируй сообщения как живой человек."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"🔍 [OPENAI] Проанализировано сообщение: '{text[:50]}...'")
            logger.info(f"   📊 Тип: {result['message_type']}")
            logger.info(f"   😊 Эмоция: {result['emotion']}")
            logger.info(f"   💭 Намерение: {result['intent']}")
            logger.info(f"   🔗 Связка: {result['suggested_connector']}")
            logger.info(f"   📏 Короткое: {result['is_short']}")
            logger.info(f"   🎯 Уверенность: {result['confidence']}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа сообщения: {e}")
            return self._get_fallback_analysis(text)
    
    def analyze_conversation_context(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Анализирует контекст всей беседы
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}]
            
        Returns:
            Dict с анализом контекста
        """
        try:
            # Формируем контекст беседы
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in messages[-10:]  # Последние 10 сообщений
            ])
            
            prompt = f"""
Проанализируй контекст этой беседы:

{conversation_text}

Верни JSON с полями:
{{
    "conversation_tone": "friendly|formal|casual|intimate|business|other",
    "user_mood": "happy|neutral|sad|excited|tired|focused|other",
    "conversation_stage": "greeting|getting_to_know|deep_conversation|closing|other",
    "user_engagement": "low|medium|high",
    "suggested_response_style": "empathetic|professional|casual|playful|supportive",
    "should_ask_question": true/false,
    "suggested_question": "вопрос для продолжения беседы или null",
    "emotional_support_needed": true/false,
    "conversation_energy": "low|medium|high",
    "confidence": 0.0-1.0
}}

Учитывай эмоциональный контекст и динамику беседы.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты эксперт по анализу человеческого общения и психологии. Анализируй беседы как опытный психолог."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"🔍 [OPENAI] Проанализирован контекст беседы:")
            logger.info(f"   🎭 Тон: {result['conversation_tone']}")
            logger.info(f"   😊 Настроение: {result['user_mood']}")
            logger.info(f"   📈 Этап: {result['conversation_stage']}")
            logger.info(f"   💪 Энергия: {result['conversation_energy']}")
            logger.info(f"   🎯 Стиль ответа: {result['suggested_response_style']}")
            logger.info(f"   ❓ Нужен вопрос: {result['should_ask_question']}")
            if result.get('suggested_question'):
                logger.info(f"   💡 Предложенный вопрос: {result['suggested_question']}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа контекста: {e}")
            return self._get_fallback_context()
    
    def generate_connector(self, previous_message: str, current_message: str) -> str:
        """
        Генерирует подходящую связку между сообщениями
        
        Args:
            previous_message: Предыдущее сообщение
            current_message: Текущее сообщение
            
        Returns:
            Подходящая связка
        """
        try:
            prompt = f"""
Определи подходящую связку между этими сообщениями:

Предыдущее: "{previous_message}"
Текущее: "{current_message}"

Выбери ОДНО слово из списка:
- "А" (для вопросов)
- "Кстати" (для смены темы)
- "и" (для продолжения)
- "Кроме того" (для дополнения)
- "Но" (для противопоставления)
- "Однако" (для мягкого противопоставления)
- "Тем временем" (для параллельных действий)
- "Короче" (для резюмирования)
- "В общем" (для обобщения)
- "Кстати" (для отступления)

Верни только одно слово, без кавычек и дополнительного текста.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты эксперт по русскому языку и стилистике. Выбирай связки как носитель языка."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            connector = response.choices[0].message.content.strip()
            logger.info(f"Сгенерирована связка: {connector}")
            return connector
            
        except Exception as e:
            logger.error(f"Ошибка генерации связки: {e}")
            return "А"
    
    def suggest_question(self, context: Dict[str, Any], stage: int) -> str:
        """
        Предлагает подходящий вопрос на основе контекста
        
        Args:
            context: Контекст беседы
            stage: Этап общения (1, 2, 3)
            
        Returns:
            Подходящий вопрос
        """
        try:
            prompt = f"""
На основе контекста беседы предложи подходящий вопрос:

Контекст:
- Тон беседы: {context.get('conversation_tone', 'neutral')}
- Настроение пользователя: {context.get('user_mood', 'neutral')}
- Этап общения: {stage}
- Энергия беседы: {context.get('conversation_energy', 'medium')}

Этапы:
- Этап 1: Знакомство (первые 3-5 сообщений)
- Этап 2: Развитие знакомства (5-15 сообщений)  
- Этап 3: Углубление отношений (15+ сообщений)

Предложи ОДИН естественный вопрос, который:
1. Подходит к этапу общения
2. Учитывает настроение пользователя
3. Поддерживает энергию беседы
4. Звучит как живой человек

Верни только вопрос, без кавычек и дополнительного текста.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты эксперт по человеческому общению. Задавай вопросы как живой, эмпатичный человек."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            question = response.choices[0].message.content.strip()
            logger.info(f"Предложен вопрос: {question}")
            return question
            
        except Exception as e:
            logger.error(f"Ошибка генерации вопроса: {e}")
            return "как дела?"
    
    def _get_fallback_analysis(self, text: str) -> Dict[str, Any]:
        """Fallback анализ если OpenAI недоступен"""
        return {
            "message_type": "statement",
            "sentiment": "neutral",
            "emotion": "calm",
            "intent": "share_info",
            "urgency": "low",
            "formality": "casual",
            "needs_response": True,
            "suggested_connector": "А",
            "is_short": len(text) < 50,
            "confidence": 0.5
        }
    
    def _get_fallback_context(self) -> Dict[str, Any]:
        """Fallback контекст если OpenAI недоступен"""
        return {
            "conversation_tone": "friendly",
            "user_mood": "neutral",
            "conversation_stage": "greeting",
            "user_engagement": "medium",
            "suggested_response_style": "casual",
            "should_ask_question": True,
            "suggested_question": "как дела?",
            "emotional_support_needed": False,
            "conversation_energy": "medium",
            "confidence": 0.5
        }
