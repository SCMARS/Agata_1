"""
Модуль короткой памяти (short_memory) для LangGraph
Совместим с EnhancedBufferMemory и архитектурой без хардкода
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .enhanced_buffer_memory import EnhancedBufferMemory, EmotionTag, BehaviorTag
from .base import Message, MemoryContext, MessageRole


class ShortMemory:
    
    def __init__(self, user_id: str, max_messages: int = None):
        """
        Инициализация короткой памяти
        
        Args:
            user_id: Идентификатор пользователя
            max_messages: Максимальное количество сообщений в буфере
        """
        self.user_id = user_id
        self.logger = logging.getLogger(f"{__name__}.{user_id}")
        
        # Используем EnhancedBufferMemory как основу
        self.enhanced_memory = EnhancedBufferMemory(user_id, max_messages)
        self.context = MemoryContext(user_id)
        
        self.logger.info(f"ShortMemory initialized for user {user_id}")
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> None:
        """
        Добавляет сообщение в короткую память
        
        Args:
            role: Роль отправителя (user/assistant/system)
            content: Содержимое сообщения
            metadata: Дополнительные метаданные
        """
        try:
            # Создаем Message объект
            message = Message(
                role=role,
                content=content,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )
            
            # Добавляем через EnhancedBufferMemory
            self.enhanced_memory.add_message(message, self.context)
            
            self.logger.debug(f"Message added to short memory: {role}[{len(content)}]")
            
        except Exception as e:
            self.logger.error(f"Failed to add message to short memory: {e}")
            raise
    
    def get_context(self) -> List[Dict[str, Any]]:
        """
        Получает контекст для LLM в формате списка сообщений
        
        Returns:
            Список сообщений с полной информацией
        """
        try:
            # Получаем контекст в формате ТЗ
            conv_context = self.enhanced_memory.get_conversation_context_tz()
            
            # Возвращаем буфер сообщений
            return conv_context.get('buffer', [])
            
        except Exception as e:
            self.logger.error(f"Failed to get context from short memory: {e}")
            return []
    
    def get_context_string(self) -> str:
        """
        Получает контекст в виде форматированной строки для промпта
        
        Returns:
            Строка с историей диалога
        """
        try:
            messages = self.get_context()
            
            if not messages:
                return "История диалога пуста."
            
            # Форматируем историю
            context_lines = []
            
            for msg in messages:
                role = msg.get('role', 'unknown')
                text = msg.get('text', '')
                cursor_mark = '>> ' if msg.get('cursor_active') else '   '
                
                # Добавляем эмоции и важность если есть
                emotion = msg.get('emotion_tag')
                importance = msg.get('importance_score', 0)
                
                emotion_str = f" [{emotion}]" if emotion and emotion != 'нет' else ""
                importance_str = f" (важность: {importance:.1f})" if importance > 0.7 else ""
                
                line = f"{cursor_mark}[{role.upper()}]: {text}{emotion_str}{importance_str}"
                context_lines.append(line)
            
            return "\n".join(context_lines)
            
        except Exception as e:
            self.logger.error(f"Failed to get context string: {e}")
            return "Ошибка получения контекста."
    
    def get_current_cursor_position(self) -> int:
        """
        Получает текущую позицию курсора
        
        Returns:
            Позиция курсора в диалоге
        """
        return self.enhanced_memory.cursor_position
    
    def get_summary_memory(self) -> List[Dict[str, Any]]:
        """
        Получает суммарную память
        
        Returns:
            Список записей суммарной памяти
        """
        try:
            conv_context = self.enhanced_memory.get_conversation_context_tz()
            return conv_context.get('summary_memory', [])
        except Exception as e:
            self.logger.error(f"Failed to get summary memory: {e}")
            return []
    
    def get_emotions_detected(self) -> List[str]:
        """
        Получает список обнаруженных эмоций в текущем буфере
        
        Returns:
            Список названий эмоций
        """
        try:
            emotions = set()
            messages = self.get_context()
            
            for msg in messages:
                emotion = msg.get('emotion_tag')
                if emotion and emotion != 'нет':
                    emotions.add(emotion)
            
            return list(emotions)
            
        except Exception as e:
            self.logger.error(f"Failed to get emotions: {e}")
            return []
    
    def get_topics_detected(self) -> List[str]:
        """
        Получает список обнаруженных тем в текущем буфере
        
        Returns:
            Список названий тем
        """
        try:
            topics = set()
            messages = self.get_context()
            
            for msg in messages:
                msg_topics = msg.get('topics', [])
                topics.update(msg_topics)
            
            return list(topics)
            
        except Exception as e:
            self.logger.error(f"Failed to get topics: {e}")
            return []
    
    def clear(self) -> None:
        """Очищает короткую память"""
        try:
            self.enhanced_memory.clear_memory()
            self.logger.info(f"Short memory cleared for user {self.user_id}")
        except Exception as e:
            self.logger.error(f"Failed to clear short memory: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получает статистику короткой памяти
        
        Returns:
            Словарь со статистикой
        """
        try:
            metrics = self.enhanced_memory.get_metrics()
            
            return {
                'buffer_size': metrics.get('current_buffer_size', 0),
                'total_messages': self.enhanced_memory.total_messages,
                'emotions_detected': metrics.get('emotions_detected', 0),
                'avg_importance': metrics.get('avg_importance', 0),
                'dominant_emotion': metrics.get('dominant_emotion'),
                'cursor_position': self.get_current_cursor_position(),
                'summary_entries': metrics.get('summary_entries', 0),
                'detected_emotions': self.get_emotions_detected(),
                'detected_topics': self.get_topics_detected()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {}


# Для обратной совместимости с LangGraph
class LangGraphShortMemory(ShortMemory):
    """
    Специализированная версия для LangGraph узлов
    Предоставляет методы, ожидаемые LangGraph
    """
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Метод для использования в LangGraph узлах
        
        Args:
            state: Состояние LangGraph
            
        Returns:
            Обновленное состояние с контекстом памяти
        """
        try:
            # Добавляем новое сообщение если есть
            if 'new_message' in state:
                msg = state['new_message']
                self.add_message(
                    role=msg.get('role', 'user'),
                    content=msg.get('content', ''),
                    metadata=msg.get('metadata', {})
                )
            
            # Возвращаем обновленное состояние
            return {
                **state,
                'memory_context': self.get_context(),
                'memory_string': self.get_context_string(),
                'cursor_position': self.get_current_cursor_position(),
                'memory_stats': self.get_stats()
            }
            
        except Exception as e:
            self.logger.error(f"LangGraph memory processing failed: {e}")
            return {
                **state,
                'memory_error': str(e)
            }


# Функция-фабрика для создания короткой памяти
def create_short_memory(user_id: str, max_messages: int = None, 
                       for_langgraph: bool = False) -> ShortMemory:
    """
    Создает экземпляр короткой памяти
    
    Args:
        user_id: Идентификатор пользователя
        max_messages: Максимальное количество сообщений
        for_langgraph: Если True, возвращает LangGraphShortMemory
        
    Returns:
        Экземпляр короткой памяти
    """
    if for_langgraph:
        return LangGraphShortMemory(user_id, max_messages)
    return ShortMemory(user_id, max_messages)
