from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class MessageRole(Enum):
    """Роли сообщений"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message:
    """Message model - простая версия без pydantic"""
    def __init__(self, role: str, content: str, timestamp: datetime, metadata: Dict[str, Any] = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.metadata = metadata or {}

class MemoryContext:
    """Memory context model - простая версия без pydantic"""
    def __init__(self, user_id: str, conversation_id: Optional[str] = None, 
                 day_number: int = 1, session_metadata: Dict[str, Any] = None):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.day_number = day_number
        self.session_metadata = session_metadata or {}

class MemoryAdapter(ABC):
    """Base memory adapter interface"""
    
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    @abstractmethod
    def add_message(self, message: Message, context: MemoryContext) -> None:
        """Add a message to memory"""
        pass
    
    @abstractmethod
    def get_context(self, context: MemoryContext) -> str:
        """Get formatted context for the prompt"""
        pass
    
    @abstractmethod
    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search through memory semantically"""
        pass
    
    @abstractmethod
    def summarize_conversation(self, messages: List[Message]) -> str:
        """Summarize a conversation"""
        pass
    
    @abstractmethod
    def clear_memory(self) -> None:
        """Clear user's memory"""
        pass

class UserProfile:
    """User profile model - простая версия без pydantic"""
    def __init__(self, user_id: str, name: Optional[str] = None,
                 preferences: Dict[str, Any] = None, communication_style: Dict[str, Any] = None,
                 interests: List[str] = None, current_strategy: str = "caring",
                 question_count: int = 0, total_messages: int = 0, days_since_start: int = 1,
                 last_activity: datetime = None, timezone: str = "UTC", language: str = "ru"):
        self.user_id = user_id
        self.name = name
        self.preferences = preferences or {}
        self.communication_style = communication_style or {}
        self.interests = interests or []
        self.current_strategy = current_strategy
        self.question_count = question_count
        self.total_messages = total_messages
        self.days_since_start = days_since_start
        self.last_activity = last_activity or datetime.utcnow()
        self.timezone = timezone
        self.language = language

# Alias for backward compatibility
BaseMemory = MemoryAdapter 