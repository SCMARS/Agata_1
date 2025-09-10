"""
Система разбиения и рандомизации сообщений Агаты
"""
import re
import random
import logging
from typing import List, Dict, Tuple
from .living_chat_config_loader import living_chat_config

logger = logging.getLogger(__name__)

class MessageSplitter:
    """Система разбиения сообщений на логические части для живого общения"""
    
    def __init__(self):
        # Загружаем конфигурацию
        self.config = living_chat_config
        self.message_splitting_config = self.config.get_message_splitting_config()
        
        # Настройки из конфигурации
        self.max_length = self.message_splitting_config.get("max_length", 150)
        self.min_delay = self.message_splitting_config.get("min_delay_ms", 500)
        self.max_delay = self.message_splitting_config.get("max_delay_ms", 2000)
        self.force_split_threshold = self.message_splitting_config.get("force_split_threshold", 100)
        self.max_parts = self.message_splitting_config.get("max_parts", 3)
    
    def split_message(self, text: str, force_split: bool = False) -> Dict[str, any]:
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
        if len(text) <= self.max_length and not force_split and len(text) <= self.force_split_threshold:
            return {
                'parts': [text],
                'has_question': has_question,
                'delays_ms': [self._generate_delay()]
            }
        
        # Принудительно разбиваем длинные сообщения для живого общения
        if len(text) > self.force_split_threshold or force_split:
            force_split = True
        
        # Разбиваем на части
        parts = self._split_into_parts(text)
        delays = [self._generate_delay() for _ in parts]
        
        logger.info(f"✂️ [SPLITTER] Разбили сообщение на {len(parts)} частей")
        for i, part in enumerate(parts, 1):
            logger.info(f"   📝 Часть {i}: '{part[:50]}{'...' if len(part) > 50 else ''}'")
        logger.info(f"   ❓ Есть вопрос: {has_question}")
        logger.info(f"   ⏱️ Задержки: {delays}мс")
        
        return {
            'parts': parts,
            'has_question': has_question,
            'delays_ms': delays
        }
    
    def _split_into_parts(self, text: str) -> List[str]:
        """Разбивает текст на логические части для живого общения"""
        
        # Сначала пробуем разбить по естественным границам
        parts = self._split_by_sentences(text)
        
        # Если получилось слишком много частей, объединяем
        if len(parts) > self.max_parts:
            parts = self._merge_short_parts(parts)
        
        # Если части слишком длинные, дополнительно разбиваем
        final_parts = []
        for part in parts:
            if len(part) > self.max_length:
                sub_parts = self._force_split_long_part(part)
                final_parts.extend(sub_parts)
            else:
                final_parts.append(part)
        
        # Ограничиваем до максимального количества частей из конфигурации
        if len(final_parts) > self.max_parts:
            final_parts = final_parts[:self.max_parts]
        
        # Добавляем естественность - делаем части более короткими и живыми
        final_parts = self._make_parts_livelier(final_parts)
        
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
        
        # 🔥 НОВАЯ ЛОГИКА: естественное разделение
        return self._natural_split(parts)
    
    def _natural_split(self, parts: List[str]) -> List[str]:
        if not parts:
            return parts
            
        # Объединяем все части в один текст
        full_text = ' '.join(parts)
        
        # Если короткий текст - НЕ разделяем (увеличен лимит)
        if len(full_text) <= 250:
            return [full_text]
        
        # Ищем естественные места разрыва
        import re
        
        # Более естественные места для разрыва:
        natural_breaks = [
            (r'\.\s+([А-ЯA-Z][а-яa-z]{2,})', 'sentence'),      # После предложения + нормальное слово
            (r'\?\s+([А-ЯA-Z][а-яa-z]{2,})', 'question'),      # После вопроса + нормальное слово  
            (r'!\s+([А-ЯA-Z][а-яa-z]{2,})', 'exclamation'),    # После восклицания + нормальное слово
            (r'\s+(А\s+как|И\s+вот|Но\s+на|Кстати\s+[а-я]|Да\s+[а-я])', 'good_conjunction'),  # Хорошие союзы с контекстом
            (r'\s+(поэтому|потому|кстати|вообще|вот)\s+', 'connectors'),  # Связующие слова
        ]
        
        best_splits = []
        for pattern, break_type in natural_breaks:
            for match in re.finditer(pattern, full_text, re.IGNORECASE):
                if break_type in ['sentence', 'question', 'exclamation']:
                    split_pos = match.start(1)
                else:
                    split_pos = match.start()
                best_splits.append((split_pos, break_type))
        
        if not best_splits:
            return [full_text]
        
        # Находим разрыв ближе к середине, но избегаем слишком коротких частей
        target = len(full_text) // 2
        valid_splits = []
        
        for split_pos, break_type in best_splits:
            part1_len = split_pos
            part2_len = len(full_text) - split_pos
            
            # Минимальные длины увеличены для естественности
            if part1_len >= 120 and part2_len >= 120:
                valid_splits.append((split_pos, break_type))
        
        if not valid_splits:
            return [full_text]
        
        best_split = min(valid_splits, key=lambda x: abs(x[0] - target))
        split_pos = best_split[0]
        
        part1 = full_text[:split_pos].strip()
        part2 = full_text[split_pos:].strip()
            
        return [part1, part2]
    
    def _merge_short_parts(self, parts: List[str], max_parts: int = None) -> List[str]:
        """Объединяет короткие части до достижения максимального количества"""
        
        if max_parts is None:
            max_parts = self.max_parts
            
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
        
        part1 = text[:best_point].strip()
        part2 = text[best_point:].strip()

        if self._is_short_start(part1):
            # Переміщуємо коротке слово до другої частини
            words = text.split()
            if len(words) > 2:
                return [
                    ' '.join(words[:2]),  
                    ' '.join(words[2:])
                ]
        
        return [part1, part2]
    
    def _is_short_start(self, text: str) -> bool:
        """Перевіряє, чи починається текст з короткого слова"""
        short_starts = ['О,', 'Да,', 'Нет,', 'Ой,', 'Ах,', 'Ох,', 'Эх,', 'Ну,', 'И,', 'А,']
        return any(text.strip().startswith(start) for start in short_starts)
    
    def _has_question(self, text: str) -> bool:
        """Проверяет наличие вопросов в тексте"""
        question_markers = ['?', 'как ', 'что ', 'где ', 'когда ', 'почему ', 'зачем ']
        text_lower = text.lower()
        
        return any(marker in text_lower for marker in question_markers)
    
    def _make_parts_livelier(self, parts: List[str]) -> List[str]:
        
        livelier_parts = []
        
        for i, part in enumerate(parts):
            part = part.strip()
            
            # Если часть слишком длинная, разбиваем на более короткие
            if len(part) > self.force_split_threshold:
                # Ищем естественные места для разбиения
                if ', ' in part:
                    sub_parts = part.split(', ', 1)
                    livelier_parts.extend([sub_parts[0] + ',', sub_parts[1]])
                elif ' и ' in part:
                    sub_parts = part.split(' и ', 1)
                    livelier_parts.extend([sub_parts[0], 'И ' + sub_parts[1]])
                elif ' но ' in part:
                    sub_parts = part.split(' но ', 1)
                    livelier_parts.extend([sub_parts[0], 'Но ' + sub_parts[1]])
                else:
                    # Принудительно разбиваем по словам
                    words = part.split()
                    mid = len(words) // 2
                    livelier_parts.extend([
                        ' '.join(words[:mid]),
                        ' '.join(words[mid:])
                    ])
            else:
                livelier_parts.append(part)
        
        # Ограничиваем до максимального количества частей из конфигурации
        return livelier_parts[:self.max_parts]
    
    def _generate_delay(self) -> int:
        """Генерирует случайную задержку для отправки сообщения"""
        return random.randint(self.min_delay, self.max_delay)

# Глобальный экземпляр разделителя
message_splitter = MessageSplitter()
