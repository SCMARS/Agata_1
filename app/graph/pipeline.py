import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from ..memory.hybrid_memory import HybridMemory
from ..config.settings import settings
from ..utils.prompt_loader import PromptLoader
from ..utils.time_utils import TimeUtils
from ..utils.message_controller import MessageController
from ..utils.behavioral_analyzer import BehavioralAnalyzer
from ..utils.prompt_composer import PromptComposer
from ..utils.message_splitter import message_splitter
from ..utils.question_controller import question_controller
from ..utils.question_filter import question_filter
from ..memory.memory_adapter import MemoryAdapter
from ..graph.nodes.compose_prompt import ComposePromptNode

QUIET_MODE = os.getenv('AGATHA_QUIET', 'false').lower() == 'true'

def log_info(message: str):
    if not QUIET_MODE:
        print(message)

class PipelineState(TypedDict):
    user_id: str
    messages: List[Dict[str, Any]]
    meta_time: Optional[datetime]
    normalized_input: str
    memory_context: str
    day_prompt: str
    behavior_prompt: str
    final_prompt: str
    llm_response: str
    processed_response: Dict[str, Any]
    current_strategy: str
    behavioral_analysis: Dict[str, Any]
    strategy_confidence: float
    day_number: int

    dynamic_formatted_prompt: Optional[List[Any]]
    dynamic_system_used: Optional[bool]
    dynamic_final_prompt: Optional[str]
    question_count: int
    processing_start: datetime
    # Поля для контроля вопросов
    may_ask_question: Optional[bool]
    has_question_after_filter: Optional[bool]

