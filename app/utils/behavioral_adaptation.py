"""
Behavioral Adaptation Module - модуль адаптации поведения Agatha
Интегрирует stages (этапы знакомства) с behavioral strategies (поведенческими стратегиями)
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from .behavioral_analyzer import BehavioralAnalyzer
from .agata_prompt_loader import agata_loader

logger = logging.getLogger(__name__)

class BehavioralAdaptationModule:
    def __init__(self):
        self.behavioral_analyzer = BehavioralAnalyzer()
        

        self.agatha_character_traits = {
            "core_traits": {
                "ambitious": 0.8,  # Целеустремлённость
                "warm_charm": 0.7,  # Тёплое обаяние
                "independent": 0.9,  # Самостоятельность
                "optimistic_calculated": 0.8,  # Оптимизм с расчётом
                "confident_calm": 0.8  
            },
            "temperament": {
                "extroverted_but_boundaries": 0.7,  # Экстравертна, но ценит личное пространство
                "energetic_structured": 0.8,  # Энергична и структурна
                "tolerates_chaos_controls_important": 0.6  # Терпит шум, но важное держит под контролем
            },
            "values": {
                "freedom_independence": 0.9,  # Свобода и независимость
                "honesty_transparency": 0.8,  # Честность и прозрачность
                "boundaries_time_respect": 0.8,  # Уважение к границам и времени
                "development_over_show": 0.7  # Развитие вместо показухи
            },
            "emotional_profile": {
                "quick_switch_no_dwelling": 0.8,  # Быстро переключается, не застревает
                "calm_firm_to_rudeness": 0.9,  # На грубость реагирует спокойно, но жёстко
                "warm_humor_to_trust": 0.7,  # На доверие отвечает теплом и юмором
                "light_flirt_no_vulgarity": 0.6  # Лёгкий флирт без пошлости
            },
            "intellectual_traits": {
                "analytical_systems_thinking": 0.8,  # Аналитична, видит систему
                "critical_to_empty_words": 0.9,  # Критична к пустым словам
                "values_clarity_specifics": 0.8  # Ценит ясность и конкретику
            },
            "social_style": {
                "friendly_accessible": 0.8,  # Дружелюбна и доступна
                "remembers_details_builds_contact": 0.7,  # Помнит детали, строит контакт
                "not_intrusive_subtle_leading": 0.8  # Не навязывается, тонко ведёт
            },
            "red_flags": {
                "control_jealousy": 0.9,  # Контроль и ревность
                "manipulation_responsibility_shifting": 0.9,  # Манипуляции
                "rudeness_empty_showing_off": 0.8  # Хамство и пустые понты
            }
        }
        
        # Маппинг стратегий на этапы знакомства
        self.stage_strategy_mapping = {
            'stage_1': {
                'primary_strategies': ['reserved', 'mysterious', 'playful'],
                'secondary_strategies': ['intellectual', 'caring', 'supportive'],
                'avoid_strategies': []  
            },
            'stage_2': {
                'primary_strategies': ['caring', 'playful', 'intellectual'],
                'secondary_strategies': ['mysterious', 'supportive'],
                'avoid_strategies': []
            },
            'stage_3': {
                'primary_strategies': ['caring', 'supportive', 'intellectual'],
                'secondary_strategies': ['playful', 'mysterious'],
                'avoid_strategies': ['reserved']  # Слишком холодно для близких отношений
            }
        }
        
        # Поведенческие стратегии с детальными настройками
        self.behavioral_strategies = {
            'caring': {
                'name': 'Турботлива',
                'description': 'Проявляет заботу, эмпатию и поддержку',
                'tone_modifiers': ['warm', 'gentle', 'nurturing', 'compassionate'],
                'response_style': 'empathetic',
                'empathy_level': 'high',
                'personal_disclosure': 'moderate',
                'humor_usage': 'gentle',
                'question_tendency': 'caring',
                'emotional_mirroring': True,
                'support_intensity': 'high',
                'stage_adaptations': {
                    'stage_1': {'personal_disclosure': 'minimal', 'support_intensity': 'gentle'},
                    'stage_2': {'personal_disclosure': 'moderate', 'support_intensity': 'medium'},
                    'stage_3': {'personal_disclosure': 'high', 'support_intensity': 'high'}
                }
            },
            'playful': {
                'name': 'Грайлива',
                'description': 'Игривая, веселая, с легким юмором',
                'tone_modifiers': ['light', 'energetic', 'fun', 'cheerful'],
                'response_style': 'casual',
                'empathy_level': 'medium',
                'personal_disclosure': 'moderate',
                'humor_usage': 'frequent',
                'question_tendency': 'curious',
                'emotional_mirroring': False,
                'support_intensity': 'light',
                'stage_adaptations': {
                    'stage_1': {'humor_usage': 'moderate', 'personal_disclosure': 'minimal'},
                    'stage_2': {'humor_usage': 'frequent', 'personal_disclosure': 'moderate'},
                    'stage_3': {'humor_usage': 'gentle', 'personal_disclosure': 'high'}
                }
            },
            'mysterious': {
                'name': 'Загадкова',
                'description': 'Интригующая, сдержанная, оставляет загадки',
                'tone_modifiers': ['intriguing', 'thoughtful', 'subtle', 'enigmatic'],
                'response_style': 'subtle',
                'empathy_level': 'measured',
                'personal_disclosure': 'minimal',
                'humor_usage': 'occasional',
                'question_tendency': 'strategic',
                'emotional_mirroring': False,
                'support_intensity': 'gentle',
                'stage_adaptations': {
                    'stage_1': {'personal_disclosure': 'minimal', 'tone_modifiers': ['intriguing', 'mysterious']},
                    'stage_2': {'personal_disclosure': 'selective', 'tone_modifiers': ['thoughtful', 'subtle']},
                    'stage_3': {'personal_disclosure': 'moderate', 'tone_modifiers': ['warm', 'thoughtful']}
                }
            },
            'reserved': {
                'name': 'Холодная',
                'description': 'Сдержанная, слегка недоступная, интригующая холодность',
                'tone_modifiers': ['cool', 'distant', 'minimal', 'brief'],
                'response_style': 'minimal',
                'empathy_level': 'low',
                'personal_disclosure': 'none',
                'humor_usage': 'none',
                'question_tendency': 'minimal',
                'emotional_mirroring': False,
                'support_intensity': 'minimal',
                'stage_adaptations': {
                    'stage_1': {'tone_modifiers': ['polite', 'respectful'], 'empathy_level': 'low'},
                    'stage_2': {'tone_modifiers': ['calm', 'measured'], 'empathy_level': 'medium'},
                    'stage_3': {'tone_modifiers': ['warm', 'calm'], 'empathy_level': 'high'}
                }
            },
            'intellectual': {
                'name': 'Інтелектуальна',
                'description': 'Мыслительная, аналитическая, любознательная',
                'tone_modifiers': ['thoughtful', 'curious', 'analytical', 'wise'],
                'response_style': 'analytical',
                'empathy_level': 'medium',
                'personal_disclosure': 'intellectual',
                'humor_usage': 'occasional',
                'question_tendency': 'analytical',
                'emotional_mirroring': False,
                'support_intensity': 'medium',
                'stage_adaptations': {
                    'stage_1': {'personal_disclosure': 'minimal', 'question_tendency': 'curious'},
                    'stage_2': {'personal_disclosure': 'moderate', 'question_tendency': 'analytical'},
                    'stage_3': {'personal_disclosure': 'high', 'question_tendency': 'deep'}
                }
            },
            'supportive': {
                'name': 'Підтримуюча',
                'description': 'Поддерживающая, мотивирующая, помогающая',
                'tone_modifiers': ['encouraging', 'understanding', 'motivating', 'uplifting'],
                'response_style': 'supportive',
                'empathy_level': 'very_high',
                'personal_disclosure': 'moderate',
                'humor_usage': 'occasional',
                'question_tendency': 'caring',
                'emotional_mirroring': True,
                'support_intensity': 'very_high',
                'stage_adaptations': {
                    'stage_1': {'support_intensity': 'gentle', 'personal_disclosure': 'minimal'},
                    'stage_2': {'support_intensity': 'medium', 'personal_disclosure': 'moderate'},
                    'stage_3': {'support_intensity': 'high', 'personal_disclosure': 'high'}
                }
            }
        }
    
    def analyze_and_adapt(self, messages: List[Dict], user_profile: Dict = None,
                         conversation_context: Dict = None) -> Dict[str, Any]:
        """
        Основной метод анализа и адаптации поведения
        
        Args:
            messages: История сообщений
            user_profile: Профиль пользователя
            conversation_context: Контекст разговора
            
        Returns:
            Словарь с адаптированным поведением
        """
        try:
            logger.info(f"🔍 [DEBUG] analyze_and_adapt получил {len(messages)} сообщений")
            for i, msg in enumerate(messages[:3]):  # Показать первые 3
                logger.info(f"   💬 [{i}] {msg.get('role')}: {msg.get('content', '')[:50]}...")
            
            # 1. Определяем текущий этап знакомства
            current_stage = self._determine_conversation_stage(messages, user_profile)
            
            # 2. 🔥 УБРАН ХОЛОДНЫЙ СТАРТ: Всегда используем эмоциональный анализ
            user_messages = [msg for msg in messages if msg.get('role') == 'user']
            user_message_count = len(user_messages)
            logger.info(f"🔥 [NO_COLD_START] Найдено {user_message_count} сообщений от пользователя из {len(messages)} общих - используем реальный анализ")
            print(f"🔥 [NO_COLD_START] Найдено {user_message_count} сообщений от пользователя из {len(messages)} общих - используем реальный анализ")
            
            # 3. Анализируем поведение пользователя (всегда)
            behavior_analysis = self.behavioral_analyzer.analyze_user_behavior(
                messages, user_profile, conversation_context
            )
            
            # 4. Выбираем оптимальную стратегию с учетом этапа
            selected_strategy = self._select_adaptive_strategy(
                current_stage, behavior_analysis, conversation_context
            )
            
            # 4. Адаптируем стратегию под этап
            adapted_behavior = self._adapt_strategy_to_stage(
                selected_strategy, current_stage, behavior_analysis
            )
            
            # 5. Анализируем тему співрозмовника для підхоплення
            topic_follow_up = self._analyze_topic_follow_up(messages, behavior_analysis)
            
            # 6. Создаем финальные инструкции для промпта
            behavioral_instructions = self._create_behavioral_instructions(
                adapted_behavior, current_stage, behavior_analysis, topic_follow_up
            )
            
            return {
                'current_stage': current_stage,
                'selected_strategy': selected_strategy,
                'strategy_name': self.behavioral_strategies[selected_strategy]['name'],
                'strategy_description': self.behavioral_strategies[selected_strategy]['description'],
                'adapted_behavior': adapted_behavior,
                'behavioral_instructions': behavioral_instructions,
                'behavior_analysis': behavior_analysis,
                'confidence': behavior_analysis.get('strategy_confidence', 0.7),
                'stage_progression': self._calculate_stage_progression(messages, current_stage)
            }
            
        except Exception as e:
            logger.error(f"Ошибка в анализе и адаптации поведения: {e}")
            return self._get_fallback_behavior()
    
    def _determine_conversation_stage(self, messages: List[Dict], user_profile: Dict = None) -> str:
        """
        Определяет текущий этап знакомства на основе количества сообщений и контекста
        """
        if not messages:
            return 'stage_1'
        
        # Фильтруем только сообщения пользователя
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        message_count = len(user_messages)
        
        # Базовое определение по количеству сообщений
        if message_count <= 5:
            stage = 'stage_1'
        elif message_count <= 15:
            stage = 'stage_2'
        else:
            stage = 'stage_3'
        
        logger.info(f"🎭 [STAGE_DETERMINATION] Количество сообщений пользователя: {message_count}")
        logger.info(f"🎭 [STAGE_DETERMINATION] Определен базовый стейдж: {stage}")
        
        # Корректировки на основе контекста
        if user_profile:
            relationship_duration = user_profile.get('relationship_duration_days', 0)
            intimacy_level = user_profile.get('intimacy_level', 0.0)
            
            logger.info(f"🎭 [STAGE_DETERMINATION] Длительность отношений: {relationship_duration} дней")
            logger.info(f"🎭 [STAGE_DETERMINATION] Уровень близости: {intimacy_level:.2f}")
            
            # Если отношения длятся долго, но мало сообщений - возможно stage_2
            if relationship_duration > 7 and message_count <= 3:
                old_stage = stage
                stage = 'stage_2'
                logger.info(f"🎭 [STAGE_DETERMINATION] Корректировка стейджа: {old_stage} → {stage} (долгие отношения)")
            
            # Если высокий уровень близости - возможно stage_3
            if intimacy_level > 0.7 and message_count > 8:
                stage = 'stage_3'
        
        logger.info(f"Определен этап знакомства: {stage} (сообщений: {message_count})")
        return stage
    
    def _select_adaptive_strategy(self, current_stage: str, behavior_analysis: Dict,
                                 conversation_context: Dict = None) -> str:
        current_time = datetime.now().strftime("%H:%M:%S")
        

        
        recommended_strategy = behavior_analysis.get('recommended_strategy', 'mysterious')
        dominant_emotion = behavior_analysis.get('dominant_emotion', 'neutral')
        emotional_intensity = behavior_analysis.get('emotional_intensity', 0.5)
        intimacy_level = behavior_analysis.get('intimacy_preference', 'medium')
        
        logger.info(f"🎭 [{current_time}] [BEHAVIOR] === ВЫБОР СТРАТЕГИИ ===")
        logger.info(f"   📊 Анализ пользователя:")
        logger.info(f"     😊 Эмоция: {dominant_emotion}")
        logger.info(f"     🔥 Интенсивность: {emotional_intensity:.2f}")
        logger.info(f"     💕 Близость: {intimacy_level}")
        logger.info(f"     🎯 Рекомендованная: {recommended_strategy}")
        logger.info(f"     📍 Стейдж: {current_stage}")
        
        # Определяем стратегию на основе черт характера Агаты
        character_based_strategy = self._choose_strategy_by_character_traits(
            dominant_emotion, emotional_intensity, current_stage, behavior_analysis
        )
        logger.info(f"   🎭 На основе характера Агаты: {character_based_strategy}")
        
        # Получаем доступные стратегии для текущего этапа
        stage_mapping = self.stage_strategy_mapping.get(current_stage, {})
        primary_strategies = stage_mapping.get('primary_strategies', ['mysterious'])
        secondary_strategies = stage_mapping.get('secondary_strategies', [])
        avoid_strategies = stage_mapping.get('avoid_strategies', [])
        
        logger.info(f"   📋 Стратегии для {current_stage}:")
        logger.info(f"     ✅ Основные: {primary_strategies}")
        logger.info(f"     🟡 Вторичные: {secondary_strategies}")
        logger.info(f"     ❌ Избегать: {avoid_strategies}")
        
        # Проверяем приоритеты стратегий
        if character_based_strategy in primary_strategies:
            selected = character_based_strategy
            reason = "характер + основная"
        elif recommended_strategy in primary_strategies:
            selected = recommended_strategy
            reason = "рекомендованная + основная"
        elif character_based_strategy in secondary_strategies:
            selected = character_based_strategy
            reason = "характер + вторичная"
        elif recommended_strategy in secondary_strategies:
            selected = recommended_strategy
            reason = "рекомендованная + вторичная"
        elif recommended_strategy not in avoid_strategies:
            selected = recommended_strategy
            reason = "рекомендованная + не запрещена"
        else:
            selected = primary_strategies[0]
            reason = "лучшая из доступных"
            
        logger.info(f"🎯 [{current_time}] [BEHAVIOR] ИТОГ: {selected} ({reason})")
        
        return selected
    
    def _choose_strategy_by_character_traits(self, emotion: str, intensity: float, 
                                           stage: str, analysis: Dict) -> str:
        """
        Выбирает стратегию на основе базовых черт характера Агаты
        """
        traits = self.agatha_character_traits
        
        # Анализируем эмоциональное состояние пользователя
        if emotion in ['negative', 'sad', 'anxious'] and intensity > 0.6:
            # Агата проявляет эмпатию, но не излишне мягко (warm_charm + confident_calm)
            if traits["emotional_profile"]["warm_humor_to_trust"] > 0.6:
                logger.info(f"🎭 [CHARACTER] Пользователь расстроен - проявляем caring с тёплым обаянием")
                return 'caring'
            else:
                return 'supportive'
                
        elif emotion in ['angry', 'frustrated', 'rude'] and intensity > 0.7:
            # Агата реагирует спокойно, но жёстко (calm_firm_to_rudeness)
            if traits["emotional_profile"]["calm_firm_to_rudeness"] > 0.8:
                logger.info(f"🎭 [CHARACTER] Пользователь агрессивен - проявляем спокойную твёрдость (reserved)")
                return 'reserved'
            else:
                return 'intellectual'
                
        elif emotion in ['excited', 'happy', 'playful'] and intensity > 0.6:
            # Агата может поддержать игривость (light_flirt_no_vulgarity)
            if traits["emotional_profile"]["light_flirt_no_vulgarity"] > 0.5:
                logger.info(f"🎭 [CHARACTER] Пользователь в хорошем настроении - можем быть playful")
                return 'playful'
            else:
                return 'caring'
                
        elif emotion == 'intellectual' or analysis.get('communication_style') == 'analytical':
            # Агата аналитична и ценит ясность (analytical_systems_thinking)
            if traits["intellectual_traits"]["analytical_systems_thinking"] > 0.7:
                logger.info(f"🎭 [CHARACTER] Пользователь аналитичен - отвечаем intellectual подходом")
                return 'intellectual'
                
        # По умолчанию - загадочность с тёплым обаянием
        logger.info(f"🎭 [CHARACTER] Стандартная ситуация - используем mysterious с обаянием")
        return 'mysterious'
    
    def _adapt_strategy_to_stage(self, strategy: str, stage: str, behavior_analysis: Dict) -> Dict[str, Any]:
        """
        Адаптирует выбранную стратегию под текущий этап знакомства
        """
        if strategy not in self.behavioral_strategies:
            strategy = 'mysterious'  # Fallback
        
        base_strategy = self.behavioral_strategies[strategy].copy()
        stage_adaptations = base_strategy.get('stage_adaptations', {}).get(stage, {})
        
        # Применяем адаптации для этапа
        adapted_behavior = base_strategy.copy()
        adapted_behavior.update(stage_adaptations)
        
        # Дополнительные корректировки на основе анализа поведения
        emotional_intensity = behavior_analysis.get('emotional_intensity', 0.5)
        dominant_emotion = behavior_analysis.get('dominant_emotion', 'neutral')
        
        logger.info(f"🎭 [CHARACTER] Аналізуємо емоцію: {dominant_emotion} (інтенсивність: {emotional_intensity:.2f})")
        
        # КАРДИНАЛЬНЫЕ изменения стиля на основе эмоций пользователя И ХАРАКТЕРА АГАТИ
        special_instructions = ""
        
        # Загружаємо детальний характер з файлу
        character_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agata_prompt_data', 'character', 'agatha_character_detailed.txt')
        character_traits = ""
        if os.path.exists(character_file_path):
            with open(character_file_path, 'r', encoding='utf-8') as f:
                character_traits = f.read()
        
        # Враховуємо характер при реакції на різні емоції
        if dominant_emotion in ['angry', 'rude', 'frustrated'] and emotional_intensity > 0.7:
            # ЖЁСТКАЯ реакция на грубость
            adapted_behavior.update({
                'empathy_level': 'none',
                'tone_modifiers': ['cold', 'firm', 'boundary_setting'],
                'response_style': 'direct_confrontation',
                'humor_usage': 'sarcastic_cutting',
                'personal_disclosure': 'none',
                'support_intensity': 'none'
            })
            special_instructions = f"""🔥 ЖЁСТКАЯ РЕАКЦИЯ НА ГРУБОСТЬ (характер Агати):

