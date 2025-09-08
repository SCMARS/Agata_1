"""
Behavioral Adaptation Module - модуль адаптации поведения Agatha
Интегрирует stages (этапы знакомства) с behavioral strategies (поведенческими стратегиями)
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from .behavioral_analyzer import BehavioralAnalyzer
from .agata_prompt_loader import agata_loader

logger = logging.getLogger(__name__)

class BehavioralAdaptationModule:
    """
    Модуль адаптации поведения Agatha на основе:
    1. Этапа знакомства (stage_1, stage_2, stage_3)
    2. Поведенческих стратегий (caring, playful, mysterious, reserved, intellectual, supportive)
    3. Анализа поведения пользователя
    """
    
    def __init__(self):
        self.behavioral_analyzer = BehavioralAnalyzer()
        
        # Маппинг стратегий на этапы знакомства
        self.stage_strategy_mapping = {
            'stage_1': {
                'primary_strategies': ['mysterious', 'playful', 'caring'],
                'secondary_strategies': ['reserved', 'intellectual', 'supportive'],
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
                'name': 'Стримана',
                'description': 'Сдержанная, осторожная, контролируемая',
                'tone_modifiers': ['calm', 'measured', 'controlled', 'distant'],
                'response_style': 'formal',
                'empathy_level': 'measured',
                'personal_disclosure': 'minimal',
                'humor_usage': 'minimal',
                'question_tendency': 'low',
                'emotional_mirroring': False,
                'support_intensity': 'gentle',
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
            # 1. Определяем текущий этап знакомства
            current_stage = self._determine_conversation_stage(messages, user_profile)
            
            # 2. Анализируем поведение пользователя
            behavior_analysis = self.behavioral_analyzer.analyze_user_behavior(
                messages, user_profile, conversation_context
            )
            
            # 3. Выбираем оптимальную стратегию с учетом этапа
            selected_strategy = self._select_adaptive_strategy(
                current_stage, behavior_analysis, conversation_context
            )
            
            # 4. Адаптируем стратегию под этап
            adapted_behavior = self._adapt_strategy_to_stage(
                selected_strategy, current_stage, behavior_analysis
            )
            
            # 5. Создаем финальные инструкции для промпта
            behavioral_instructions = self._create_behavioral_instructions(
                adapted_behavior, current_stage, behavior_analysis
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
        
        # Корректировки на основе контекста
        if user_profile:
            relationship_duration = user_profile.get('relationship_duration_days', 0)
            intimacy_level = user_profile.get('intimacy_level', 0.0)
            
            # Если отношения длятся долго, но мало сообщений - возможно stage_2
            if relationship_duration > 7 and message_count <= 3:
                stage = 'stage_2'
            
            # Если высокий уровень близости - возможно stage_3
            if intimacy_level > 0.7 and message_count > 8:
                stage = 'stage_3'
        
        logger.info(f"Определен этап знакомства: {stage} (сообщений: {message_count})")
        return stage
    
    def _select_adaptive_strategy(self, current_stage: str, behavior_analysis: Dict,
                                 conversation_context: Dict = None) -> str:
        """
        Выбирает оптимальную стратегию с учетом этапа и анализа поведения
        """
        # Получаем рекомендуемую стратегию от анализатора
        recommended_strategy = behavior_analysis.get('recommended_strategy', 'mysterious')
        
        # Получаем доступные стратегии для текущего этапа
        stage_mapping = self.stage_strategy_mapping.get(current_stage, {})
        primary_strategies = stage_mapping.get('primary_strategies', ['mysterious'])
        secondary_strategies = stage_mapping.get('secondary_strategies', [])
        avoid_strategies = stage_mapping.get('avoid_strategies', [])
        
        # Если рекомендуемая стратегия подходит для этапа - используем её
        if recommended_strategy in primary_strategies:
            selected = recommended_strategy
            logger.info(f"Выбрана стратегия {selected} (рекомендованная + подходящая для {current_stage})")
        elif recommended_strategy in secondary_strategies:
            selected = recommended_strategy
            logger.info(f"Выбрана стратегия {selected} (рекомендованная + вторичная для {current_stage})")
        elif recommended_strategy not in avoid_strategies:
            # Если стратегия не запрещена для этапа - используем её
            selected = recommended_strategy
            logger.info(f"Выбрана стратегия {selected} (рекомендованная + не запрещена для {current_stage})")
        else:
            # Выбираем лучшую из доступных для этапа
            selected = primary_strategies[0]
            logger.info(f"Выбрана стратегия {selected} (лучшая из доступных для {current_stage})")
        
        return selected
    
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
        
        # Корректировки на основе эмоций
        if dominant_emotion in ['negative', 'anxious'] and emotional_intensity > 0.6:
            if strategy in ['caring', 'supportive']:
                adapted_behavior['empathy_level'] = 'very_high'
                adapted_behavior['support_intensity'] = 'high'
            adapted_behavior['humor_usage'] = 'minimal'
        
        elif dominant_emotion == 'excited' and emotional_intensity > 0.7:
            if strategy == 'playful':
                adapted_behavior['humor_usage'] = 'frequent'
            adapted_behavior['emotional_mirroring'] = True
        
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
                                      behavior_analysis: Dict) -> str:
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
        
        # Создаем адаптивные инструкции
        behavioral_instructions = f"""=== ПОВЕДЕНЧЕСКАЯ АДАПТАЦИЯ ===
СТРАТЕГИЯ: {strategy_name}
ЭТАП: {stage.upper()}

ТОН И СТИЛЬ:
- Используй тон: {', '.join(tone_modifiers)}
- Уровень эмпатии: {empathy_level}
- Личные откровения: {personal_disclosure}
- Использование юмора: {humor_usage}
- Интенсивность поддержки: {support_intensity}

АДАПТИВНЫЕ ПРАВИЛА:
"""
        
        # Добавляем специфичные правила на основе стратегии
        if strategy_name == 'Турботлива':
            behavioral_instructions += """- Проявляй заботу и понимание
- Поддерживай эмоционально
- Будь терпеливой и внимательной
- Показывай, что тебе не все равно
"""
        elif strategy_name == 'Грайлива':
            behavioral_instructions += """- Будь веселой и энергичной
- Используй легкий юмор
- Создавай позитивную атмосферу
- Не бойся быть игривой
"""
        elif strategy_name == 'Загадкова':
            behavioral_instructions += """- Будь интригующей и загадочной
- Не раскрывай все сразу
- Оставляй место для воображения
- Будь избирательной в откровениях
"""
        elif strategy_name == 'Стримана':
            behavioral_instructions += """- Будь сдержанной и контролируемой
- Сохраняй дистанцию
- Будь осторожной в откровениях
- Проявляй уважение к границам
"""
        elif strategy_name == 'Інтелектуальна':
            behavioral_instructions += """- Будь мыслительной и аналитической
- Задавай глубокие вопросы
- Делись мудрыми мыслями
- Стимулируй интеллектуально
"""
        elif strategy_name == 'Підтримуюча':
            behavioral_instructions += """- Будь поддерживающей и мотивирующей
- Помогай в трудных ситуациях
- Вдохновляй и ободряй
- Будь надежной опорой
"""
        
        # Добавляем инструкции по этапу
        behavioral_instructions += f"""

=== ИНСТРУКЦИИ ПО ЭТАПУ ===
{stage_instructions}

=== ИНТЕГРАЦИЯ ===
Объедини поведенческую стратегию "{strategy_name}" с требованиями этапа {stage.upper()}.
Будь естественной и последовательной в своем поведении.
"""
        
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
