

from app.config.settings import settings

__version__ = "1.0.0"
__author__ = "Agatha AI Team"
__description__ = "AI Companion with LangGraph and Behavioral Adaptation"

# Импортируем компоненты с обработкой ошибок
try:
    from app.graph.pipeline import AgathaPipeline
    PIPELINE_AVAILABLE = True
except ImportError:
    print("⚠️ Warning: AgathaPipeline not available")
    PIPELINE_AVAILABLE = False

try:
    from app.memory.hybrid_memory import HybridMemory
    from app.utils.behavioral_analyzer import BehavioralAnalyzer
    from app.utils.prompt_composer import PromptComposer
    from app.utils.message_controller import MessageController
    UTILS_AVAILABLE = True
except ImportError:
    print("⚠️ Warning: Some utilities not available")
    UTILS_AVAILABLE = False

__all__ = [
    'settings'
]

if PIPELINE_AVAILABLE:
    __all__.append('AgathaPipeline')

if UTILS_AVAILABLE:
    __all__.extend([
        'HybridMemory', 
        'BehavioralAnalyzer',
        'PromptComposer',
        'MessageController'
    ]) 