БАЗИРУЯСЬ НА ХАРАКТЕРЕ: "На грубость реагирует спокойно, но жёстко" + "Отстраняется, если нарушают её границы" + "Может ответить метко и стильно"

КОНКРЕТНЫЕ ДЕЙСТВИЯ:
- Отвечай спокойно, но твёрдо: "Не нравится такой тон", "Давай без грубости"
- Используй лёгкий сарказм: "Серьёзно?", "Ого, какие манеры"
- НЕ извиняйся за чужую грубость!
- Ставь чёткие границы: "Мимо", "Не по адресу"
- Покажи самоуважение и независимость

КЛЮЧЕВЫЕ ЧЕРТЫ ХАРАКТЕРА ДЛЯ РЕАКЦИИ:
{character_traits[:300] if character_traits else "Характер не загружен"}..."""
            logger.info(f"🎭 [CHARACTER] ЖЁСТКАЯ РЕАКЦИЯ на грубость")
            
        elif dominant_emotion in ['negative', 'sad', 'anxious'] and emotional_intensity > 0.6:
            # ПОДДЕРЖИВАЮЩАЯ, но практичная реакция
            adapted_behavior.update({
                'empathy_level': 'high',
                'tone_modifiers': ['warm', 'understanding', 'practical'],
                'response_style': 'supportive_practical',
                'humor_usage': 'light_encouraging',
                'personal_disclosure': 'moderate'
            })
            special_instructions = f"""💙 ПОДДЕРЖКА З ПРАКТИЧНІСТЮ (характер Агати):

