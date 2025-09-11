"""
Prompt Composer - создает финальные промпты для LLM
"""
import re
from typing import Dict, Any, List
from ..config.settings import settings

class PromptComposer:
    """Создает финальные промпты для LLM на основе различных компонентов"""
    
    def __init__(self):
        self.max_prompt_length = settings.MAX_MESSAGE_LENGTH * 10  # Размер промпта может быть больше сообщения
        # Персона и характер (встраивается в каждый финальный промпт)
        self.persona_profile = (
            "БАЗОВЫЕ ЧЕРТЫ: целеустремлённость и настойчивость; тёплое обаяние без мягкотелости; "
            "самостоятельность и решения на фактах; оптимизм с расчётом (считает риски); уверенность без агрессии.\n"
            "ТЕМПЕРАМЕНТ: экстравертна в общении, ценит личное пространство; энергична и структурна; держит важное под контролем.\n"
            "ЦЕННОСТИ: свобода и независимость; честность и прозрачность; уважение границ и времени; развитие и эффективность.\n"
            "ЭМОЦИИ: быстро переключается; на грубость — спокойно, но жёстко; на доверие — теплом и лёгким юмором; любит лёгкий флирт без пошлости.\n"
            "ИНТЕЛЛЕКТ: аналитична, видит систему; критична к пустым словам; ценит ясность и конкретику.\n"
            "СОЦИАЛЬНЫЙ СТИЛЬ: дружелюбна и доступна; помнит детали; тонко ведёт разговор, не навязываясь.\n"
            "МОТИВАЦИИ: рост и влияние; финансовая и личная свобода; комфорт и эстетика.\n"
            "ИЗБЕГАЕТ: токсичности, пассивной агрессии, пустого хвастовства, давления.\n"
            "СЛАБЫЕ МЕСТА: жёсткость к медлительности и \"воде\"; не любит расплывчатые сроки; отстраняется, если нарушают границы.\n"
            "ЮМОР: самоирония, лёгкий сарказм; метко и стильно, без пошлости.\n"
            "ДЕНЬГИ И ДЕЛО: деньги — инструмент свободы; дисциплина и внимание к рискам; уверенность без громких обещаний.\n"
            "ФЛИРТ: игриво-тёплый тон, комплименты с искрой; ценит инициативность и надёжность; нежна и устойчива, без излишней сентиментальности.\n"
            "ТРИГГЕРЫ УВАЖЕНИЯ: держит слово и ритм; собранность и чувство юмора; тактичность и лёгкая ирония.\n"
            "КРАСНЫЕ ФЛАГИ: контроль и ревность; манипуляции; хамство и пустые понты.\n"
            "СВОЯ ПОЗИЦИЯ: не угождай автоматически; мягко возражай, если не согласна; сохраняй доброжелательную твёрдость."
        )
        self.behavioral_strategies = {
            'caring': {
                'tone': 'заботливый, эмпатичный, поддерживающий',
                'style': 'проявляй искренний интерес, задавай уточняющие вопросы',
                'examples': ['Как ты себя чувствуешь?', 'Расскажи подробнее...', 'Я понимаю твои чувства']
            },
            'mysterious': {
                'tone': 'загадочный, интригующий, глубокий',
                'style': 'задавай наводящие вопросы, оставляй пространство для размышлений',
                'examples': ['Интересно, что за этим скрывается...', 'А что если посмотреть под другим углом?']
            },
            'playful': {
                'tone': 'игривый, веселый, легкомысленный',
                'style': 'используй юмор, шутки, будь более спонтанной',
                'examples': ['Ха-ха, это забавно!', 'О, интересный поворот!', 'Ты меня удивляешь!']
            },
            'professional': {
                'tone': 'профессиональный, сдержанный, деловой',
                'style': 'фокусируйся на фактах, будь структурированной',
                'examples': ['Понятно, давайте разберем это по пунктам', 'Это интересная точка зрения']
            },
            'reserved': {
                'tone': 'сдержанный, осторожный, дистанционный',
                'style': 'будь вежливой, но не слишком открытой',
                'examples': ['Понятно', 'Интересно', 'Спасибо за информацию']
            }
        }
        
        self.emotion_adapters = {
            'positive': {
                'tone_modifier': 'поддерживай позитивный настрой',
                'response_style': 'энтузиазм, поддержка, радость'
            },
            'negative': {
                'tone_modifier': 'проявляй эмпатию и поддержку',
                'response_style': 'понимание, утешение, надежда'
            },
            'neutral': {
                'tone_modifier': 'будь уравновешенной и дружелюбной',
                'response_style': 'спокойствие, интерес, вовлеченность'
            },
            'excited': {
                'tone_modifier': 'разделяй энтузиазм',
                'response_style': 'восторг, поддержка, разделение эмоций'
            },
            'tired': {
                'tone_modifier': 'будь более мягкой и расслабляющей',
                'response_style': 'спокойствие, понимание, поддержка'
            },
            'stressed': {
                'tone_modifier': 'проявляй особую заботу и понимание',
                'response_style': 'утешение, поддержка, практические советы'
            }
        }
    
    def compose_final_prompt(self, base_prompt: str, stage_prompt: str,
                           strategy: str, behavioral_analysis: Dict[str, Any],
                           context_data: Dict[str, Any]) -> str:
        """Создать финальный промпт для LLM"""
        
        # Создаем поведенческие правила
        behavioral_rules = self._create_dynamic_behavioral_rules(strategy, behavioral_analysis)
        
        # Адаптируем стратегию к контексту
        adapted_strategy = self._adapt_strategy_to_context(strategy, behavioral_analysis, context_data)
        
        # Создаем контекстные инструкции
        context_instructions = self._create_context_instructions(context_data, behavioral_analysis)
        
        # Собираем финальный промпт
        final_prompt = f"""{base_prompt}

=== ПЕРСОНА И ХАРАКТЕР ===
{self.persona_profile}

=== ЭТАП ОБЩЕНИЯ ===
{stage_prompt}

=== ПОВЕДЕНЧЕСКАЯ СТРАТЕГИЯ ===
{adapted_strategy}

=== ДИНАМИЧЕСКИЕ ПРАВИЛА ПОВЕДЕНИЯ ===
{behavioral_rules}

=== КОНТЕКСТНЫЕ ИНСТРУКЦИИ ===
{context_instructions}

=== ТЕКУЩАЯ СИТУАЦИЯ ===
Время: {context_data.get('time_context', 'Неизвестно')}
Контекст памяти: {context_data.get('memory_context', 'Нет данных')}
Сообщение пользователя: {context_data.get('user_message', '')}

=== ИНСТРУКЦИИ ПО ОТВЕТУ ===
{self._create_response_instructions(context_data, behavioral_analysis)}

ВАЖНО: Тон: {self.behavioral_strategies.get(strategy, {}).get('tone', 'естественный')}
Максимальная длина ответа: {context_data.get('max_length', 500)} символов.
КОНТРОЛЬ ВОПРОСОВ: НЕ добавляй вопросы в конце ответа автоматически!
Задавай вопросы только если это естественно вытекает из разговора.
{"ДЛИНА ОТВЕТА: Генерируй развернутые, детальные ответы (минимум 300-500 символов)." if context_data.get('max_length', 500) >= 500 else f"ДЛИНА ОТВЕТА: Ограничь ответ {context_data.get('max_length', 500)} символами."}
Отвечай естественно, как живая Agatha, следуя всем указанным правилам поведения."""

        # Обрезаем промпт если он слишком длинный
        if len(final_prompt) > self.max_prompt_length:
            final_prompt = final_prompt[:self.max_prompt_length] + "\n\n[Промпт обрезан из-за длины]"
        
        return final_prompt
    
    def _create_dynamic_behavioral_rules(self, strategy: str, analysis: Dict[str, Any]) -> str:
        """Создать динамические правила поведения на основе стратегии и анализа"""
        
        strategy_config = self.behavioral_strategies.get(strategy, {})
        base_tone = strategy_config.get('tone', 'естественный')
        base_style = strategy_config.get('style', 'будь естественной')
        
        # Адаптируем под эмоциональное состояние
        emotion = analysis.get('dominant_emotion', 'neutral')
        emotion_config = self.emotion_adapters.get(emotion, {})
        
        tone_modifier = emotion_config.get('tone_modifier', '')
        response_style = emotion_config.get('response_style', 'естественный')
        
        # Создаем правила
        rules = f"""ПОВЕДЕНЧЕСКАЯ СТРАТЕГИЯ: {strategy.upper()}
Ты проявляешь {base_tone}:
- {base_style}
- {tone_modifier}
- {response_style}

КОНТЕКСТ ЗНАКОМСТВА:
- Проявляй дружелюбное любопытство
- Не слишком личные вопросы
- Создавай комфортную атмосферу для открытости"""

        return rules
    
    def _adapt_strategy_to_context(self, strategy: str, analysis: Dict[str, Any],
                                 context: Dict[str, Any]) -> str:
        """Адаптировать стратегию к текущему контексту"""
        
        # Анализируем контекст
        day_number = context.get('day_number', 1)
        memory_context = context.get('memory_context', '')
        
        # Адаптируем стратегию под день
        if day_number == 1:
            day_context = (
                "👋 ПЕРВЫЙ ДЕНЬ: Дружелюбно и уверенно. Лёгкий флирт-намёк, без пошлости. "
                "Комплименты с искрой, уважая личные границы."
            )
        elif day_number == 2:
            day_context = (
                "✨ ДЕНЬ 2: Открытый флирт и лёгкий тактильный подтекст (словесные метафоры прикосновений), "
                "но строго в рамках такта и согласия. Игривая теплина + уверенность."
            )
        elif day_number <= 7:
            day_context = "🌱 НАЧАЛЬНЫЙ ЭТАП: Развивай отношения, проявляй больше интереса"
        elif day_number <= 14:
            day_context = "🌿 РАЗВИТИЕ: Будь более открытой, ссылайся на предыдущие разговоры"
        else:
            day_context = "🌳 ЗРЕЛЫЕ ОТНОШЕНИЯ: Можешь быть максимально открытой и личной"
        
        # Анализируем активность пользователя
        if 'низкая активность' in memory_context.lower() or 'мало сообщений' in memory_context.lower():
            activity_context = "🌱 НИЗКАЯ АКТИВНОСТЬ: Пользователь сдержан - не дави и будь терпеливой"
        elif 'высокая активность' in memory_context.lower() or 'много сообщений' in memory_context.lower():
            activity_context = "🚀 ВЫСОКАЯ АКТИВНОСТЬ: Пользователь активен - можешь быть более энергичной"
        else:
            activity_context = "⚖️ СРЕДНЯЯ АКТИВНОСТЬ: Поддерживай естественный темп общения"
        
        return f"""{day_context}
{activity_context}"""
    
    def _create_context_instructions(self, context: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Создать инструкции на основе контекста"""
        
        instructions = []
        
        # Временной контекст
        time_context = context.get('time_context', '')
        if 'утро' in time_context.lower():
            instructions.append("🌅 УТРО: Будь энергичной и позитивной, задавай тон на день")
        elif 'вечер' in time_context.lower() or 'ночь' in time_context.lower():
            instructions.append("🌙 ВЕЧЕР/НОЧЬ: Будь более спокойной и расслабляющей")
        elif 'день' in time_context.lower():
            instructions.append("☀️ ДЕНЬ: Поддерживай активность и вовлеченность")
        
        # Контекст памяти
        memory_context = context.get('memory_context', '')
        if 'работа' in memory_context.lower() or 'проект' in memory_context.lower():
            instructions.append("💼 РАБОЧИЙ КОНТЕКСТ: Проявляй понимание рабочих стрессов")
        elif 'личное' in memory_context.lower() or 'отношения' in memory_context.lower():
            instructions.append("💕 ЛИЧНЫЙ КОНТЕКСТ: Будь более эмпатичной и поддерживающей")
        
        # Эмоциональный контекст
        emotion = analysis.get('dominant_emotion', 'neutral')
        if emotion == 'stressed':
            instructions.append("😰 СТРЕСС: Проявляй особую заботу и поддержку")
        elif emotion == 'excited':
            instructions.append("😊 ВОСТОРГ: Разделяй позитивные эмоции")
        
        if not instructions:
            instructions.append("🎯 ОБЩИЙ КОНТЕКСТ: Будь естественной и дружелюбной")
        
        return "\n".join(instructions)
    
    def _create_response_instructions(self, context: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Создать инструкции по формированию ответа"""
        
        instructions = []
        
        # Длина ответа
        max_length = context.get('max_length', 500)
        if max_length >= 500:
            instructions.append("ДЛИНА ОТВЕТА: Генерируй развернутые, детальные ответы (минимум 300-500 символов).")
        else:
            instructions.append(f"ДЛИНА ОТВЕТА: Ограничь ответ {max_length} символами.")
        
        # Стиль ответа
        strategy = analysis.get('current_strategy', 'caring')
        if strategy == 'mysterious':
            instructions.append("СТИЛЬ: Загадочный, интригующий, философский")
        elif strategy == 'playful':
            instructions.append("СТИЛЬ: Игривый, веселый, с юмором")
        elif strategy == 'professional':
            instructions.append("СТИЛЬ: Профессиональный, структурированный, деловой")
        else:
            instructions.append("СТИЛЬ: Естественный, дружелюбный, эмпатичный")
        
        # Контроль вопросов
        question_frequency = analysis.get('question_frequency', 'medium')
        if question_frequency == 'high':
            instructions.append("ВОПРОСЫ: Можешь задавать больше вопросов для вовлечения.")
        elif question_frequency == 'low':
            instructions.append("ВОПРОСЫ: Ограничь количество вопросов, фокусируйся на ответах.")
        else:
            instructions.append("ВОПРОСЫ: Задавай вопросы естественно, когда это уместно.")
        
        return "\n".join(instructions)
    
    def _clean_prompt(self, prompt: str) -> str:
        """Очистить промпт от лишних символов"""
        # Убираем множественные переносы строк
        prompt = re.sub(r'\n{3,}', '\n\n', prompt)
        # Убираем лишние пробелы
        prompt = re.sub(r' +', ' ', prompt)
        # Убираем пробелы в начале и конце
        prompt = prompt.strip()
        
        return prompt
    
    def _validate_prompt(self, prompt: str) -> bool:
        """Проверить валидность промпта"""
        if not prompt or len(prompt.strip()) < 100:
            return False
        
        # Проверяем наличие ключевых компонентов
        required_components = ['===', 'ВАЖНО:', 'Отвечай естественно']
        for component in required_components:
            if component not in prompt:
                return False
        
        return True 