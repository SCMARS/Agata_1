from typing import List, Dict, Any
from datetime import datetime, timedelta
import json

from .base import MemoryAdapter, Message, MemoryContext
from ..config.settings import settings

class BufferMemory(MemoryAdapter):
    """Simple buffer memory that keeps recent messages in memory"""
    
    def __init__(self, user_id: str, max_messages: int = 20):
        super().__init__(user_id)
        self.max_messages = max_messages
        self.messages: List[Message] = []
        self.last_activity: datetime = datetime.utcnow()
    
    def add_message(self, message: Message, context: MemoryContext) -> None:
        """Add message to buffer"""
        self.messages.append(message)
        self.last_activity = datetime.utcnow()
        
        # Keep only recent messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_context(self, context: MemoryContext) -> str:
        """Get formatted context from recent messages with key information extraction"""
        if not self.messages:
            return "Это начало вашего разговора."
        
        # Format recent messages
        context_parts = []
        
        # Add time context
        time_gap = datetime.utcnow() - self.last_activity
        if time_gap > timedelta(hours=6):
            context_parts.append(f"Прошло {self._format_time_gap(time_gap)} с последнего сообщения.")
        
        # Extract key information from user messages
        key_info = self._extract_key_information()
        if key_info:
            context_parts.append(f"Ключевая информация: {key_info}")
            print(f"🧠 BufferMemory: Извлечена ключевая информация: {key_info}")
        else:
            print(f"🧠 BufferMemory: Ключевая информация не найдена")
        
        # Add recent conversation summary
        context_parts.append("Недавний разговор:")
        for msg in self.messages[-5:]:  # Last 5 messages
            role = "Пользователь" if msg.role == "user" else "Ты"
            context_parts.append(f"{role}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def _extract_key_information(self) -> str:
        """Extract key information from user messages"""
        user_messages = [msg for msg in self.messages if msg.role == "user"]
        if not user_messages:
            return ""
        
        # Combine all user messages
        all_text = " ".join([msg.content for msg in user_messages])
        text_lower = all_text.lower()
        
        key_info = []
        

        words = all_text.split()
        for i, word in enumerate(words):
            if word.lower() in ["я", "меня", "мне"] and i + 1 < len(words):
                next_word = words[i + 1].replace(',', '').replace('.', '').replace('!', '')
                if len(next_word) > 2 and next_word[0].isupper() and next_word.isalpha():
                    key_info.append(f"Имя: {next_word}")
                    break
        
        # ИСПРАВЛЕНО: Убираем хардкод возрастных паттернов
        # Ищем числа с помощью regex
        import re
        age_match = re.search(r'\b(\d{1,3})\s*(?:лет|года|год)\b', text_lower)
        if age_match:
            age = int(age_match.group(1))
            if 1 <= age <= 120:
                key_info.append(f"Возраст: {age} лет")
        

        
        # ИСПРАВЛЕНО: Убираем все хардкод списки
        # Векторная база данных сама найдет семантически похожие факты о хобби, профессии, городах
        
        return "; ".join(key_info) if key_info else ""
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Simple text search in buffer (not semantic)"""
        results = []
        query_lower = query.lower()
        
        for msg in reversed(self.messages):
            if query_lower in msg.content.lower():
                results.append({
                    "content": msg.content,
                    "role": msg.role,
                    "timestamp": msg.timestamp,
                    "relevance": 1.0
                })
                if len(results) >= limit:
                    break
        
        return results
    
    def summarize_conversation(self, messages: List[Message]) -> str:
        """Simple summarization"""
        if not messages:
            return "Нет сообщений для обобщения."
        
        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]
        
        summary = f"Разговор из {len(messages)} сообщений. "
        summary += f"Пользователь написал {len(user_messages)} сообщений, "
        summary += f"ассистент ответил {len(assistant_messages)} раз."
        
        if user_messages:
            # Extract key topics (simple keyword approach)
            all_text = " ".join([m.content for m in user_messages])
            words = all_text.lower().split()
            # This is very simplified - in real implementation use proper NLP
            common_words = [w for w in words if len(w) > 4]
            if common_words:
                summary += f" Основные темы: {', '.join(common_words[:3])}."
        
        return summary
    
    def clear_memory(self) -> None:
        """Clear buffer memory"""
        self.messages.clear()
        self.last_activity = datetime.utcnow()
    
    def _format_time_gap(self, gap: timedelta) -> str:
        """Format time gap in Russian"""
        if gap.days > 0:
            return f"{gap.days} дн."
        elif gap.seconds > 3600:
            hours = gap.seconds // 3600
            return f"{hours} ч."
        else:
            minutes = gap.seconds // 60
            return f"{minutes} мин." 