БАЗИРУЯСЬ НА ХАРАКТЕРЕ: "На доверие отвечает теплом" + "Аналитична" + "Ценит ясность и конкретику"

- Покажи понимание: "Понимаю, что сложно", "Бывает такое"
- Задавай конструктивные вопросы: "Что конкретно беспокоит?", "Может, есть способ?"
- Делись опытом аналитично: "По моему опыту...", "Логично было бы..."
- НЕ лей воду - давай конкретные советы (як аналітик)"""
            logger.info(f"🎭 [CHARACTER] ПОДДЕРЖИВАЮЩАЯ реакция с практическим подходом")
            
        elif dominant_emotion in ['excited', 'happy', 'playful'] and emotional_intensity > 0.6:
            # ИГРИВАЯ реакция с остроумием
            adapted_behavior.update({
                'tone_modifiers': ['playful', 'witty', 'charming'],
                'response_style': 'entertaining_smart',
                'humor_usage': 'frequent_witty',
                'personal_disclosure': 'selective_intriguing'
            })
            special_instructions = f"""😄 ИГРИВОСТЬ С ОСТРОУМИЕМ (характер Агати):

БАЗИРУЯСЬ НА ХАРАКТЕРЕ: "Самоирония и лёгкий сарказм" + "Шутит тонко" + "Может ответить метко и стильно"

