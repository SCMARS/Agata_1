"""
Глобальный менеджер экземпляров памяти
Обеспечивает что все части системы используют один экземпляр UnifiedMemoryManager для каждого пользователя
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Глобальный кэш экземпляров памяти
_memory_instances: Dict[str, 'UnifiedMemoryManager'] = {}

def get_unified_memory(user_id: str) -> Optional['UnifiedMemoryManager']:
    """
    Получить или создать единственный экземпляр UnifiedMemoryManager для пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        UnifiedMemoryManager instance или None при ошибке
    """
    global _memory_instances
    
    if user_id not in _memory_instances:
        try:
            from .unified_memory import UnifiedMemoryManager
            _memory_instances[user_id] = UnifiedMemoryManager(user_id)
            logger.info(f"✅ [GLOBAL] Создан новый UnifiedMemoryManager для {user_id}")
            print(f"✅ [GLOBAL] Создан новый UnifiedMemoryManager для {user_id}")
        except Exception as e:
            logger.error(f"❌ [GLOBAL] Ошибка создания UnifiedMemoryManager для {user_id}: {e}")
            print(f"❌ [GLOBAL] Ошибка создания UnifiedMemoryManager для {user_id}: {e}")
            return None
    else:
        logger.debug(f"🔄 [GLOBAL] Используем существующий UnifiedMemoryManager для {user_id}")
        print(f"🔄 [GLOBAL] Используем существующий UnifiedMemoryManager для {user_id}")
    
    return _memory_instances[user_id]

def clear_memory_cache(user_id: Optional[str] = None):
    """
    Очистить кэш памяти для пользователя или всех пользователей
    
    Args:
        user_id: ID пользователя для очистки, или None для очистки всех
    """
    global _memory_instances
    
    if user_id:
        if user_id in _memory_instances:
            del _memory_instances[user_id]
            logger.info(f"🗑️ [GLOBAL] Очищен кэш памяти для {user_id}")
            print(f"🗑️ [GLOBAL] Очищен кэш памяти для {user_id}")
    else:
        _memory_instances.clear()
        logger.info(f"🗑️ [GLOBAL] Очищен весь кэш памяти")
        print(f"🗑️ [GLOBAL] Очищен весь кэш памяти")

def get_memory_stats() -> Dict[str, int]:
    """Получить статистику кэша памяти"""
    return {
        "cached_users": len(_memory_instances),
        "user_ids": list(_memory_instances.keys())
    }
