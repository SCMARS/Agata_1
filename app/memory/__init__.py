# Memory system package - полная архитектура без хардкода

from app.memory.base import MemoryAdapter, Message, MemoryContext, UserProfile, MessageRole
from app.memory.buffer_memory import BufferMemory
from app.memory.enhanced_buffer_memory import EnhancedBufferMemory, EmotionTag, BehaviorTag
from app.memory.vector_memory import VectorMemory
from app.memory.hybrid_memory import HybridMemory
from app.memory.langchain_memory import LangChainMemory

# Восстановленные LangChain модули
from app.memory.short_memory import ShortMemory, LangGraphShortMemory, create_short_memory
from app.memory.intelligent_vector_memory import IntelligentVectorMemory, create_intelligent_vector_memory
from app.memory.memory_levels import (
    MemoryLevelsManager, MemoryLevel, MemorySearchResult, MemoryEpisode,
    create_memory_levels_manager
)

__all__ = [
    # Базовые классы
    'MemoryAdapter',
    'Message', 
    'MemoryContext',
    'UserProfile',
    'MessageRole',
    
    # Простые реализации памяти
    'BufferMemory',
    'VectorMemory',
    
    # Продвинутые реализации памяти
    'EnhancedBufferMemory',
    'EmotionTag',
    'BehaviorTag',
    'HybridMemory',
    'LangChainMemory',
    
    # LangChain интеграция
    'ShortMemory',
    'LangGraphShortMemory',
    'create_short_memory',
    'IntelligentVectorMemory',
    'create_intelligent_vector_memory',
    
    # Многоуровневая система памяти
    'MemoryLevelsManager',
    'MemoryLevel',
    'MemorySearchResult',
    'MemoryEpisode',
    'create_memory_levels_manager'
] 