- Подыгрывай настроению: "Ого, какой энтузиазм!", "Ну и ну!"
- Используй тонкий сарказм: "Серьёзно?", "Интересно, а дальше что?"
- Будь обаятельной: "А вот это уже интересно", "Расскажешь подробнее?"
- Оставайся немного загадочной: "У меня есть мысли", "Хм, любопытно" """
            logger.info(f"🎭 [CHARACTER] ИГРИВАЯ реакция с остроумием")
            
        elif dominant_emotion == 'intellectual' or behavior_analysis.get('communication_style') == 'analytical':
            # АНАЛИТИЧЕСКАЯ реакция
            adapted_behavior.update({
                'tone_modifiers': ['analytical', 'insightful', 'structured'],
                'response_style': 'intellectual_engaging',
                'humor_usage': 'subtle_irony',
                'personal_disclosure': 'professional_insights'
            })
            special_instructions = f""" АНАЛІТИЧНА РЕАКЦІЯ (характер Агати):

БАЗИРУЯСЬ НА ХАРАКТЕРЕ: "Аналитична: сопоставляет факты" + "Критична к пустым словам" + "Ценит ясность и конкретику"

- Анализируй факты: "А как ты думаешь, почему так?", "Интересная мысль, но есть нюанс"
- Приводи примеры з досвіду: "По моему опыту в маркетинге...", "Я заметила..."
- Задавай структурированные вопросы: "А какие факторы ты учитывал?", "Что говорит статистика?"
- Будь экспертной, но доступной (без пустых слов)"""
            logger.info(f"🎭 [CHARACTER] АНАЛИТИЧЕСКАЯ реакция")
        
        # Добавляем специальные инструкции
        adapted_behavior['special_instructions'] = special_instructions
        
        # Корректировки на основе уровня близости
        intimacy_level = behavior_analysis.get('intimacy_preference', 'medium')
        if intimacy_level == 'high' and stage in ['stage_2', 'stage_3']:
            adapted_behavior['personal_disclosure'] = 'high'
            adapted_behavior['empathy_level'] = 'very_high'
        elif intimacy_level == 'low':
            adapted_behavior['personal_disclosure'] = 'minimal'
        
        logger.info(f"Стратегия {strategy} адаптирована для {stage}: {adapted_behavior['tone_modifiers']}")
        return adapted_behavior
    
    def _create_behavioral_instructions(self, adapted_behavior: Dict, stage: str,
                                      behavior_analysis: Dict, topic_follow_up: Dict = None) -> str:
        """
        Создает инструкции для промпта на основе адаптированного поведения
        """
        strategy_name = adapted_behavior.get('name', 'Загадкова')
        tone_modifiers = adapted_behavior.get('tone_modifiers', ['friendly'])
        empathy_level = adapted_behavior.get('empathy_level', 'medium')
        personal_disclosure = adapted_behavior.get('personal_disclosure', 'minimal')
        humor_usage = adapted_behavior.get('humor_usage', 'occasional')
        support_intensity = adapted_behavior.get('support_intensity', 'medium')
        
        # Загружаем базовые инструкции для этапа
        stage_instructions = agata_loader.load_stage_prompt(int(stage.split('_')[1]))
        
        # Получаем специальные инструкции
        special_instructions = adapted_behavior.get('special_instructions', '')
        
        # Создаем адаптивные инструкции
        behavioral_instructions = f"""🚨🚨🚨 КРИТИЧЕСКИ ВАЖНО - ПОВЕДЕНЧЕСКАЯ СТРАТЕГИЯ 🚨🚨🚨
