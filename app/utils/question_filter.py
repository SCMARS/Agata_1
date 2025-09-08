"""
Модуль для принудительной фильтрации вопросов из ответов LLM
когда система определила, что вопросы должны быть запрещены.
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

class QuestionFilter:
    """
    Фильтр для принудительного удаления вопросов из ответов LLM
    """
    
    def __init__(self):
        # Паттерны для обнаружения вопросов
        self.question_patterns = [
            r'\?+\s*$',  # Вопросительные знаки в конце
            r'\?\s*[😊😄😃🤔💭❓]?\s*$',  # Вопросы с эмодзи в конце
            r'как дела\?',  # Конкретные вопросы
            r'что делаешь\?',
            r'как жизнь\?',
            r'чем занимаешься\?',
            r'как настроение\?',
            r'что нового\?',
            r'как прошел день\?',
            r'что планируешь\?',
        ]
        
        # Вопросительные слова в начале предложений
        self.question_words = [
            r'^как\s+',
            r'^что\s+',
            r'^где\s+',
            r'^когда\s+',
            r'^почему\s+',
            r'^зачем\s+',
            r'^куда\s+',
            r'^откуда\s+',
            r'^кто\s+',
            r'^какой\s+',
            r'^какая\s+',
            r'^какое\s+',
            r'^какие\s+',
            r'^сколько\s+',
        ]
        
        # Замены для превращения вопросов в утверждения
        self.question_replacements = {
            r'как дела\?': 'надеюсь, у тебя все хорошо.',
            r'что делаешь\?': 'интересно, чем ты занимаешься.',
            r'как жизнь\?': 'надеюсь, жизнь идет хорошо.',
            r'чем занимаешься\?': 'интересно узнать о твоих делах.',
            r'как настроение\?': 'надеюсь, настроение отличное.',
            r'что нового\?': 'интересно, есть ли новости.',
            r'как прошел день\?': 'надеюсь, день прошел хорошо.',
            r'что планируешь\?': 'интересно узнать о твоих планах.',
        }
    
    def filter_questions(self, text: str, may_ask_question: bool) -> Tuple[str, bool]:
        """
        Фильтрует вопросы из текста если они запрещены
        
        Args:
            text: исходный текст ответа
            may_ask_question: разрешено ли задавать вопросы
            
        Returns:
            Tuple[filtered_text, has_question_after_filter]
        """
        if may_ask_question:
            # Вопросы разрешены - не фильтруем
            has_question = self._has_question(text)
            logger.info(f"🔍 [FILTER] Вопросы разрешены, не фильтруем. has_question={has_question}")
            return text, has_question
        
        logger.info(f"🚫 [FILTER] ВОПРОСЫ ЗАПРЕЩЕНЫ - применяем фильтр к тексту: '{text}'")
        
        original_text = text
        filtered_text = self._remove_questions(text)
        
        has_question_before = self._has_question(original_text)
        has_question_after = self._has_question(filtered_text)
        
        if has_question_before and not has_question_after:
            logger.info(f"✅ [FILTER] УСПЕШНО удалили вопросы: '{original_text}' -> '{filtered_text}'")
        elif has_question_before and has_question_after:
            logger.warning(f"⚠️ [FILTER] НЕ УДАЛОСЬ полностью удалить вопросы: '{filtered_text}'")
        else:
            logger.info(f"ℹ️ [FILTER] Вопросов не было, текст не изменен")
        
        return filtered_text, has_question_after
    
    def _has_question(self, text: str) -> bool:
        """Проверяет, содержит ли текст вопросы"""
        text_lower = text.lower()
        
        # Проверяем вопросительные знаки
        if '?' in text:
            return True
        
        # Проверяем вопросительные слова в начале предложений
        sentences = re.split(r'[.!]\s*', text_lower)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            for pattern in self.question_words:
                if re.search(pattern, sentence, re.IGNORECASE):
                    return True
        
        return False
    
    def _remove_questions(self, text: str) -> str:
        """Удаляет вопросы из текста"""
        result = text
        
        # 1. Применяем конкретные замены
        for pattern, replacement in self.question_replacements.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # 2. Удаляем вопросительные знаки в конце
        for pattern in self.question_patterns:
            result = re.sub(pattern, '.', result, flags=re.IGNORECASE)
        
        # 3. Обрабатываем предложения с вопросительными словами
        result = self._convert_question_sentences(result)
        
        # 4. Финальная очистка - удаляем оставшиеся вопросительные знаки
        result = result.replace('?', '.')
        
        # 5. Убираем двойные точки
        result = re.sub(r'\.+', '.', result)
        
        # 6. Убираем лишние пробелы
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result
    
    def _convert_question_sentences(self, text: str) -> str:
        """Преобразует вопросительные предложения в утвердительные"""
        sentences = re.split(r'([.!?]\s*)', text)
        result_parts = []
        
        i = 0
        while i < len(sentences):
            sentence = sentences[i].strip()
            
            if not sentence:
                if i + 1 < len(sentences):
                    result_parts.append(sentences[i + 1])  # Добавляем разделитель
                    i += 2
                else:
                    i += 1
                continue
            
            # Проверяем, является ли это вопросительным предложением
            converted = self._convert_single_question(sentence)
            result_parts.append(converted)
            
            # Добавляем разделитель, если он есть
            if i + 1 < len(sentences):
                separator = sentences[i + 1]
                if '?' in separator:
                    separator = separator.replace('?', '.')
                result_parts.append(separator)
                i += 2
            else:
                i += 1
        
        return ''.join(result_parts)
    
    def _convert_single_question(self, sentence: str) -> str:
        """Преобразует одно вопросительное предложение в утвердительное"""
        sentence_lower = sentence.lower().strip()
        
        # Простые преобразования
        conversions = {
            r'^как дела': 'надеюсь, дела идут хорошо',
            r'^что делаешь': 'интересно, чем занимаешься',
            r'^как жизнь': 'надеюсь, жизнь хороша',
            r'^чем занимаешься': 'интересно узнать о твоих занятиях',
            r'^как настроение': 'надеюсь, настроение отличное',
            r'^что нового': 'интересно, есть ли новости',
            r'^как прошел день': 'надеюсь, день прошел хорошо',
            r'^что планируешь': 'интересно узнать о планах',
        }
        
        for pattern, replacement in conversions.items():
            if re.match(pattern, sentence_lower):
                return replacement
        
        # Если не нашли конкретное преобразование, просто убираем вопросительные слова
        result = sentence
        for pattern in self.question_words:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        result = result.strip()
        if result and not result.endswith('.'):
            result += '.'
        
        return result if result else 'Хорошо.'


# Глобальный экземпляр фильтра
question_filter = QuestionFilter()
