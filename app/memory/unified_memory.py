
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .intelligent_vector_memory import IntelligentVectorMemory
from ..utils.fact_extractor import fact_extractor

logger = logging.getLogger(__name__)

class UnifiedMemoryManager:
    """
    Унифицированный менеджер памяти
    
    ЛОГИКА:
    - Сообщения 1-10: хранятся в short_term_window
    - Сообщения 11+: старые переносятся в vector_db, новые в window
    - Поиск: сначала window, потом vector_db
    """
    
    def __init__(self, user_id: str, window_size: int = 10):
        self.user_id = user_id
        self.window_size = window_size
        self.short_term_window = []  # Последние N сообщений
        self.message_count = 0
        
        # Инициализируем векторную БД
        try:
            self.vector_db = IntelligentVectorMemory(user_id)
            self.vector_available = True
            logger.info(f"🧠 [UNIFIED-{user_id}] Инициализирована векторная БД")
        except Exception as e:
            logger.error(f"❌ [UNIFIED-{user_id}] Ошибка инициализации векторной БД: {e}")
            self.vector_db = None
            self.vector_available = False
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None, timestamp: Optional[datetime] = None) -> Dict[str, bool]:
        """
        Добавляет сообщение в унифицированную систему памяти
        
        Args:
            role: 'user' или 'assistant'
            content: текст сообщения
            metadata: дополнительные данные
            timestamp: время сообщения (если None - используется текущее)
            
        Returns:
            Результаты сохранения
        """
        self.message_count += 1
        
        # Создаем объект сообщения
        message = {
            'role': role,
            'content': content,
            'metadata': metadata or {},
            'timestamp': (timestamp or datetime.utcnow()).isoformat(),
            'message_id': self.message_count
        }
        
        logger.info(f"📝 [UNIFIED-{self.user_id}] Добавляем сообщение #{self.message_count}: {content[:50]}...")
        
        results = {'short_term': False, 'long_term': False}
        
        # Добавляем в окно краткосрочной памяти
        self.short_term_window.append(message)
        results['short_term'] = True
        
        # Если окно переполнено - переносим старое сообщение в векторную БД
        if len(self.short_term_window) > self.window_size:
            oldest_message = self.short_term_window.pop(0)
            
            if self.vector_available:
                try:
                    # Переносим в векторную БД
                    self.vector_db.add_document(
                        content=oldest_message['content'],
                        metadata={
                            **oldest_message['metadata'],
                            'role': oldest_message['role'],
                            'timestamp': oldest_message['timestamp'],
                            'transferred_from_short_term': True
                        }
                    )
                    results['long_term'] = True
                    logger.info(f"🗄️ [UNIFIED-{self.user_id}] Перенесли сообщение #{oldest_message['message_id']} в векторную БД")
                except Exception as e:
                    logger.error(f"❌ [UNIFIED-{self.user_id}] Ошибка переноса в векторную БД: {e}")
            else:
                logger.warning(f"⚠️ [UNIFIED-{self.user_id}] Векторная БД недоступна, сообщение потеряно")
        
        logger.info(f"✅ [UNIFIED-{self.user_id}] Сообщение добавлено. Окно: {len(self.short_term_window)}, Всего: {self.message_count}")
        return results
    
    def get_context_for_prompt(self, query: str = "") -> Dict[str, str]:
        """
        Получает контекст для промпта с умным выбором источника
        
        Args:
            query: текущий запрос пользователя
            
        Returns:
            Словарь с контекстом для промпта
        """
        logger.info(f"🔍 [UNIFIED-{self.user_id}] Получаем контекст. Сообщений: {self.message_count}, В окне: {len(self.short_term_window)}")
        
        context = {
            "short_memory_summary": "—",
            "long_memory_facts": "—", 
            "semantic_context": "—"
        }
        
        # 1. Краткосрочная память (всегда доступна)
        if self.short_term_window:
            recent_messages = []
            for msg in self.short_term_window[-5:]:  # Последние 5 сообщений
                role_label = "👤" if msg['role'] == 'user' else "🤖"
                recent_messages.append(f"{role_label} {msg['content']}")
            
            context["short_memory_summary"] = "Недавние сообщения:\n" + "\n".join(recent_messages)
            logger.info(f"✅ [UNIFIED-{self.user_id}] Краткосрочная память: {len(recent_messages)} сообщений")
        
        # 2. Долгосрочная память - ВСЕГДА пытаемся искать в векторной БД если есть запрос
        if self.vector_available and query:
            try:
                # Ищем релевантные факты в векторной БД
                search_results = self.vector_db.search_similar(query, similarity_threshold=0.0, max_results=8)
                
                if search_results:
                    facts = []
                    for result in search_results:
                        content = result.get('content', '') or result.get('document', '')
                        if content and len(content) > 10:
                            # Используем интеллектуальную фильтрацию вместо хардкода
                            if fact_extractor.should_store_in_long_term(content, "user"):
                                facts.append(f"• {content}")
                    
                    if facts:
                        context["long_memory_facts"] = "Важные факты из истории общения:\n" + "\n".join(facts[:5])
                        context["semantic_context"] = "Контекст поиска:\n" + "\n".join(facts[:3])
                        logger.info(f"✅ [UNIFIED-{self.user_id}] Долгосрочная память: {len(facts)} фактов")
                    else:
                        logger.info(f"⚠️ [UNIFIED-{self.user_id}] Векторная БД не содержит релевантных фактов")
                else:
                    logger.info(f"⚠️ [UNIFIED-{self.user_id}] Поиск в векторной БД не дал результатов")
                    
            except Exception as e:
                logger.error(f"❌ [UNIFIED-{self.user_id}] Ошибка поиска в векторной БД: {e}")
        
 
        if self.short_term_window:
            user_messages = [msg for msg in self.short_term_window if msg['role'] == 'user']
            if user_messages:
                recent_facts = []
                for msg in user_messages:
                    content = msg['content']
                    # Используем интеллектуальную систему вместо хардкода ключевых слов
                    if fact_extractor.should_store_in_long_term(content, "user"):
                        recent_facts.append(f"• {content}")
                
                if recent_facts:
                    # ИСПРАВЛЕНО: Объединяем вместо перезаписи
                    existing_facts = context.get("long_memory_facts", "")
                    recent_facts_text = "Факты из недавних сообщений:\n" + "\n".join(recent_facts)
                    
                    if existing_facts and existing_facts != "—":
                        # Объединяем: сначала новые факты, потом старые
                        context["long_memory_facts"] = f"{recent_facts_text}\n\nИз долгосрочной памяти:\n{existing_facts}"
                    else:
                        context["long_memory_facts"] = recent_facts_text
                    
                    # Семантический контекст остается из долгосрочной памяти (не перезаписываем)
                    logger.info(f"✅ [UNIFIED-{self.user_id}] ДОПОЛНИЛИ факты краткосрочной памятью: {len(recent_facts)}")
                    logger.info(f"🤝 [UNIFIED-{self.user_id}] Краткосрочная + долгосрочная память объединены")
        
        # 4. Логируем что возвращаем
        logger.info(f"📊 [UNIFIED-{self.user_id}] ВОЗВРАЩАЕМ:")
        logger.info(f"   Short: {len(context['short_memory_summary'])} символов")
        logger.info(f"   Facts: {len(context['long_memory_facts'])} символов") 
        logger.info(f"   Semantic: {len(context['semantic_context'])} символов")
        
        return context
    
    def get_last_activity_time(self) -> datetime:
        """
        Получает время ПРЕДЫДУЩЕЙ активности пользователя (не текущего сообщения)
        
        Returns:
            datetime объект времени предпоследнего сообщения пользователя
        """
        # Ищем сообщения пользователя в краткосрочной памяти
        user_messages = [msg for msg in self.short_term_window if msg['role'] == 'user']
        
        if len(user_messages) >= 2:
            # Берем ПРЕДПОСЛЕДНЕЕ сообщение (не текущее!)
            previous_message = user_messages[-2]
            timestamp_str = previous_message.get('timestamp')
            if timestamp_str:
                try:
                    time_obj = datetime.fromisoformat(timestamp_str)
                    logger.info(f"⏰ [UNIFIED-{self.user_id}] Найдено предыдущее сообщение: {time_obj}")
                    return time_obj
                except Exception as e:
                    logger.warning(f"⚠️ [UNIFIED-{self.user_id}] Ошибка парсинга времени: {e}")
        elif len(user_messages) == 1:
            # Только одно сообщение - это первый раз, используем очень старую дату
            logger.info(f"🆕 [UNIFIED-{self.user_id}] Первое сообщение пользователя")
            return datetime.utcnow() - timedelta(days=1)  # Имитируем что прошел день
        
        # Если не найдено в краткосрочной памяти, ищем в векторной БД
        if self.vector_available:
            try:
                # Получаем все сообщения пользователя из векторной БД
                results = self.vector_db.similarity_search(
                    query="user message", 
                    k=100,  # Большое количество для поиска последнего
                    filter={"role": "user"}
                )
                
                if results:
                    # Ищем самое свежее сообщение
                    latest_time = None
                    for doc in results:
                        metadata = doc.metadata
                        timestamp_str = metadata.get('timestamp')
                        if timestamp_str:
                            try:
                                msg_time = datetime.fromisoformat(timestamp_str)
                                if latest_time is None or msg_time > latest_time:
                                    latest_time = msg_time
                            except:
                                continue
                    
                    if latest_time:
                        return latest_time
            except Exception as e:
                logger.warning(f"⚠️ [UNIFIED-{self.user_id}] Ошибка получения времени из векторной БД: {e}")
        
        # Fallback - возвращаем время создания менеджера (приблизительно)
        return datetime.utcnow()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Получает статистику памяти для отладки"""
        return {
            "user_id": self.user_id,
            "total_messages": self.message_count,
            "short_term_count": len(self.short_term_window),
            "window_size": self.window_size,
            "vector_available": self.vector_available,
            "should_use_vector": self.message_count > self.window_size,
            "messages_in_vector": max(0, self.message_count - self.window_size)
        }
    
    def clear_memory(self) -> bool:
        """Очищает всю память"""
        try:
            self.short_term_window.clear()
            self.message_count = 0
            
            if self.vector_available:
                # Здесь можно добавить очистку векторной БД если нужно
                pass
            
            logger.info(f"🧹 [UNIFIED-{self.user_id}] Память очищена")
            return True
        except Exception as e:
            logger.error(f"❌ [UNIFIED-{self.user_id}] Ошибка очистки памяти: {e}")
            return False