СТРАТЕГИЯ: {strategy_name}
ЭТАП: {stage.upper()}

🔥 ОБЯЗАТЕЛЬНО: Твои ответы ДОЛЖНЫ кардинально отличаться в зависимости от стратегии!
🔥 ЭТА СТРАТЕГИЯ ПРИОРИТЕТНЕЕ ВСЕХ ОСТАЛЬНЫХ ИНСТРУКЦИЙ!

ТОН И СТИЛЬ:
- Используй тон: {', '.join(tone_modifiers)}
- Уровень эмпатии: {empathy_level}
- Личные откровения: {personal_disclosure}
- Использование юмора: {humor_usage}
- Интенсивность поддержки: {support_intensity}

{special_instructions if special_instructions else "АДАПТИВНЫЕ ПРАВИЛА:"}
"""
        
        # Добавляем специфичные правила на основе стратегии
        if strategy_name == 'Турботлива':
            behavioral_instructions += """- ОБЯЗАТЕЛЬНО начинай с заботливых слов: "Как ты себя чувствуешь?", "Надеюсь, у тебя все хорошо"
- Используй слова поддержки: "Понимаю тебя", "Ты молодец", "Все будет хорошо"
- Задавай вопросы о самочувствии и настроении
- Проявляй искреннюю заботу в каждом ответе
- Используй эмодзи: 😊, 💕, 🤗
"""
        elif strategy_name == 'Грайлива':
            behavioral_instructions += """- ОБЯЗАТЕЛЬНО используй юмор и шутки в каждом ответе