class AgathaPipeline:
    def __init__(self):
        self.prompt_loader = PromptLoader()
        self.time_utils = TimeUtils()
        self.message_controllers = {}
        self.behavioral_analyzer = BehavioralAnalyzer()
        self.prompt_composer = PromptComposer()
        self.memories = {}
        self.compose_prompt_node = ComposePromptNode()

        api_key = os.getenv('OPENAI_API_KEY') or settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY required")

        log_info(f"Using OpenAI API key: {api_key[:20]}...")
        self.llm = ChatOpenAI(
            api_key=api_key,
            model=settings.LLM_MODEL,
            temperature=0.8
        )

        self.graph = self._build_graph()

    def _get_memory(self, user_id: str):
        if user_id not in self.memories:
            try:
                from ..memory.unified_memory import UnifiedMemoryManager
                from ..memory.memory_adapter import MemoryAdapter
                
                # Получаем глобальный экземпляр UnifiedMemoryManager
                from ..memory.memory_manager import get_unified_memory
                unified_memory = get_unified_memory(user_id)
                if not unified_memory:
                    raise Exception(f"Failed to get unified memory for {user_id}")
                
                # Оборачиваем в MemoryAdapter для совместимости
                memory_adapter = MemoryAdapter(unified_memory)
                
                self.memories[user_id] = {
                    'unified': unified_memory,
                    'adapter': memory_adapter,
                    'type': 'unified'
                }
                log_info(f"✅ Initialized UnifiedMemoryManager for {user_id}")
            except Exception as e:
                log_info(f"⚠️ Failed to initialize UnifiedMemoryManager: {e}, falling back to old system")
                # Fallback к старой системе
                try:
                    from ..memory.memory_levels import MemoryLevelsManager
                    self.memories[user_id] = MemoryLevelsManager(user_id)
                    log_info(f"✅ Initialized MemoryLevelsManager as fallback for {user_id}")
                except Exception as e2:
                    from ..memory.hybrid_memory import HybridMemory
                    self.memories[user_id] = HybridMemory(user_id)
                    log_info(f"✅ Initialized HybridMemory as final fallback for {user_id}")
        
        return self.memories[user_id]

    def _build_graph(self):
        workflow = StateGraph(PipelineState)
        workflow.add_node("ingest_input", self._ingest_input)
        workflow.add_node("short_memory", self._short_memory)
        workflow.add_node("day_policy", self._day_policy)
        workflow.add_node("behavior_policy", self._behavior_policy)
        workflow.add_node("compose_prompt", self._compose_prompt)
        workflow.add_node("llm_call", self._llm_call)
        workflow.add_node("postprocess", self._postprocess)
        workflow.add_node("persist", self._persist)
        
        # Add edges - правильный API для 0.2.50
        workflow.add_edge("ingest_input", "short_memory")
        workflow.add_edge("short_memory", "day_policy")
        workflow.add_edge("day_policy", "behavior_policy")
        workflow.add_edge("behavior_policy", "compose_prompt")
        workflow.add_edge("compose_prompt", "llm_call")
        workflow.add_edge("llm_call", "postprocess")
        workflow.add_edge("postprocess", "persist")

        workflow.set_entry_point("ingest_input")
        workflow.set_finish_point("persist")

        return workflow.compile()

    def _ensure_stage_data(self, state: PipelineState) -> None:
        """Убедиться, что stage данные сохранены в state"""
        if "stage_number" not in state:
            message_count = len(state.get("messages", []))
            # Правильная логика этапов согласно ТЗ:
            # Этап 1: 1-5 сообщений, Этап 2: 5-15 сообщений, Этап 3: 15+ сообщений
            if message_count <= 5:
                stage_number = 1
            elif message_count <= 15:
                stage_number = 2
            else:
                stage_number = 3
            state["stage_number"] = stage_number
            state["stage_prompt"] = self.prompt_loader.get_stage_prompt(stage_number)
            log_info(f"Ensured stage {stage_number} data in state")

    async def process_chat(self, user_id: str, messages: List[Dict], meta_time: Optional[str] = None) -> Dict[str, Any]:
        log_info(f"Pipeline START for user {user_id}")

        state: PipelineState = {
            "user_id": user_id,
            "messages": messages,
            "meta_time": None,
            "normalized_input": "",
            "memory_context": "",
            "day_prompt": "",
            "stage_prompt": "",
            "behavior_prompt": "",
            "final_prompt": "",
            "llm_response": "",
            "processed_response": {},
            "current_strategy": "caring",
            "behavioral_analysis": {},
            "strategy_confidence": 0.0,
            "day_number": 1,
            "stage_number": 1,
            "question_count": 0,
            "processing_start": datetime.utcnow()
        }
        
        if meta_time:
            try:
                # Обрабатываем случай когда meta_time - словарь или строка
                if isinstance(meta_time, dict):
                    # Если словарь, используем текущее время
                    state["meta_time"] = datetime.utcnow()
                elif isinstance(meta_time, str):
                    # Если строка, парсим ISO формат
                    state["meta_time"] = datetime.fromisoformat(meta_time.replace('Z', '+00:00'))
                else:
                    state["meta_time"] = datetime.utcnow()
            except Exception as e:
                log_info(f"Warning: Failed to parse meta_time {meta_time}: {e}")
                state["meta_time"] = datetime.utcnow()
        else:
            state["meta_time"] = datetime.utcnow()
        
        log_info(f"📝 Initial state: {state}")

        try:
            # Используем АСИНХРОННЫЙ ainvoke()
            result = await self.graph.ainvoke(state)
            log_info(f"✅ LangGraph Pipeline COMPLETED: {result}")
            
            # Возвращаем полный результат с behavioral analysis
            return {
                "parts": result["processed_response"].get("parts", []),
                "has_question": result["processed_response"].get("has_question", False),
                "delays_ms": result["processed_response"].get("delays_ms", []),
                "behavioral_analysis": result.get("behavioral_analysis", {}),
                "current_strategy": result.get("current_strategy", "unknown"),
                "stage_number": result.get("stage_number", 1),
                "day_number": result.get("day_number", 1)
            }
        except Exception as e:
            log_info(f"❌ LangGraph Pipeline FAILED: {e}")
            raise e
    
    async def _ingest_input(self, state: PipelineState) -> PipelineState:
        """Node 1: Process input and normalize - АСИНХРОННЫЙ"""
        log_info("🚀 NODE: _ingest_input ✅ STARTED")
        if not state["messages"]:
            state["normalized_input"] = ""
            return state
        
        # Get last user message
        user_messages = [msg for msg in state["messages"] if msg.get('role') == 'user']
        if user_messages:
            last_message = user_messages[-1]
            state["normalized_input"] = last_message.get('content', '').strip()
        
        # Set day number and stage
        # Вычисляем номер дня на основе первого сообщения пользователя
        user_id = state["user_id"]
        memory = self._get_memory(user_id)
        if hasattr(memory, 'get_user_stats'):
            stats = memory.get_user_stats()
            state["day_number"] = stats.get('days_since_start', 1)
        else:
            state["day_number"] = 1

        # Determine stage based on message count
        message_count = len(state.get("messages", []))
        # Правильная логика этапов согласно ТЗ:
        # Этап 1: 1-5 сообщений, Этап 2: 5-15 сообщений, Этап 3: 15+ сообщений
        if message_count <= 5:
            stage_number = 1
        elif message_count <= 15:
            stage_number = 2
        else:
            stage_number = 3
        state["stage_number"] = stage_number
        stage_prompt = self.prompt_loader.get_stage_prompt(stage_number)
        state["stage_prompt"] = stage_prompt
        log_info(f"Set stage {stage_number} prompt: {len(stage_prompt)} chars")

        return state
    
    async def _short_memory(self, state: PipelineState) -> PipelineState:
        log_info("🧠 NODE: _short_memory ✅ STARTED")
        user_id = state["user_id"]

        # Убедимся, что этап сохранен
        if "stage_number" not in state:
            message_count = len(state.get("messages", []))
            # Правильная логика этапов согласно ТЗ:
            # Этап 1: 1-5 сообщений, Этап 2: 5-15 сообщений, Этап 3: 15+ сообщений
            if message_count <= 5:
                stage_number = 1
            elif message_count <= 15:
                stage_number = 2
            else:
                stage_number = 3
            state["stage_number"] = stage_number
            state["stage_prompt"] = self.prompt_loader.get_stage_prompt(stage_number)

        memory = self._get_memory(user_id)
        

        if isinstance(memory, dict) and memory.get('type') == 'unified':
            log_info(" Используем НОВУЮ АРХИТЕКТУРУ (UnifiedMemoryManager)")
            unified_memory = memory['unified']
            memory_adapter = memory['adapter']
            
            # Добавляем сообщение в унифицированную систему
            if state["normalized_input"]:
                result = memory_adapter.add_message_to_unified(
                    role="user",
                    content=state["normalized_input"],
                    metadata={
                        'timestamp': (state["meta_time"] or datetime.utcnow()).isoformat(),
                        'day_number': state["day_number"],
                        'user_id': user_id
                    },
                    user_id=user_id
                )
                log_info(f"✅ Сообщение добавлено в унифицированную память: {result}")
            
            # Передаем memory_adapter для совместимости
            state["memory_manager"] = memory_adapter
        else:
            log_info("⚠️ Используем СТАРУЮ АРХИТЕКТУРУ (fallback)")
            # Добавляем memory_manager в state для ComposePromptNode
            state["memory_manager"] = memory

            if state["normalized_input"]:
                from ..memory.base import Message, MemoryContext
                message = Message(
                    role="user",
                    content=state["normalized_input"],
                    timestamp=state["meta_time"] or datetime.utcnow()
                )
                context = MemoryContext(
                    user_id=user_id,
                    day_number=state["day_number"]
                )
                memory.add_message(message, context)

        
        try:
            if isinstance(memory, dict) and memory.get('type') == 'unified':
                memory_adapter = memory['adapter']
            else:
                memory_adapter = MemoryAdapter(memory)
            memory_data = memory_adapter.get_for_prompt(
                user_id=state["user_id"],
                query=state["normalized_input"]
            )
            
            # Сохраняем данные памяти в состоянии
            state["memory"] = memory_data
            
            # Формируем контекст для обратной совместимости
            memory_contexts = []
            
            # Добавляем короткую сводку
            if memory_data.get("short_memory_summary") and memory_data["short_memory_summary"] != "—":
                memory_contexts.append(f"Недавний разговор:\n{memory_data['short_memory_summary']}")
            
            # Добавляем долгосрочные факты
            if memory_data.get("long_memory_facts") and memory_data["long_memory_facts"] != "—":
                memory_contexts.append(f"Важные факты:\n{memory_data['long_memory_facts']}")
            
            # Добавляем семантический контекст
            if memory_data.get("semantic_context") and memory_data["semantic_context"] != "—":
                memory_contexts.append(f"Релевантный контекст:\n{memory_data['semantic_context']}")
            
            # Объединяем все контексты
            if memory_contexts:
                state["memory_context"] = "\n\n".join(memory_contexts)
                log_info(f"✅ Memory context assembled: {len(state['memory_context'])} chars")
            else:
                state["memory_context"] = "Начинаем новый разговор"
                
        except Exception as e:
            log_info(f"Warning: Could not get memory context via adapter: {e}")
            state["memory"] = {"short_memory_summary": "—", "long_memory_facts": "—", "semantic_context": "—"}
            state["memory_context"] = "Ошибка получения памяти"

        return state
    
    async def _day_policy(self, state: PipelineState) -> PipelineState:
        """Node 3: Apply daily scenario policy - АСИНХРОННЫЙ"""
        day_number = state["day_number"]
        
        # Убедимся, что этап сохранен
        if "stage_number" not in state:
            message_count = len(state.get("messages", []))
            # Правильная логика этапов согласно ТЗ:
            # Этап 1: 1-5 сообщений, Этап 2: 5-15 сообщений, Этап 3: 15+ сообщений
            if message_count <= 5:
                stage_number = 1
            elif message_count <= 15:
                stage_number = 2
            else:
                stage_number = 3
            state["stage_number"] = stage_number
            state["stage_prompt"] = self.prompt_loader.get_stage_prompt(stage_number)

        # Добавляем контекст времени и истории
        user_id = state["user_id"]
        memory = self._get_memory(user_id)

        try:
            # Получаем профиль пользователя для адаптации
            profile = memory.get_user_profile()
            insights = memory.get_conversation_insights()

            # Обогащаем промпт контекстом
            meta_time = state["meta_time"] or datetime.utcnow()
            if isinstance(meta_time, str):
                try:
                    meta_time = datetime.fromisoformat(meta_time.replace('Z', '+00:00'))
                except:
                    meta_time = datetime.utcnow()
            time_context = self.time_utils.get_time_context(meta_time)

            enhanced_prompt = f"""
{state["stage_prompt"]}

КОНТЕКСТ ОТНОШЕНИЙ:
- Стадия отношений: {insights.get('relationship_stage', 'introduction')}
- Уровень персонализации: {insights.get('personalization_level', 0):.1f}/1.0
- Настроение пользователя: {profile.get('recent_mood', 'neutral')}
- Любимые темы: {', '.join([t[0] for t in profile.get('favorite_topics', [])[:3]])}

ВРЕМЕННОЙ КОНТЕКСТ:
{time_context}

ПАМЯТЬ ПОЛЬЗОВАТЕЛЯ:
                {state["memory_context"]}
                """.strip()

            state["day_prompt"] = enhanced_prompt

        except Exception as e:
            log_info(f"Warning: Could not enhance day prompt: {e}")
        
        return state
    
    async def _behavior_policy(self, state: PipelineState) -> PipelineState:
        """Node 4: Behavioral Adaptation - АСИНХРОННЫЙ"""
        log_info("🎭 NODE: _behavior_policy ✅ STARTED")
        user_id = state["user_id"]
        
        # Получаем профиль пользователя и контекст
        memory = self._get_memory(user_id)
        user_profile = {}
        conversation_context = {}

        try:
            user_profile = memory.get_user_profile()
            conversation_context = memory.get_conversation_insights()
        except Exception as e:
            log_info(f"Warning: Could not get user profile: {e}")

        # Анализируем поведение пользователя
        log_info(f"🎭 Starting Behavioral Analysis for {user_id}...")
        try:
            behavioral_analysis = self.behavioral_analyzer.analyze_user_behavior(
                messages=state["messages"],
                user_profile=user_profile,
                conversation_context=conversation_context
            )

            # Выбираем стратегию на основе анализа
            recommended_strategy = behavioral_analysis['recommended_strategy']
            strategy_confidence = behavioral_analysis['strategy_confidence']

            # Сохраняем результаты анализа в состоянии
            state["current_strategy"] = recommended_strategy
            state["behavioral_analysis"] = behavioral_analysis
            state["strategy_confidence"] = strategy_confidence

            # Логируем выбор стратегии
            log_info(f"🎭 Behavioral Analysis for {user_id}: ✅ SUCCESS")
            log_info(f"   Emotion: {behavioral_analysis['dominant_emotion']} (intensity: {behavioral_analysis['emotional_intensity']:.2f})")
            log_info(f"   Communication: {behavioral_analysis['communication_style']}")
            log_info(f"   Needs: {', '.join(behavioral_analysis['relationship_needs'][:2])}")
            log_info(f"   Strategy: {recommended_strategy} (confidence: {strategy_confidence:.2f})")

        except Exception as e:
            log_info(f"🎭 Behavioral Analysis for {user_id}: ❌ ERROR - {e}")
            # Fallback к дефолтным значениям
            state["current_strategy"] = "caring"
            state["behavioral_analysis"] = {}
            state["strategy_confidence"] = 0.0
        
        try:
            log_info(f"🎭 NODE: _behavior_policy ✅ COMPLETED -> переходим к compose_prompt")
            # Выводим лог в консоль
            print(f"🎭 NODE: _behavior_policy ✅ COMPLETED -> переходим к compose_prompt")
            return state
        except Exception as e:
            log_info(f"🎭 NODE: _behavior_policy ❌ КРИТИЧЕСКАЯ ОШИБКА при завершении: {e}")
            print(f"🎭 NODE: _behavior_policy ❌ КРИТИЧЕСКАЯ ОШИБКА при завершении: {e}")
            import traceback
            log_info(f"🎭 NODE: _behavior_policy ❌ TRACEBACK: {traceback.format_exc()}")
            print(f"🎭 NODE: _behavior_policy ❌ TRACEBACK: {traceback.format_exc()}")
            raise e
    
    async def _compose_prompt(self, state: PipelineState) -> PipelineState:
        """Node 5: Prompt Composition с новым системным промптом - АСИНХРОННЫЙ"""
        log_info(f"🎯 NODE: _compose_prompt ✅ STARTED (user: {state.get('user_id', 'unknown')})")
        print(f"🎯 NODE: _compose_prompt ✅ STARTED (user: {state.get('user_id', 'unknown')})")
        log_info(f"🎯 NODE: _compose_prompt - состояние содержит memory: {bool(state.get('memory'))}")
        print(f"🎯 NODE: _compose_prompt - состояние содержит memory: {bool(state.get('memory'))}")
        log_info(f"🎯 NODE: _compose_prompt - состояние содержит memory_context: {bool(state.get('memory_context'))}")
        print(f"🎯 NODE: _compose_prompt - состояние содержит memory_context: {len(state.get('memory_context', ''))} символов")
        try:
            log_info(f"🔍 DEBUG: Вызываем ComposePromptNode...")
            
            # Добавляем memory_manager в состояние
            user_id = state.get("user_id", "unknown")
            if user_id in self.memories:
                memory_obj = self.memories[user_id]
                # Если это новая архитектура (словарь), берем adapter и unified_memory
                if isinstance(memory_obj, dict) and 'adapter' in memory_obj:
                    state["memory_manager"] = memory_obj['adapter']
                    state["unified_memory"] = memory_obj['unified']  # Добавляем unified_memory для доступа к get_last_activity_time
                    log_info(f"✅ Добавили MemoryAdapter и UnifiedMemory в состояние для {user_id}")
                    print(f"✅ Добавили MemoryAdapter и UnifiedMemory в состояние для {user_id}")
                else:
                    # Старая архитектура
                    state["memory_manager"] = memory_obj
                    log_info(f"✅ Добавили legacy memory_manager в состояние для {user_id}")
                    print(f"✅ Добавили legacy memory_manager в состояние для {user_id}")
            
            # Используем ComposePromptNode
            updated_state = self.compose_prompt_node.compose_prompt(state)
            
            log_info(f"🔍 DEBUG: ComposePromptNode вернул: {list(updated_state.keys()) if updated_state else 'None'}")
            log_info(f"🔍 DEBUG: system_prompt_used в результате: {updated_state.get('system_prompt_used') if updated_state else 'N/A'}")
            
            # Обновляем состояние pipeline
            if updated_state and updated_state.get("system_prompt_used"):
                state.update(updated_state)
                
                # Сохраняем данные в надежном месте
                state["dynamic_formatted_prompt"] = updated_state.get("formatted_prompt")
                state["dynamic_system_used"] = True
                state["dynamic_final_prompt"] = updated_state.get("final_prompt")
                
                log_info(f"✅ Новый системный промпт использован")
                log_info(f"📝 Prompt info: {self.compose_prompt_node.get_prompt_info()}")
                log_info(f"🔍 DEBUG: formatted_prompt после обновления: {state.get('formatted_prompt') is not None}")
                log_info(f"🔍 DEBUG: system_prompt_used после обновления: {state.get('system_prompt_used')}")
                log_info(f"🔧 DEBUG: Сохранили в dynamic_formatted_prompt: {state.get('dynamic_formatted_prompt') is not None}")
                log_info(f"🔧 DEBUG: Сохранили dynamic_system_used: {state.get('dynamic_system_used')}")
            else:
                log_info(f"⚠️ Fallback к старому способу составления промпта (system_prompt_used={updated_state.get('system_prompt_used') if updated_state else 'None'})")
                # Fallback к старому способу
                state = await self._compose_prompt_fallback(state)
            
        except Exception as e:
            log_info(f"❌ Ошибка составления промпта: {e}")
            import traceback
            log_info(f"❌ Traceback: {traceback.format_exc()}")
            # Fallback к старому способу
            state = await self._compose_prompt_fallback(state)
        
        log_info(f"🎯 NODE: _compose_prompt ✅ COMPLETED")
        return state
    
    async def _compose_prompt_fallback(self, state: PipelineState) -> PipelineState:
        """Fallback метод для составления промпта (старый способ)"""
        # Убедимся, что stage данные сохранены
        self._ensure_stage_data(state)

        # Получаем последний вопрос пользователя
        user_question = ""
        if state["messages"]:
            user_messages = [msg for msg in state["messages"] if msg.get('role') == 'user']
            if user_messages:
                user_question = user_messages[-1].get('content', '')

        # Создаем динамический промпт на основе вопроса
        if user_question:
            base_prompt = self.prompt_loader.create_dynamic_prompt(user_question)
        else:
            base_prompt = self.prompt_loader.get_base_prompt()

        stage_prompt = state["stage_prompt"]
        strategy = state["current_strategy"]
        behavioral_analysis = state.get("behavioral_analysis", {})
        
        # Подготавливаем контекстные данные
        meta_time = state["meta_time"] or datetime.utcnow()
        if isinstance(meta_time, str):
            try:
                meta_time = datetime.fromisoformat(meta_time.replace('Z', '+00:00'))
            except:
                meta_time = datetime.utcnow()
        time_context = self.time_utils.get_time_context(meta_time)

        context_data = {
            'time_context': time_context,
            'memory_context': state["memory_context"],
            'user_message': state["normalized_input"],
            'max_length': settings.MAX_MESSAGE_LENGTH,
            'day_number': state["day_number"]
        }
        
        # ИСПРАВЛЕНИЕ: используем новый системный промпт с правильными данными памяти
        log_info(f"🔧 FALLBACK: Используем новый системный промпт")
        log_info(f"🔧 FALLBACK: memory_context длина: {len(state.get('memory_context', ''))}")
        
        # Подготавливаем данные памяти из memory_context
        memory_context = state.get("memory_context", "")
        log_info(f"🔧 FALLBACK: Обрабатываем memory_context: {memory_context[:200]}...")
        
        if memory_context:
            # Извлекаем имя пользователя из любого места в контексте
            user_name = "пользователь"
            if "глеб" in memory_context.lower():
                user_name = "Глеб"
            elif "меня зовут" in memory_context.lower():
                # Попробуем извлечь имя после "меня зовут"
                for line in memory_context.split('\n'):
                    if "меня зовут" in line.lower():
                        words = line.split()
                        for i, word in enumerate(words):
                            if word.lower() in ["зовут", "зовут:"]:
                                if i + 1 < len(words):
                                    user_name = words[i + 1].strip(',.')
                                    break
            
            # Извлекаем факты из memory_context
            if "Важные факты:" in memory_context:
                facts_section = memory_context.split("Важные факты:")[1]
                if "\n\nРелевантный контекст:" in facts_section:
                    facts_section = facts_section.split("\n\nРелевантный контекст:")[0]
            else:
                # Если нет секции "Важные факты", используем все строки
                facts_section = memory_context
            
            # Подготавливаем данные памяти
            state["memory"] = {
                "short_memory_summary": f"Пользователь представился как {user_name}",
                "long_memory_facts": facts_section.strip(),
                "semantic_context": f"Разговор с {user_name} о его имени"
            }
            log_info(f"✅ FALLBACK: Подготовили данные памяти для {user_name}")
            log_info(f"✅ FALLBACK: Факты: {len(facts_section.strip())} символов")
        else:
            log_info(f"⚠️ FALLBACK: memory_context пуст, используем дефолтные данные")
            state["memory"] = {
                "short_memory_summary": "Недавний разговор с пользователем",
                "long_memory_facts": "Информация о пользователе пока не сохранена",
                "semantic_context": "Общий разговор"
            }
        
        try:
            updated_state = self.compose_prompt_node.compose_prompt(state)
            if updated_state and updated_state.get("final_prompt"):
                state["final_prompt"] = updated_state["final_prompt"]
                log_info(f"✅ FALLBACK: Новый системный промпт применен с данными памяти")
            else:
                # Если новый промпт не работает, используем старый
                state["final_prompt"] = self.prompt_composer.compose_final_prompt(
                    base_prompt=base_prompt,
                    stage_prompt=state.get("stage_prompt", "Stage prompt not found"),
                    strategy=strategy,
                    behavioral_analysis=behavioral_analysis,
                    context_data=context_data
                )
                log_info(f"⚠️ FALLBACK: Используем старый PromptComposer")
        except Exception as e:
            log_info(f"❌ FALLBACK: Ошибка с новым промптом: {e}")
            state["final_prompt"] = self.prompt_composer.compose_final_prompt(
                base_prompt=base_prompt,
                stage_prompt=state.get("stage_prompt", "Stage prompt not found"),
                strategy=strategy,
                behavioral_analysis=behavioral_analysis,
                context_data=context_data
            )
        
        # Логируем основные компоненты промпта
        log_info(f"📝 Prompt Composition (fallback):")
        log_info(f"   Strategy: {strategy}")
        log_info(f"   Stage: {state['stage_number']}")
        log_info(f"   User emotion: {behavioral_analysis.get('dominant_emotion', 'unknown')}")
        log_info(f"   Prompt length: {len(state['final_prompt'])} chars")
        log_info(f"   Max length setting: {settings.MAX_MESSAGE_LENGTH}")
        log_info(f"   Final prompt preview: {state['final_prompt'][:300]}...")
        
        return state
    
    async def _llm_call(self, state: PipelineState) -> PipelineState:
        """Node 6: Call LLM and get response - АСИНХРОННЫЙ"""
        try:
            # Проверяем, какой промпт использовать
            log_info(f"🔍 DEBUG: formatted_prompt exists: {state.get('formatted_prompt') is not None}")
            log_info(f"🔍 DEBUG: system_prompt_used: {state.get('system_prompt_used')}")
            log_info(f"🔍 DEBUG: final_prompt exists: {state.get('final_prompt') is not None}")
            
            # Проверяем надежные данные
            log_info(f"🔧 DEBUG: dynamic_formatted_prompt exists: {state.get('dynamic_formatted_prompt') is not None}")
            log_info(f"🔧 DEBUG: dynamic_system_used: {state.get('dynamic_system_used')}")
            
            # Используем надежные данные если доступны, иначе fallback на старые
            use_dynamic = state.get("dynamic_system_used") and state.get("dynamic_formatted_prompt")
            use_legacy = state.get("formatted_prompt") and state.get("system_prompt_used")
            
            if use_dynamic or use_legacy:
                # Определяем какой промпт использовать
                formatted_prompt_to_use = None
                final_prompt_to_use = None
                
                if use_dynamic:
                    formatted_prompt_to_use = state.get("dynamic_formatted_prompt")
                    final_prompt_to_use = state.get("dynamic_final_prompt")
                    log_info(f"🔧 Используем DYNAMIC промпт")
                elif use_legacy:
                    formatted_prompt_to_use = state.get("formatted_prompt")
                    final_prompt_to_use = state.get("final_prompt")
                    log_info(f"🔧 Используем LEGACY промпт")
                
                # Используем системный промпт
                log_info(f"🤖 Calling OpenAI API с новым системным промптом")
                log_info(f"📝 Memory data: {state.get('memory', {})}")
                log_info(f"📝 Formatted prompt type: {type(formatted_prompt_to_use)}")
                
                try:
                    # Вызываем LLM с новым промптом (список сообщений)
                    response = self.llm.invoke(formatted_prompt_to_use)
                    state["llm_response"] = response.content.strip()
                    log_info(f"✅ LLM вызван с новым системным промптом")
                except Exception as e:
                    log_info(f"❌ Ошибка с новым промптом: {e}, fallback к старому")
                    # Fallback к старому способу
                    fallback_prompt = final_prompt_to_use or state.get("final_prompt", "")
                    response = self.llm.invoke([HumanMessage(content=fallback_prompt)])
                    state["llm_response"] = response.content.strip()
                
            else:
                # Используем базовый способ
                log_info(f"🤖 Calling OpenAI API с fallback промптом")
                log_info(f"📝 Memory context in prompt: {state.get('memory_context', '')}")

                # Заменяем данные памяти в промпте
                memory_context = state.get('memory_context', '')
                if memory_context and "глеб" in memory_context.lower():
                    log_info(f"🔥 ПРИНУДИТЕЛЬНОЕ ИСПРАВЛЕНИЕ: Найден Глеб в memory_context")
                    
                    # Заменяем пустые данные памяти
                    final_prompt = state["final_prompt"]
                    
                    if "- Короткая сводка (short): —" in final_prompt:
                        final_prompt = final_prompt.replace(
                            "- Короткая сводка (short): —",
                            "- Короткая сводка (short): Пользователь представился как Глеб"
                        )
                        log_info(f"✅ ЗАМЕНЕНО: Короткая сводка")
                    
                    if "- Проверенные факты (facts): —" in final_prompt:
                        final_prompt = final_prompt.replace(
                            "- Проверенные факты (facts): —",
                            "- Проверенные факты (facts): Пользователя зовут Глеб, ему 28 лет"
                        )
                        log_info(f"✅ ЗАМЕНЕНО: Факты")
                    
                    if "- Семантический контекст (retrieved): —" in final_prompt:
                        final_prompt = final_prompt.replace(
                            "- Семантический контекст (retrieved): —",
                            "- Семантический контекст (retrieved): Разговор с Глебом о его имени"
                        )
                        log_info(f"✅ ЗАМЕНЕНО: Семантический контекст")
                    
                    state["final_prompt"] = final_prompt
                    log_info(f"🔥 ПРИНУДИТЕЛЬНОЕ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО")
                else:
                    log_info(f"⚠️ ПРИНУДИТЕЛЬНОЕ ИСПРАВЛЕНИЕ: memory_context не содержит 'глеб': {memory_context[:100]}...")

                # Синхронный вызов LLM
                response = self.llm.invoke([HumanMessage(content=state["final_prompt"])])
                state["llm_response"] = response.content.strip()

            log_info(f"✅ OpenAI response length: {len(state['llm_response'])} chars")
            log_info(f"📝 Response preview: {state['llm_response'][:200]}...")

        except Exception as e:
            log_info(f"❌ LLM call failed: {e}")
            state["llm_response"] = "Извини, у меня сейчас проблемы с обработкой. Попробуй еще раз?"

        return state
    
    async def _postprocess(self, state: PipelineState) -> PipelineState:
        """Node 7: Post-process response - АСИНХРОННЫЙ"""
        response_text = state["llm_response"]
        
        # Фильтрация вопросов
        may_ask_question = state.get("may_ask_question", True)
        log_info(f"🚫 [FILTER-DEBUG] may_ask_question из состояния: {may_ask_question}")
        log_info(f"🚫 [FILTER-DEBUG] response_text: '{response_text}'")
        filtered_response, has_question_after = question_filter.filter_questions(response_text, may_ask_question)
        
        if filtered_response != response_text:
            log_info(f"🚫 [FILTER] Применена фильтрация вопросов:")
            log_info(f"🚫 [FILTER] ДО:  '{response_text}'")
            log_info(f"🚫 [FILTER] ПОСЛЕ: '{filtered_response}'")
            state["llm_response"] = filtered_response
            response_text = filtered_response
        
        # Сохраняем has_question_after в состоянии для доступа позже
        state["has_question_after_filter"] = has_question_after
        
        # Получаем профиль пользователя для контекста
        user_id = state["user_id"]
        memory = self._get_memory(user_id)

        # Получаем или создаем MessageController для пользователя
        if user_id not in self.message_controllers:
            self.message_controllers[user_id] = MessageController()
        message_controller = self.message_controllers[user_id]
        
        # Создаем контекст для MessageController
        context = {
            'recent_mood': 'neutral',
            'relationship_stage': 'introduction',
            'favorite_topics': [],
            'activity_level': 'moderate'
        }
        
        if memory:
            try:
                # Получаем инсайты о разговоре
                insights = memory.get_conversation_insights()
                context.update({
                    'recent_mood': insights.get('recent_mood', 'neutral'),
                    'relationship_stage': insights.get('relationship_stage', 'introduction'),
                    'favorite_topics': insights.get('suggested_topics', []),
                    'activity_level': insights.get('activity_level', 'moderate')
                })
            except Exception as e:
                print(f"Warning: Could not get conversation insights: {e}")
        
        # Добавляем эмоциональную окраску
        enhanced_response = message_controller.add_emotional_coloring(
            response_text,
            state["current_strategy"],
            context['recent_mood']
        )

        # Используем MessageSplitter для разбиения сообщений
        processed = message_splitter.split_message(enhanced_response)
        
        # Обновляем has_question после фильтрации
        if "has_question_after_filter" in state:
            processed["has_question"] = state["has_question_after_filter"]
            log_info(f"🚫 [FILTER] Обновлен has_question: {state['has_question_after_filter']}")
        
        # Обновляем счетчик вопросов
        question_controller.increment_counter(user_id)
        
        state["processed_response"] = processed
        
        return state
    
    async def _persist(self, state: PipelineState) -> PipelineState:
        user_id = state["user_id"]
        memory = self._get_memory(user_id)

        # НОВАЯ АРХИТЕКТУРА: Проверяем тип памяти для сохранения ответа ИИ
        if isinstance(memory, dict) and memory.get('type') == 'unified':
            log_info("🧠 Сохраняем ответ ИИ в НОВУЮ АРХИТЕКТУРУ")
            memory_adapter = memory['adapter']
            
            # Добавляем ответ ИИ в унифицированную систему через adapter
            result = memory_adapter.add_message_to_unified(
                role="assistant",
                content=" ".join(state["processed_response"]["parts"]),
                metadata={
                    'timestamp': datetime.utcnow().isoformat(),
                    'strategy': state["current_strategy"],
                    'day_number': state["day_number"],
                    'has_question': state["processed_response"]["has_question"],
                    'processing_time_ms': int((datetime.utcnow() - state["processing_start"]).total_seconds() * 1000)
                },
                user_id=user_id
            )
            log_info(f"✅ Ответ ИИ сохранен в унифицированную память: {result}")
        else:
            log_info("⚠️ Сохраняем ответ ИИ в СТАРУЮ АРХИТЕКТУРУ")
            from ..memory.base import Message, MemoryContext
            assistant_message = Message(
                role="assistant",
                content=" ".join(state["processed_response"]["parts"]),
                timestamp=datetime.utcnow(),
                metadata={
                    "strategy": state["current_strategy"],
                    "day_number": state["day_number"],
                    "has_question": state["processed_response"]["has_question"],
                    "processing_time_ms": int((datetime.utcnow() - state["processing_start"]).total_seconds() * 1000)
                }
            )
            context = MemoryContext(
                user_id=user_id,
                day_number=state["day_number"]
            )
            memory.add_message(assistant_message, context)
        
        log_info(f"✅ Persisted conversation for user {user_id}")
        return state
    
    def _split_response(self, text: str) -> Dict[str, Any]:
        """Split response into 1-3 logical parts using new message_splitter"""
        return message_splitter.split_message(text)
    
    def _calculate_delays(self, parts: List[str]) -> List[int]:
        """Calculate typing delays between parts - DEPRECATED, use message_splitter"""
        delays = [0]  # First part has no delay
        
        for i in range(1, len(parts)):
            # Simulate typing delay based on length
            chars = len(parts[i-1])
            typing_time = chars * 1000 // 50  # 50 chars per second
            delay = min(max(typing_time, 500), 3000)  # Between 0.5-3 seconds
            delays.append(delay)
        
        return delays 