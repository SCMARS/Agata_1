"""
Система разбиения и рандомизации сообщений Агаты
"""
import re
import random
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

class MessageSplitter:
    """Система разбиения сообщений на логические части"""
    
    def __init__(self, max_length: int = 200):
        self.max_length = max_length
        self.min_delay = 800   # мс
        self.max_delay = 2500  # мс
    
    def split_message(self, text: str, force_split: bool = False) -> Dict[str, any]:
        """
        Разбивает сообщение на 1-3 логические части
        
        Args:
            text: Исходный текст сообщения
            force_split: Принудительно разбить на части
            
        Returns:
            Dict с частями сообщения, флагом наличия вопроса и задержками
        """
        # Очищаем текст
        text = text.strip()
        
        if not text:
            return {
                'parts': [''],
                'has_question': False,
                'delays_ms': [0]
            }
        
        # Проверяем наличие вопросов
        has_question = self._has_question(text)
        
        # Если текст короткий и нет принуждения к разбиению
        if len(text) <= self.max_length and not force_split:
            return {
                'parts': [text],
                'has_question': has_question,
                'delays_ms': [self._generate_delay()]
            }
        
        # Разбиваем на части
        parts = self._split_into_parts(text)
        delays = [self._generate_delay() for _ in parts]
        
        logger.info(f"Разбили сообщение на {len(parts)} частей")
        return {
            'parts': parts,
            'has_question': has_question,
            'delays_ms': delays
        }
    
    def _split_into_parts(self, text: str) -> List[str]:
        """Разбивает текст на логические части"""
        
        # Сначала пробуем разбить по естественным границам
        parts = self._split_by_sentences(text)
        
        # Если получилось слишком много частей, объединяем
        if len(parts) > 3:
            parts = self._merge_short_parts(parts, max_parts=3)
        
        # Если части слишком длинные, дополнительно разбиваем
        final_parts = []
        for part in parts:
            if len(part) > self.max_length:
                sub_parts = self._force_split_long_part(part)
                final_parts.extend(sub_parts)
            else:
                final_parts.append(part)
        
        # Ограничиваем до 3 частей максимум
        if len(final_parts) > 3:
            final_parts = final_parts[:3]
        
        return final_parts
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """Разбивает текст по предложениям"""
        
        # Паттерны для разбиения
        sentence_endings = r'[.!?…]\s+'
        logical_breaks = r'\n\n+'
        
        # Сначала разбиваем по абзацам
        paragraphs = re.split(logical_breaks, text)
        
        parts = []
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # Разбиваем абзац по предложениям
            sentences = re.split(sentence_endings, paragraph)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if len(sentences) == 1:
                parts.append(sentences[0])
            else:
                # Группируем предложения
                current_part = []
                current_length = 0
                
                for sentence in sentences:
                    sentence_length = len(sentence)
                    
                    if current_length + sentence_length > self.max_length and current_part:
                        # Завершаем текущую часть
                        parts.append(' '.join(current_part))
                        current_part = [sentence]
                        current_length = sentence_length
                    else:
                        current_part.append(sentence)
                        current_length += sentence_length
                
                if current_part:
                    parts.append(' '.join(current_part))
        
        return parts
    
    def _merge_short_parts(self, parts: List[str], max_parts: int = 3) -> List[str]:
        """Объединяет короткие части до достижения максимального количества"""
        
        if len(parts) <= max_parts:
            return parts
        
        merged = []
        current_group = []
        current_length = 0
        
        for part in parts:
            part_length = len(part)
            
            if (current_length + part_length > self.max_length and current_group) or len(merged) >= max_parts - 1:
                # Завершаем текущую группу
                merged.append(' '.join(current_group))
                current_group = [part]
                current_length = part_length
            else:
                current_group.append(part)
                current_length += part_length
        
        if current_group:
            if merged and len(merged[-1]) + current_length <= self.max_length * 1.5:
                # Объединяем с последней частью если не слишком длинно
                merged[-1] += ' ' + ' '.join(current_group)
            else:
                merged.append(' '.join(current_group))
        
        return merged[:max_parts]
    
    def _force_split_long_part(self, text: str) -> List[str]:
        """Принудительно разбивает слишком длинную часть"""
        
        # Ищем места для разбиения (запятые, союзы)
        break_points = []
        
        # Паттерны для поиска мест разбиения
        patterns = [
            r',\s+',      # запятые
            r'\s+и\s+',   # союз "и"
            r'\s+но\s+',  # союз "но"
            r'\s+а\s+',   # союз "а"
            r'\s+или\s+', # союз "или"
            r':\s+',      # двоеточие
            r';\s+',      # точка с запятой
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                break_points.append(match.end())
        
        if not break_points:
            # Если нет хороших мест для разбиения, разбиваем по словам
            words = text.split()
            mid_point = len(words) // 2
            return [
                ' '.join(words[:mid_point]),
                ' '.join(words[mid_point:])
            ]
        
        # Выбираем лучшую точку разбиения (ближе к середине)
        text_mid = len(text) // 2
        best_point = min(break_points, key=lambda x: abs(x - text_mid))
        
        return [
            text[:best_point].strip(),
            text[best_point:].strip()
        ]
    
    def _has_question(self, text: str) -> bool:
        """Проверяет наличие вопросов в тексте"""
        question_markers = ['?', 'как ', 'что ', 'где ', 'когда ', 'почему ', 'зачем ']
        text_lower = text.lower()
        
        return any(marker in text_lower for marker in question_markers)
    
    def _generate_delay(self) -> int:
        """Генерирует случайную задержку для отправки сообщения"""
        return random.randint(self.min_delay, self.max_delay)

# Глобальный экземпляр разделителя
message_splitter = MessageSplitter()