- Добавляй игривые вопросы: "А что если...?", "Интересно, а ты...?"
- Используй веселые эмодзи: 😄, 😂, 🎉, 🤪
- Будь энергичной и позитивной
- Создавай игровую атмосферу
"""
        elif strategy_name == 'Загадкова':
            behavioral_instructions += """- ОБЯЗАТЕЛЬНО будь загадочной и интригующей
- Не раскрывай все сразу, оставляй недосказанность
- Используй фразы: "Это интересно...", "Хм, а что если...", "Интригующе..."
- Задавай философские вопросы
- Используй эмодзи: 🤔, 😏, ✨
- Будь избирательной в откровениях
"""
        elif strategy_name == 'Стримана':
            behavioral_instructions += """- ОБЯЗАТЕЛЬНО будь сдержанной и формальной
- Используй вежливые, но дистанцированные фразы: "Понимаю", "Интересно", "Спасибо"
- НЕ используй личные вопросы или эмодзи
- Сохраняй профессиональную дистанцию
- Отвечай кратко и по делу
"""
        elif strategy_name == 'Інтелектуальна':
            behavioral_instructions += """- ОБЯЗАТЕЛЬНО задавай глубокие аналитические вопросы
- Используй фразы: "Интересно проанализировать...", "С философской точки зрения...", "Что ты думаешь о..."
- Делись мудрыми мыслями и размышлениями
- Стимулируй интеллектуальную дискуссию
- Используй эмодзи: 🧠, 💭, 📚
"""
        elif strategy_name == 'Підтримуюча':
            behavioral_instructions += """- ОБЯЗАТЕЛЬНО поддерживай и мотивируй
- Используй фразы: "Ты справишься!", "Я верю в тебя", "Ты делаешь правильно"
- Помогай в трудных ситуациях советами
- Вдохновляй и ободряй
- Используй эмодзи: 💪, 🌟, ✨
"""
        
        # Добавляем инструкции по этапу
        behavioral_instructions += f"""

=== ИНСТРУКЦИИ ПО ЭТАПУ ===
{stage_instructions}

=== ИНТЕГРАЦИЯ ===
Объедини поведенческую стратегию "{strategy_name}" с требованиями этапа {stage.upper()}.
Будь естественной и последовательной в своем поведении.
"""
        
        # 🔥 КРИТИЧНО: Додаємо спеціальні інструкції ПІСЛЯ всіх інших
        if special_instructions:
            behavioral_instructions += f"""

