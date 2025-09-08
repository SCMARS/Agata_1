"""
Behavioral Analyzer - модуль анализа поведения пользователя для выбора стратегий
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

class BehavioralAnalyzer:
    """
    Анализирует поведение пользователя и выбирает оптимальную стратегию поведения для Agatha
    
    Зона ответственности:
    1. Анализ сообщений пользователя (эмоции, темы, паттерны)
    2. Выбор поведенческой стратегии на основе анализа
    3. Подготовка динамических правил поведения для PromptComposer
    """
    
    def __init__(self):
        # Эмоциональные паттерны для анализа состояний пользователя
        self.emotion_patterns = {
            'positive': {
                'keywords': ['отлично', 'хорошо', 'прекрасно', 'замечательно', 'великолепно', 
                           'радуюсь', 'счастлив', 'восторг', 'ура', 'супер', 'класс', 'круто'],
                'emojis': ['😊', '😄', '😁', '🎉', '👍', '❤️', '😍'],
                'punctuation': ['!', '!!']
            },
            'negative': {
                'keywords': ['плохо', 'ужасно', 'грустно', 'депрессия', 'проблемы', 'беда',
                           'потерял', 'потеря', 'не знаю что делать', 'валится из рук',
                           'расстроен', 'подавлен', 'тяжело', 'трудно', 'кошмар'],
                'emojis': ['😢', '😭', '😞', '💔', '😔', '😟'],
                'punctuation': ['...', '((', '))']
            },
            'excited': {
                'keywords': ['возбужден', 'взволнован', 'не могу дождаться', 'предвкушение',
                           'обожаю', 'обалдеть', 'невероятно', 'потрясающе'],
                'emojis': ['🤩', '😲', '🚀', '⚡'],
                'punctuation': ['!!!', '!?']
            },
            'angry': {
                'keywords': ['злой', 'бесит', 'раздражает', 'ненавижу', 'достал', 'надоело',
                           'сил нет', 'идиот', 'дурак', 'глупо', 'возмущен'],
                'emojis': ['😠', '😡', '🤬', '💢'],
                'punctuation': ['!', '!!!']
            },
            'anxious': {
                'keywords': ['беспокоюсь', 'волнуюсь', 'переживаю', 'тревожно', 'боюсь',
                           'нервничаю', 'стресс', 'паника', 'страшно'],
                'emojis': ['😰', '😨', '😬', '🤯'],
                'punctuation': ['...']
            },
            'tired': {
                'keywords': ['устал', 'усталость', 'выматывает', 'нет сил', 'измотан',
                           'сложный день', 'тяжелый день', 'много работы'],
                'emojis': ['😴', '🥱', '😪'],
                'punctuation': ['...']
            },
            'confused': {
                'keywords': ['не понимаю', 'запутался', 'сложно', 'непонятно', 'не знаю',
                           'что делать', 'как быть', 'растерян'],
                'emojis': ['😕', '🤔', '😵‍💫'],
                'punctuation': ['???', '??']
            }
        }
        
        # Темы разговора
        self.topic_patterns = {
            'personal_life': ['семья', 'отношения', 'любовь', 'дружба', 'личное'],
            'work_career': ['работа', 'карьера', 'профессия', 'коллеги', 'начальник', 'проект'],
            'hobbies': ['хобби', 'увлечение', 'спорт', 'музыка', 'игры', 'чтение', 'фильмы'],
            'health': ['здоровье', 'болею', 'врач', 'лечение', 'самочувствие', 'боль'],
            'dreams_goals': ['мечты', 'цели', 'планы', 'хочу', 'надеюсь', 'стремлюсь'],
            'problems': ['проблема', 'трудности', 'сложности', 'не получается', 'помощь'],
            'philosophical': ['смысл', 'жизнь', 'душа', 'мысли', 'размышления', 'философия']
        }
        
        # Паттерны коммуникации
        self.communication_patterns = {
            'question_heavy': r'\?.*\?|\? .+\?',  # Много вопросов
            'exclamation_heavy': r'!.*!|! .+!',  # Много восклицаний
            'long_sentences': r'.{100,}',  # Длинные предложения
            'short_bursts': r'^.{1,20}$',  # Короткие сообщения
            'storytelling': r'(сначала|потом|затем|в итоге|история)',  # Рассказывание историй
            'seeking_advice': r'(что делать|как быть|посоветуй|помоги)',  # Просьба совета
            'sharing_emotions': r'(чувствую|ощущаю|переживаю|настроение)'  # Делится эмоциями
        }
    
    def analyze_user_behavior(self, messages: List[Dict], user_profile: Dict = None,
                                  conversation_context: Dict = None) -> Dict[str, Any]:
        """
        Полный анализ поведения пользователя
        
        Returns:
            {
                'dominant_emotion': str,
                'emotional_intensity': float,
                'primary_topics': List[str],
                'communication_style': str,
                'relationship_needs': List[str],
                'recommended_strategy': str,
                'strategy_confidence': float,
                'behavioral_adjustments': Dict[str, Any]
            }
        """
        if not messages:
            return self._get_default_analysis()
        
        # Фильтруем только сообщения пользователя
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        
        if not user_messages:
            return self._get_default_analysis()
        
        # Анализируем последние сообщения (более свежие важнее)
        recent_messages = user_messages[-5:]  # Последние 5 сообщений
        all_content = ' '.join([msg.get('content', '') for msg in recent_messages])
        
        # 1. Анализ эмоций
        emotion_analysis = self._analyze_emotions(all_content, recent_messages)
        
        # 2. Анализ тем
        topic_analysis = self._analyze_topics(all_content)
        
        # 3. Анализ стиля коммуникации  
        communication_analysis = self._analyze_communication_style(recent_messages)
        
        # 4. Анализ потребностей в отношениях
        relationship_analysis = self._analyze_relationship_needs(
            all_content, user_profile, conversation_context
        )
        
        # 5. Выбор стратегии на основе всех анализов
        strategy_choice = self._choose_strategy(
            emotion_analysis, topic_analysis, communication_analysis,
            relationship_analysis, user_profile, conversation_context
        )
        
        return {
            'dominant_emotion': emotion_analysis['dominant_emotion'],
            'emotional_intensity': emotion_analysis['intensity'],
            'emotional_stability': emotion_analysis['stability'],
            'primary_topics': topic_analysis['primary_topics'],
            'topic_focus': topic_analysis['focus_level'],
            'communication_style': communication_analysis['style'],
            'engagement_level': communication_analysis['engagement'],
            'relationship_needs': relationship_analysis['needs'],
            'intimacy_preference': relationship_analysis['intimacy_level'],
            'recommended_strategy': strategy_choice['strategy'],
            'strategy_confidence': strategy_choice['confidence'],
            'behavioral_adjustments': strategy_choice['adjustments'],
            'context_factors': strategy_choice['context_factors']
        }
    
    def _analyze_emotions(self, content: str, messages: List[Dict]) -> Dict[str, Any]:
        """Анализ эмоционального состояния"""
        content_lower = content.lower()
        emotion_scores = {}
        
        # Подсчет эмоциональных маркеров
        for emotion, patterns in self.emotion_patterns.items():
            score = 0
            
            # Ключевые слова
            for keyword in patterns['keywords']:
                score += content_lower.count(keyword) * 2
            
            # Эмодзи
            for emoji in patterns['emojis']:
                score += content.count(emoji) * 3
            
            # Пунктуация
            for punct in patterns['punctuation']:
                score += content.count(punct) * 1
            
            emotion_scores[emotion] = score
        
        # Определяем доминирующую эмоцию
        if not any(emotion_scores.values()):
            dominant_emotion = 'neutral'
            intensity = 0.3
        else:
            dominant_emotion = max(emotion_scores, key=emotion_scores.get)
            max_score = emotion_scores[dominant_emotion]
            intensity = min(max_score / 10.0, 1.0)  # Нормализуем к 0-1
        
        # Анализ эмоциональной стабильности (изменения эмоций между сообщениями)
        stability = self._calculate_emotional_stability(messages)
        
        return {
            'dominant_emotion': dominant_emotion,
            'intensity': intensity,
            'stability': stability,
            'emotion_scores': emotion_scores
        }
    
    def _analyze_topics(self, content: str) -> Dict[str, Any]:
        """Анализ тем разговора"""
        content_lower = content.lower()
        topic_scores = {}
        
        for topic, keywords in self.topic_patterns.items():
            score = sum(content_lower.count(keyword) for keyword in keywords)
            if score > 0:
                topic_scores[topic] = score
        
        # Сортируем темы по важности
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        primary_topics = [topic for topic, score in sorted_topics[:3]]
        
        # Определяем уровень фокуса на темах
        total_score = sum(topic_scores.values())
        focus_level = 'focused' if len(primary_topics) <= 2 and total_score > 3 else 'diverse'
        
        return {
            'primary_topics': primary_topics,
            'topic_scores': topic_scores,
            'focus_level': focus_level
        }
    
    def _analyze_communication_style(self, messages: List[Dict]) -> Dict[str, Any]:
        """Анализ стиля коммуникации"""
        if not messages:
            return {'style': 'balanced', 'engagement': 'moderate'}
        
        all_content = ' '.join([msg.get('content', '') for msg in messages])
        
        # Анализ паттернов
        pattern_matches = {}
        for pattern_name, pattern in self.communication_patterns.items():
            matches = len(re.findall(pattern, all_content, re.IGNORECASE))
            pattern_matches[pattern_name] = matches
        
        # Анализ длины сообщений
        message_lengths = [len(msg.get('content', '')) for msg in messages]
        avg_length = sum(message_lengths) / len(message_lengths)
        
        # Анализ частоты сообщений (engagement)
        engagement_level = 'high' if len(messages) > 3 else 'moderate' if len(messages) > 1 else 'low'
        
        # Определение стиля
        style = 'balanced'
        if pattern_matches.get('question_heavy', 0) > 2:
            style = 'inquisitive'
        elif pattern_matches.get('storytelling', 0) > 0 and avg_length > 100:
            style = 'narrative'
        elif pattern_matches.get('sharing_emotions', 0) > 1:
            style = 'emotional'
        elif pattern_matches.get('seeking_advice', 0) > 0:
            style = 'advice_seeking'
        elif avg_length < 30:
            style = 'concise'
        elif pattern_matches.get('exclamation_heavy', 0) > 2:
            style = 'expressive'
        
        return {
            'style': style,
            'engagement': engagement_level,
            'average_length': avg_length,
            'pattern_matches': pattern_matches
        }
    
    def _analyze_relationship_needs(self, content: str, user_profile: Dict = None,
                                         conversation_context: Dict = None) -> Dict[str, Any]:
        """Анализ потребностей в отношениях"""
        content_lower = content.lower()
        
        # Индикаторы потребностей
        need_indicators = {
            'emotional_support': ['поддержи', 'помоги', 'трудно', 'сложно', 'грустно', 'одиноко'],
            'intellectual_stimulation': ['интересно', 'думаю', 'мнение', 'философия', 'смысл'],
            'playful_interaction': ['весело', 'смешно', 'шутка', 'игра', 'развлечение'],
            'deep_connection': ['близость', 'доверие', 'секрет', 'личное', 'сокровенное'],
            'guidance': ['совет', 'что делать', 'как быть', 'направление', 'решение'],
            'validation': ['правильно', 'нормально', 'понимаешь', 'согласна', 'поддерживаешь']
        }
        
        need_scores = {}
        for need, indicators in need_indicators.items():
            score = sum(content_lower.count(indicator) for indicator in indicators)
            need_scores[need] = score
        
        # Определяем основные потребности
        primary_needs = [need for need, score in need_scores.items() if score > 0]
        
        # Определяем предпочтительный уровень интимности
        intimacy_indicators = {
            'high': ['секрет', 'личное', 'сокровенное', 'доверие', 'близко'],
            'medium': ['друг', 'понимание', 'поддержка', 'общение'],
            'low': ['помощь', 'совет', 'информация', 'вопрос']
        }
        
        intimacy_level = 'medium'  # по умолчанию
        for level, indicators in intimacy_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                intimacy_level = level
                break
        
        # Учитываем контекст отношений
        if conversation_context:
            relationship_stage = conversation_context.get('relationship_stage', 'introduction')
            if relationship_stage in ['close_friend', 'confidant']:
                intimacy_level = 'high'
            elif relationship_stage in ['introduction', 'getting_acquainted']:
                intimacy_level = 'low'
        
        return {
            'needs': primary_needs[:3],  # Топ-3 потребности
            'need_scores': need_scores,
            'intimacy_level': intimacy_level
        }
    
    def _choose_strategy(self, emotion_analysis: Dict, topic_analysis: Dict,
                               communication_analysis: Dict, relationship_analysis: Dict,
                               user_profile: Dict = None, conversation_context: Dict = None) -> Dict[str, Any]:
        """Выбор оптимальной поведенческой стратегии"""
        
        # Доступные стратегии с весами
        strategy_scores = {
            'caring': 0.0,
            'playful': 0.0,
            'mysterious': 0.0,
            'reserved': 0.0,
            'intellectual': 0.0,
            'supportive': 0.0
        }
        
        dominant_emotion = emotion_analysis['dominant_emotion']
        emotional_intensity = emotion_analysis['intensity']
        primary_needs = relationship_analysis['needs']
        communication_style = communication_analysis['style']
        
        # Эмоционально-ориентированный выбор
        if dominant_emotion in ['negative', 'anxious', 'tired']:
            strategy_scores['caring'] += 3.0
            strategy_scores['supportive'] += 2.5
            if emotional_intensity > 0.6:
                strategy_scores['caring'] += 1.0
        
        elif dominant_emotion in ['positive', 'excited']:
            strategy_scores['playful'] += 2.5
            strategy_scores['caring'] += 1.5
            if emotional_intensity > 0.6:
                strategy_scores['playful'] += 1.0
        
        elif dominant_emotion == 'confused' or communication_style == 'advice_seeking':
            strategy_scores['supportive'] += 3.5
            strategy_scores['intellectual'] += 1.5
            strategy_scores['caring'] += 1.0
        
        elif dominant_emotion == 'angry':
            strategy_scores['reserved'] += 2.0
            strategy_scores['supportive'] += 1.5
        
        else:  # neutral
            strategy_scores['mysterious'] += 1.5
            strategy_scores['playful'] += 1.0
            strategy_scores['caring'] += 1.0
        
        # Потребности-ориентированный выбор
        for need in primary_needs:
            if need == 'emotional_support':
                strategy_scores['caring'] += 2.0
                strategy_scores['supportive'] += 1.5
            elif need == 'intellectual_stimulation':
                strategy_scores['intellectual'] += 2.5
                strategy_scores['mysterious'] += 1.5
            elif need == 'playful_interaction':
                strategy_scores['playful'] += 2.5
            elif need == 'deep_connection':
                strategy_scores['caring'] += 1.5
                strategy_scores['mysterious'] += 1.0
            elif need == 'guidance':
                strategy_scores['supportive'] += 2.0
                strategy_scores['intellectual'] += 1.0
            elif need == 'validation':
                strategy_scores['caring'] += 1.5
                strategy_scores['supportive'] += 1.0
        
        # Стиль коммуникации
        if communication_style == 'emotional':
            strategy_scores['caring'] += 1.5
            strategy_scores['supportive'] += 1.0
        elif communication_style == 'inquisitive':
            strategy_scores['intellectual'] += 1.5
            strategy_scores['mysterious'] += 1.0
        elif communication_style == 'narrative':
            strategy_scores['caring'] += 1.0
            strategy_scores['intellectual'] += 1.0
        elif communication_style == 'expressive':
            strategy_scores['playful'] += 1.5
        elif communication_style == 'advice_seeking':
            strategy_scores['supportive'] += 3.0
            strategy_scores['intellectual'] += 1.5
        elif communication_style == 'concise':
            strategy_scores['reserved'] += 1.0
        
        # Контекст отношений
        if conversation_context:
            relationship_stage = conversation_context.get('relationship_stage', 'introduction')
            personalization_level = conversation_context.get('personalization_level', 0.0)
            
            if relationship_stage == 'introduction':
                strategy_scores['mysterious'] += 1.0
                strategy_scores['playful'] += 0.5
            elif relationship_stage in ['building_trust', 'close_friend']:
                strategy_scores['caring'] += 1.5
                strategy_scores['supportive'] += 1.0
            elif relationship_stage == 'confidant':
                strategy_scores['caring'] += 2.0
                strategy_scores['intellectual'] += 1.0
            
            # Высокий уровень персонализации
            if personalization_level > 0.7:
                strategy_scores['caring'] += 1.0
        
        # Выбираем лучшую стратегию
        best_strategy = max(strategy_scores, key=strategy_scores.get)
        confidence = strategy_scores[best_strategy] / max(sum(strategy_scores.values()), 1.0)
        
        # Создаем поведенческие корректировки
        adjustments = self._create_behavioral_adjustments(
            best_strategy, emotion_analysis, relationship_analysis, communication_analysis
        )
        
        # Контекстные факторы
        context_factors = {
            'emotional_state': dominant_emotion,
            'relationship_stage': conversation_context.get('relationship_stage', 'introduction') if conversation_context else 'introduction',
            'primary_need': primary_needs[0] if primary_needs else 'general_interaction',
            'communication_preference': communication_style
        }
        
        return {
            'strategy': best_strategy,
            'confidence': min(confidence, 1.0),
            'adjustments': adjustments,
            'context_factors': context_factors,
            'alternative_strategies': sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)[1:3]
        }
    
    def _create_behavioral_adjustments(self, strategy: str, emotion_analysis: Dict,
                                             relationship_analysis: Dict, communication_analysis: Dict) -> Dict[str, Any]:
        """Создание конкретных поведенческих корректировок для стратегии"""
        
        adjustments = {
            'tone_modifiers': [],
            'response_style': 'normal',
            'empathy_level': 'medium',
            'question_tendency': 'moderate',
            'emotional_mirroring': False,
            'personal_disclosure': 'minimal',
            'humor_usage': 'occasional',
            'support_intensity': 'medium'
        }
        
        emotional_intensity = emotion_analysis['intensity']
        dominant_emotion = emotion_analysis['dominant_emotion']
        intimacy_level = relationship_analysis['intimacy_level']
        
        # Базовые настройки для стратегии
        strategy_base_settings = {
            'caring': {
                'empathy_level': 'high',
                'support_intensity': 'high',
                'personal_disclosure': 'moderate',
                'tone_modifiers': ['warm', 'gentle', 'nurturing']
            },
            'playful': {
                'humor_usage': 'frequent',
                'tone_modifiers': ['light', 'energetic', 'fun'],
                'question_tendency': 'high',
                'response_style': 'casual'
            },
            'mysterious': {
                'personal_disclosure': 'minimal',
                'tone_modifiers': ['intriguing', 'thoughtful'],
                'question_tendency': 'strategic',
                'response_style': 'subtle'
            },
            'reserved': {
                'empathy_level': 'measured',
                'personal_disclosure': 'minimal',
                'tone_modifiers': ['calm', 'measured'],
                'support_intensity': 'gentle'
            },
            'intellectual': {
                'question_tendency': 'analytical',
                'tone_modifiers': ['thoughtful', 'curious'],
                'personal_disclosure': 'intellectual',
                'response_style': 'analytical'
            },
            'supportive': {
                'empathy_level': 'high',
                'support_intensity': 'high',
                'tone_modifiers': ['encouraging', 'understanding'],
                'question_tendency': 'caring'
            }
        }
        
        # Применяем базовые настройки
        if strategy in strategy_base_settings:
            adjustments.update(strategy_base_settings[strategy])
        
        # Корректировки на основе эмоций
        if dominant_emotion in ['negative', 'anxious'] and emotional_intensity > 0.6:
            adjustments['empathy_level'] = 'very_high'
            adjustments['support_intensity'] = 'high'
            adjustments['emotional_mirroring'] = True
            adjustments['humor_usage'] = 'minimal'
        
        elif dominant_emotion == 'excited' and emotional_intensity > 0.7:
            adjustments['emotional_mirroring'] = True
            adjustments['tone_modifiers'].append('enthusiastic')
        
        # Корректировки на основе уровня близости
        if intimacy_level == 'high':
            adjustments['personal_disclosure'] = 'high'
            adjustments['empathy_level'] = 'very_high'
        elif intimacy_level == 'low':
            adjustments['personal_disclosure'] = 'minimal'
            adjustments['empathy_level'] = 'measured'
        
        # Корректировки на основе стиля коммуникации
        comm_style = communication_analysis['style']
        if comm_style == 'concise':
            adjustments['response_style'] = 'concise'
        elif comm_style == 'narrative':
            adjustments['response_style'] = 'detailed'
        elif comm_style == 'inquisitive':
            adjustments['question_tendency'] = 'responsive'
        
        return adjustments
    
    def _calculate_emotional_stability(self, messages: List[Dict]) -> float:
        """Вычисляет эмоциональную стабильность пользователя"""
        if len(messages) < 2:
            return 0.8  # Нейтральная стабильность
        
        emotions = []
        for msg in messages[-5:]:  # Последние 5 сообщений
            content = msg.get('content', '').lower()
            msg_emotion = 'neutral'
            
            for emotion, patterns in self.emotion_patterns.items():
                score = 0
                for keyword in patterns['keywords']:
                    score += content.count(keyword)
                if score > 0:
                    msg_emotion = emotion
                    break
            
            emotions.append(msg_emotion)
        
        # Подсчитываем изменения эмоций
        emotion_changes = sum(1 for i in range(1, len(emotions)) 
                            if emotions[i] != emotions[i-1])
        
        # Стабильность = 1 - (количество изменений / максимальные изменения)
        max_changes = len(emotions) - 1
        stability = 1.0 - (emotion_changes / max_changes) if max_changes > 0 else 1.0
        
        return max(0.0, min(1.0, stability))
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Возвращает анализ по умолчанию для новых пользователей"""
        return {
            'dominant_emotion': 'neutral',
            'emotional_intensity': 0.3,
            'emotional_stability': 0.8,
            'primary_topics': ['general'],
            'topic_focus': 'diverse',
            'communication_style': 'balanced',
            'engagement_level': 'moderate',
            'relationship_needs': ['general_interaction'],
            'intimacy_preference': 'medium',
            'recommended_strategy': 'mysterious',  # Безопасная стратегия для знакомства
            'strategy_confidence': 0.6,
            'behavioral_adjustments': {
                'tone_modifiers': ['friendly', 'curious'],
                'response_style': 'normal',
                'empathy_level': 'medium',
                'question_tendency': 'moderate',
                'emotional_mirroring': False,
                'personal_disclosure': 'minimal',
                'humor_usage': 'occasional',
                'support_intensity': 'medium'
            },
            'context_factors': {
                'emotional_state': 'neutral',
                'relationship_stage': 'introduction',
                'primary_need': 'general_interaction',
                'communication_preference': 'balanced'
            }
        } 