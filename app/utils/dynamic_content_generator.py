"""
Динамічний генератор контенту замість хардкоду
"""
import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
import openai
import os

logger = logging.getLogger(__name__)

class DynamicContentGenerator:
    """Генерує контент динамічно через OpenAI замість хардкоду"""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
    def generate_questions_for_time(self, time_of_day: str, context: Dict[str, Any]) -> List[str]:
        """Генерує питання залежно від часу дня та контексту"""
        try:
            prompt = f"""
            Згенеруй 3-5 коротких питань для {time_of_day} часу дня.
            
            Контекст розмови:
            - День тижня: {context.get('day_of_week', 'не відомо')}
            - Стейдж спілкування: {context.get('stage', 'знайомство')}
            - Попередні теми: {context.get('previous_topics', [])}
            
            Питання повинні бути:
            - Природними для даного часу
            - Відповідати стейджу спілкування
            - Короткими (до 50 символів)
            - Різноманітними
            
            Поверни список питань у форматі JSON: ["питання1", "питання2", ...]
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=200
            )
            
            import json
            questions = json.loads(response.choices[0].message.content)
            logger.info(f"Згенеровано {len(questions)} питань для {time_of_day}")
            return questions
            
        except Exception as e:
            logger.error(f"Помилка генерації питань: {e}")
            # Fallback до простих питань
            fallback = {
                "morning": ["як спав?", "як планів на день?", "що робитимеш?"],
                "day": ["як справи?", "що робиш?", "як настрій?"],
                "evening": ["як пройшов день?", "що цікавого?", "як настрій?"],
                "night": ["як справи?", "що робиш так пізно?", "як день?"]
            }
            return fallback.get(time_of_day, ["як справи?"])
    
    def generate_emotional_response(self, user_message: str, emotion_context: Dict[str, Any]) -> str:
        """Генерує емоційну реакцію на основі повідомлення користувача"""
        try:
            prompt = f"""
            Згенеруй коротку емоційну реакцію на повідомлення користувача: "{user_message}"
            
            Контекст:
            - Поточна емоція Агати: {emotion_context.get('current_emotion', 'нейтральна')}
            - Стиль спілкування: {emotion_context.get('communication_style', 'дружелюбний')}
            - Рівень близькості: {emotion_context.get('intimacy_level', 'початковий')}
            
            Реакція повинна:
            - Бути короткою (до 30 символів)
            - Відображати емоцію
            - Бути природною
            - Містити максимум 1 емодзі
            
            Поверни тільки текст реакції.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=50
            )
            
            reaction = response.choices[0].message.content.strip()
            logger.info(f"Згенерована реакція: {reaction}")
            return reaction
            
        except Exception as e:
            logger.error(f"Помилка генерації емоційної реакції: {e}")
            # Fallback реакції
            fallbacks = ["цікаво!", "розумію", "ого!", "класно", "зрозуміло"]
            return random.choice(fallbacks)
    
    def generate_conversation_connectors(self, message1: str, message2: str) -> str:
        """Генерує з'єднувач для об'єднання двох повідомлень"""
        try:
            prompt = f"""
            Як природно об'єднати ці повідомлення користувача:
            1. "{message1}"
            2. "{message2}"
            
            Дай ОДИН короткий з'єднувач (1-2 слова) який звучить природно в розмові:
            - "а також"
            - "і ще"
            - "кстаті"
            - "та"
            - "і"
            - "плюс"
            
            Поверни ТІЛЬКИ з'єднувач без коми.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=10
            )
            
            connector = response.choices[0].message.content.strip().replace(",", "").replace(".", "")
            logger.info(f"Згенерований з'єднувач: {connector}")
            return connector
            
        except Exception as e:
            logger.error(f"Помилка генерації з'єднувача: {e}")
            return "і"  # Fallback
    
    def analyze_message_emotions(self, messages: List[str]) -> Dict[str, Any]:
        """Покращений аналіз емоцій з урахуванням характеру Агати"""
        try:
            messages_text = " ".join(messages)
            

            prompt = f"""
            Проаналізуй емоційний тон та характер цих повідомлень: "{messages_text}"
            
            Визначи ДЕТАЛЬНО:
            1. Основну емоцію: positive/negative/neutral/excited/sad/angry/frustrated/anxious/playful/intellectual/rude
            2. Інтенсивність емоції (0.0-1.0): 0.1-0.3=слабо, 0.4-0.6=помірно, 0.7-0.9=сильно, 1.0=дуже сильно
            3. Тип повідомлення: question/statement/greeting/story/complaint/joke/flirt/insult
            4. Стиль спілкування: friendly/formal/casual/aggressive/analytical/emotional/playful/rude
            5. Потребу у відповіді: support/information/entertainment/argument/flirt/casual_chat
            6. Рівень поваги: respectful/neutral/disrespectful/rude
            
            ОСОБЛИВА УВАГА до:
            - Грубості, образ, нецензурної лексики
            - Агресивності та негативу  
            - Інтелектуального рівня спілкування
            - Емоційного стану користувача
            
            Поверни у форматі JSON:
            {{
                "emotion": "конкретна_емоція",
                "intensity": число_від_0_до_1,
                "message_type": "тип_повідомлення", 
                "communication_style": "стиль_спілкування",
                "response_need": "потреба_у_відповіді",
                "respect_level": "рівень_поваги",
                "requires_boundaries": true/false,
                "can_be_playful": true/false
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Менша температура для більш стабільного аналізу
                max_tokens=150
            )
            
            import json
            import re
            
            content = response.choices[0].message.content.strip()
            logger.info(f"🔍 [EMOTION_ANALYSIS] Сырой ответ OpenAI: '{content}'")
            
            # Убираем markdown блоки и извлекаем JSON
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*$', '', content)
            
            # Попробуем извлечь JSON из ответа
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group()
            
            analysis = json.loads(content)
            
            # Додаткова обробка для кращого логування
            logger.info(f"🔍 [EMOTION_ANALYSIS] Повідомлення: '{messages_text[:50]}...'")
            logger.info(f"🔍 [EMOTION_ANALYSIS] Емоція: {analysis.get('emotion')} (інтенсивність: {analysis.get('intensity')})")
            logger.info(f"🔍 [EMOTION_ANALYSIS] Стиль: {analysis.get('communication_style')}, Повага: {analysis.get('respect_level')}")
            logger.info(f"🔍 [EMOTION_ANALYSIS] Потребує границь: {analysis.get('requires_boundaries')}, Можна грати: {analysis.get('can_be_playful')}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ [EMOTION_ANALYSIS] Помилка аналізу емоцій: {e}")
            return {
                "emotion": "neutral",
                "intensity": 0.5,
                "message_type": "statement",
                "communication_style": "casual",
                "response_need": "casual_chat",
                "respect_level": "neutral",
                "requires_boundaries": False,
                "can_be_playful": True
            }
    
    def generate_stage_appropriate_questions(self, stage: str, covered_topics: List[str], user_context: Dict[str, Any]) -> List[str]:
        """Генерує питання відповідно до поточного стейджу"""
        try:
            prompt = f"""
            Згенеруй 3-5 питань для стейджу "{stage}" спілкування з користувачем.
            
            Вже обговорені теми: {covered_topics}
            Контекст користувача: {user_context}
            
            Стейджі:
            - stage_1 (знайомство): базові питання про життя, роботу, хобі
            - stage_2 (дружба): більш особисті питання, цінності, мрії
            - stage_3 (близькість): глибокі питання про почуття, стосунки
            
            Питання повинні:
            - Відповідати рівню близькості
            - Не повторювати вже обговорені теми
            - Бути природними та цікавими
            - Бути короткими (до 60 символів)
            
            Поверни JSON: ["питання1", "питання2", ...]
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=300
            )
            
            import json
            questions = json.loads(response.choices[0].message.content)
            logger.info(f"Згенеровано {len(questions)} питань для стейджу {stage}")
            return questions
            
        except Exception as e:
            logger.error(f"Помилка генерації питань для стейджу: {e}")
            # Fallback питання по стейджах
            fallback = {
                "stage_1": ["звідки ти?", "ким працюєш?", "що любиш робити?"],
                "stage_2": ["що для тебе важливо?", "які у тебе мрії?", "як проводиш час?"],
                "stage_3": ["що тебе надихає?", "які у тебе цінності?", "що робить тебе щасливим?"]
            }
            return fallback.get(stage, ["як справи?"])