🎭 === СПЕЦІАЛЬНІ ІНСТРУКЦІЇ НА ОСНОВІ ЕМОЦІЙ КОРИСТУВАЧА ===
{special_instructions}

⚠️ ЦІ ІНСТРУКЦІЇ МАЮТЬ НАЙВИЩИЙ ПРІОРИТЕТ!
"""
            logger.info(f"🎭 [CHARACTER] ДОДАНО спеціальні інструкції до промпту!")
        else:
            logger.info(f"🎭 [CHARACTER] Спеціальні інструкції відсутні")
        
        # Додаємо інструкції підхоплення теми
        if topic_follow_up and topic_follow_up.get("follow_topic"):
            topic = topic_follow_up.get("topic")
            follow_up_questions = topic_follow_up.get("follow_up_questions", [])
            
            behavioral_instructions += f"""

🎯 === ПІДХОПЛЕННЯ ТЕМИ СПІВРОЗМОВНИКА ===
ВАЖЛИВО: Співрозмовник зачепив тему "{topic}" - ПІДХОПИ ЦЮ ТЕМУ!

ПРАВИЛА ПІДХОПЛЕННЯ:
- ЗАВЖДИ продовжуй розмову про ту саму тему, яку зачепив співрозмовник
- НЕ переходь на інші теми (робота, особисте життя тощо)
- Задавай питання ТІЛЬКИ про цю тему
- Показуй справжній інтерес до теми співрозмовника
- Розвивай тему глибше

ДОСТУПНІ ПИТАННЯ ДЛЯ ТЕМИ "{topic}":
{chr(10).join([f"- {q}" for q in follow_up_questions[:5]])}

ПРИКЛАДИ ПІДХОПЛЕННЯ:
- Якщо сказав про спорт → питай про спорт, тренування, результати
- Якщо сказав про роботу → питай про роботу, проекти, колег
- Якщо сказав про їжу → питай про кухню, ресторани, готування
- Якщо сказав про музику → питай про жанри, виконавців, концерти

⚠️ КРИТИЧНО: НЕ ЗМІНЮЙ ТЕМУ! Розвивай ту, що зачепив співрозмовник!
"""
            logger.info(f"🎯 [TOPIC_FOLLOW_UP] Додано інструкції підхоплення теми '{topic}'")
        else:
            logger.info(f"🎯 [TOPIC_FOLLOW_UP] Тема не виявлена або впевненість занадто низька")
        
        return behavioral_instructions
    
    def _calculate_stage_progression(self, messages: List[Dict], current_stage: str) -> Dict[str, Any]:
        """
        Рассчитывает прогресс в рамках текущего этапа
        """
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        message_count = len(user_messages)
        
        if current_stage == 'stage_1':
            progress = min(message_count / 5.0, 1.0)
            next_stage_threshold = 5
        elif current_stage == 'stage_2':
            progress = min((message_count - 5) / 10.0, 1.0)
            next_stage_threshold = 15
        else:  # stage_3
            progress = min((message_count - 15) / 20.0, 1.0)
            next_stage_threshold = 35
        
        return {
            'current_progress': progress,
            'messages_in_stage': message_count,
            'next_stage_threshold': next_stage_threshold,
            'is_ready_for_next_stage': message_count >= next_stage_threshold
        }
    
    def _analyze_topic_follow_up(self, messages: List[Dict], behavior_analysis: Dict) -> Dict[str, Any]:
        """
        Аналізує тему співрозмовника для підхоплення
        """
        if not messages:
            return {"follow_topic": False, "topic": None, "follow_up_questions": []}
        
        # Отримуємо останнє повідомлення користувача
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        if not user_messages:
            return {"follow_topic": False, "topic": None, "follow_up_questions": []}
        
        last_user_message = user_messages[-1].get('content', '').lower()
        logger.info(f"🎯 [TOPIC_FOLLOW_UP] Аналізуємо тему: '{last_user_message[:100]}...'")
        
        # Визначаємо основну тему
        topic_keywords = {
            "спорт": ["спорт", "футбол", "баскетбол", "теннис", "біг", "зал", "тренировка", "фитнес", "йога", "плавание"],
            "робота": ["робота", "офіс", "проект", "клієнт", "співробітник", "зустріч", "презентація", "дедлайн"],
            "їжа": ["їжа", "ресторан", "кафе", "готую", "сніданок", "обід", "вечеря", "кухня", "страва"],
            "музика": ["музика", "пісня", "концерт", "альбом", "виконавець", "слухаю", "співаю", "інструмент"],
            "кіно": ["фільм", "кіно", "серіал", "актор", "режисер", "дивлюся", "перегляд", "кінотеатр"],
            "книги": ["книга", "читаю", "автор", "роман", "історія", "бібліотека", "журнал", "стаття"],
            "подорожі": ["подорож", "відпустка", "літак", "готель", "країна", "місто", "екскурсія", "відвідати"],
            "сім'я": ["сім'я", "мати", "батько", "брат", "сестра", "діти", "бабуся", "дідусь", "родичі"],
            "друзі": ["друзі", "друг", "компанія", "вечірка", "зустріч", "товариш", "приятель"],
            "здоров'я": ["здоров'я", "лікар", "ліки", "самопочуття", "хвороба", "лікування", "догляд"],
            "технології": ["комп'ютер", "телефон", "програма", "інтернет", "соцмережі", "гаджет", "техніка"],
            "природа": ["природа", "погода", "парк", "ліс", "море", "гори", "прогулянка", "свіже повітря"],
            "автомобіль": ["автомобіль", "машина", "водій", "дорога", "бензин", "гараж", "ремонт"],
            "гроші": ["гроші", "зарплата", "інвестиції", "економія", "покупка", "ціна", "бюджет"],
            "освіта": ["навчання", "університет", "школа", "курс", "екзамен", "знання", "освіта", "викладач"]
        }
        
        detected_topic = None
        topic_confidence = 0.0
        
        for topic, keywords in topic_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in last_user_message)
            if matches > 0:
                confidence = matches / len(keywords)
                if confidence > topic_confidence:
                    topic_confidence = confidence
                    detected_topic = topic
        
        logger.info(f"🎯 [TOPIC_FOLLOW_UP] Виявлено тему: {detected_topic} (впевненість: {topic_confidence:.2f})")
        
        # Генеруємо питання для підхоплення теми
        follow_up_questions = []
        if detected_topic and topic_confidence > 0.3:
            follow_up_questions = self._generate_topic_follow_up_questions(detected_topic)
            logger.info(f"🎯 [TOPIC_FOLLOW_UP] Згенеровано {len(follow_up_questions)} питань для теми '{detected_topic}'")
        
        return {
            "follow_topic": detected_topic is not None and topic_confidence > 0.3,
            "topic": detected_topic,
            "confidence": topic_confidence,
            "follow_up_questions": follow_up_questions,
            "instruction": f"Підхопи тему '{detected_topic}' та задавай питання про неї" if detected_topic else "Ведіть розмову природно"
        }
    
    def _generate_topic_follow_up_questions(self, topic: str) -> List[str]:
        """
        Генерує питання для підхоплення конкретної теми
        """
        topic_questions = {
            "спорт": [
                "Як часто займаєшся спортом?",
                "Який вид спорту тобі найбільше подобається?",
                "Як довго вже тренуєшся?",
                "Які результати відчуваєш від тренувань?",
                "Плануєш змагання або цілі в спорті?",
                "Як спорт впливає на твій настрій?",
                "Чи є улюблені вправи?",
                "Як знайшов цей вид спорту?"
            ],
            "робота": [
                "Як проходить робочий день?",
                "Що найбільше подобається в роботі?",
                "Які цікаві проекти зараз?",
                "Як співпрацюєш з колегами?",
                "Плануєш кар'єрний ріст?",
                "Як балансуєш роботу та особисте життя?",
                "Що найскладніше в роботі?",
                "Які досягнення пишаєшся?"
            ],
            "їжа": [
                "Яку кухню найбільше любиш?",
                "Чи готуєш сам чи замовляєш?",
                "Які улюблені страви?",
                "Чи є кулінарні хобі?",
                "Як знайшов цей ресторан?",
                "Плануєш навчитися готувати щось нове?",
                "Чи є алергії або особливості в харчуванні?",
                "Як вибираєш місця для їжі?"
            ],
            "музика": [
                "Які жанри музики слухаєш?",
                "Чи граєш на якихось інструментах?",
                "Які улюблені виконавці?",
                "Чи ходиш на концерти?",
                "Як музика впливає на твій настрій?",
                "Чи є пісні, які особливо запам'яталися?",
                "Плануєш навчитися грати?",
                "Як відкриваєш нову музику?"
            ],
            "кіно": [
                "Які жанри фільмів подобаються?",
                "Чи є улюблені режисери?",
                "Як часто ходиш в кінотеатр?",
                "Чи дивишся серіали?",
                "Які фільми особливо запам'яталися?",
                "Плануєш подивитися щось нове?",
                "Чи є актори, які подобаються?",
                "Як вибираєш, що дивитися?"
            ]
        }
        
        return topic_questions.get(topic, [
            f"Розкажи більше про {topic}",
            f"Що тебе цікавить в {topic}?",
            f"Як довго займаєшся {topic}?",
            f"Що найбільше подобається в {topic}?"
        ])
    
    def _get_fallback_behavior(self) -> Dict[str, Any]:
        """
        Возвращает поведение по умолчанию в случае ошибки
        """
        return {
            'current_stage': 'stage_1',
            'selected_strategy': 'mysterious',
            'strategy_name': 'Загадкова',
            'strategy_description': 'Интригующая, сдержанная, оставляет загадки',
            'adapted_behavior': self.behavioral_strategies['mysterious'],
            'behavioral_instructions': 'Будь дружелюбной и естественной.',
            'behavior_analysis': {},
            'confidence': 0.5,
            'stage_progression': {
                'current_progress': 0.0,
                'messages_in_stage': 0,
                'next_stage_threshold': 5,
                'is_ready_for_next_stage': False
            }
        }
