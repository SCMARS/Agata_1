"""
Тесты для EnhancedBufferMemory
Проверяет интеграцию с существующей архитектурой, эмоции и суммаризацию
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Импорт тестируемого модуля
import sys
sys.path.append(str(__file__).rsplit('/', 2)[0])

from app.memory.enhanced_buffer_memory import (
    EnhancedBufferMemory, 
    EnhancedMessage, 
    EmotionTag, 
    BehaviorTag,
    SummaryEntry
)
from app.memory.base import Message, MemoryContext


class TestEnhancedMessage:
    """Тесты для EnhancedMessage"""
    
    def test_enhanced_message_creation(self):
        """Тест создания расширенного сообщения"""
        now = datetime.now()
        msg = EnhancedMessage(
            role="user",
            content="Я очень рад нашему знакомству!",
            timestamp=now,
            emotion_tag=EmotionTag.EXCITED,
            behavior_tag=BehaviorTag.FRIENDLY,
            importance_score=0.8
        )
        
        assert msg.role == "user"
        assert msg.content == "Я очень рад нашему знакомству!"
        assert msg.emotion_tag == EmotionTag.EXCITED
        assert msg.behavior_tag == BehaviorTag.FRIENDLY
        assert msg.importance_score == 0.8
    
    def test_enhanced_message_serialization(self):
        """Тест сериализации расширенного сообщения"""
        now = datetime.now()
        msg = EnhancedMessage(
            role="assistant",
            content="Я тоже рада!",
            timestamp=now,
            emotion_tag=EmotionTag.HAPPY,
            importance_score=0.7
        )
        
        data = msg.to_dict()
        assert data['role'] == 'assistant'
        assert data['emotion_tag'] == 'happy'
        assert data['importance_score'] == 0.7
        
        restored = EnhancedMessage.from_dict(data)
        assert restored.role == msg.role
        assert restored.emotion_tag == msg.emotion_tag
        assert restored.importance_score == msg.importance_score


class TestEnhancedBufferMemory:
    """Тесты для EnhancedBufferMemory"""
    
    @pytest.fixture
    def memory(self):
        """Создает экземпляр памяти для тестов"""
        return EnhancedBufferMemory(user_id="test_user", max_messages=5)
    
    @pytest.fixture
    def sample_context(self):
        """Создает тестовый контекст"""
        return MemoryContext(user_id="test_user", day_number=1)
    
    def test_memory_initialization(self, memory):
        """Тест инициализации памяти"""
        assert memory.user_id == "test_user"
        assert memory.max_messages == 5
        assert len(memory.messages) == 0
        assert len(memory.summary_memory) == 0
        assert memory.total_messages == 0
    
    def test_add_regular_message(self, memory, sample_context):
        """Тест добавления обычного сообщения"""
        message = Message(
            role="user",
            content="Привет! Как дела?",
            timestamp=datetime.now()
        )
        
        memory.add_message(message, sample_context)
        
        assert len(memory.messages) == 1
        assert memory.total_messages == 1
        assert memory.metrics['messages_added'] == 1
        
        # Проверяем что сообщение было расширено
        enhanced_msg = memory.messages[0]
        assert isinstance(enhanced_msg, EnhancedMessage)
        assert enhanced_msg.emotion_tag is not None
        assert enhanced_msg.importance_score > 0
    
    def test_add_enhanced_message(self, memory, sample_context):
        """Тест добавления уже расширенного сообщения"""
        enhanced_msg = EnhancedMessage(
            role="user",
            content="Мне грустно сегодня",
            timestamp=datetime.now(),
            emotion_tag=EmotionTag.SAD,
            importance_score=0.8
        )
        
        memory.add_message(enhanced_msg, sample_context)
        
        assert len(memory.messages) == 1
        stored_msg = memory.messages[0]
        assert stored_msg.emotion_tag == EmotionTag.SAD
        assert stored_msg.importance_score == 0.8
    
    def test_emotion_detection(self, memory, sample_context):
        """Тест автоматического определения эмоций"""
        test_cases = [
            ("Спасибо большое! 😊", EmotionTag.HAPPY),
            ("Ура! Получилось! 🎉", EmotionTag.EXCITED),
            ("Мне очень грустно 😢", EmotionTag.SAD),
            ("Я беспокоюсь о работе", EmotionTag.WORRIED),
            ("Не понимаю, что происходит", EmotionTag.CONFUSED),
            ("Это меня раздражает!", EmotionTag.FRUSTRATED),
            ("Обычное сообщение", EmotionTag.NEUTRAL)
        ]
        
        for text, expected_emotion in test_cases:
            message = Message(role="user", content=text, timestamp=datetime.now())
            memory.add_message(message, sample_context)
            
            last_msg = memory.messages[-1]
            assert last_msg.emotion_tag == expected_emotion, f"Failed for: {text}"
        
        # Проверяем метрику обнаружения эмоций
        assert memory.metrics['emotions_detected'] > 0
    
    def test_importance_calculation(self, memory, sample_context):
        """Тест расчета важности сообщений"""
        # Высокая важность
        important_msg = Message(
            role="user", 
            content="Это очень важно! Меня зовут Алексей и я работаю программистом",
            timestamp=datetime.now()
        )
        memory.add_message(important_msg, sample_context)
        high_importance = memory.messages[-1].importance_score
        
        # Низкая важность
        simple_msg = Message(role="user", content="Привет", timestamp=datetime.now())
        memory.add_message(simple_msg, sample_context)
        low_importance = memory.messages[-1].importance_score
        
        assert high_importance > low_importance
        assert high_importance > 0.7
        assert low_importance < 0.6
    
    def test_buffer_size_limit(self, memory, sample_context):
        """Тест ограничения размера буфера"""
        # Добавляем больше сообщений чем лимит
        for i in range(7):
            message = Message(
                role="user",
                content=f"Сообщение {i}",
                timestamp=datetime.now()
            )
            memory.add_message(message, sample_context)
        
        # Проверяем что буфер не превышает лимит
        assert len(memory.messages) == memory.max_messages
        assert memory.total_messages == 7  # Общий счетчик не сбрасывается
        
        # Проверяем что остались последние сообщения
        assert "Сообщение 6" in memory.messages[-1].content
    
    def test_context_generation(self, memory, sample_context):
        """Тест генерации контекста"""
        # Добавляем сообщения с разными эмоциями
        messages = [
            ("Привет! Меня зовут Анна", EmotionTag.HAPPY),
            ("Я работаю дизайнером", EmotionTag.NEUTRAL),
            ("Сегодня у меня отличное настроение!", EmotionTag.EXCITED)
        ]
        
        for content, emotion in messages:
            enhanced_msg = EnhancedMessage(
                role="user",
                content=content,
                timestamp=datetime.now(),
                emotion_tag=emotion,
                importance_score=0.7
            )
            memory.add_message(enhanced_msg, sample_context)
        
        context = memory.get_context(sample_context)
        
        # Проверяем что контекст содержит ключевую информацию
        assert "Анна" in context or "Имя: Анна" in context
        assert "дизайнер" in context or "Профессия: дизайнер" in context
        assert "Недавний разговор:" in context
        assert "excited" in context or "happy" in context  # Эмоции
        assert "Рекомендуемое поведение:" in context  # Поведение
        
        # Проверяем метрику
        assert memory.metrics['context_requests'] > 0
    
    def test_dominant_emotion_detection(self, memory, sample_context):
        """Тест определения доминирующей эмоции"""
        # Добавляем сообщения с разными эмоциями, но больше счастливых
        emotions = [EmotionTag.HAPPY, EmotionTag.HAPPY, EmotionTag.SAD, EmotionTag.EXCITED]
        
        for i, emotion in enumerate(emotions):
            enhanced_msg = EnhancedMessage(
                role="user",
                content=f"Сообщение {i}",
                timestamp=datetime.now(),
                emotion_tag=emotion
            )
            memory.add_message(enhanced_msg, sample_context)
        
        dominant = memory._get_dominant_emotion()
        # Должна быть HAPPY или EXCITED (больше позитивных)
        assert dominant in [EmotionTag.HAPPY, EmotionTag.EXCITED]
    
    def test_behavior_determination(self, memory, sample_context):
        """Тест определения поведения"""
        # Грустное сообщение должно вызвать поддерживающее поведение
        sad_msg = EnhancedMessage(
            role="user",
            content="Мне очень плохо",
            timestamp=datetime.now(),
            emotion_tag=EmotionTag.SAD
        )
        memory.add_message(sad_msg, sample_context)
        
        behavior = memory._determine_current_behavior(EmotionTag.SAD)
        assert behavior == BehaviorTag.SUPPORTIVE
        
        # Счастливое сообщение должно вызвать игривое поведение
        behavior = memory._determine_current_behavior(EmotionTag.HAPPY)
        assert behavior == BehaviorTag.PLAYFUL
    
    def test_key_information_extraction(self, memory, sample_context):
        """Тест извлечения ключевой информации"""
        # Добавляем сообщения с персональными данными
        personal_messages = [
            "Привет! Меня зовут Мария",
            "Мне 25 лет",
            "Я работаю учителем в школе"
        ]
        
        for content in personal_messages:
            message = Message(role="user", content=content, timestamp=datetime.now())
            memory.add_message(message, sample_context)
        
        key_info = memory._extract_key_information()
        
        assert "Мария" in key_info or "Имя: Мария" in key_info
        assert "25" in key_info or "Возраст: 25" in key_info
        assert "учитель" in key_info or "Профессия: учитель" in key_info
    
    def test_topic_extraction(self, memory, sample_context):
        """Тест извлечения тем"""
        topic_messages = [
            "Я работаю в офисе программистом",
            "У меня есть семья и дети",
            "Люблю путешествовать по миру"
        ]
        
        enhanced_messages = []
        for content in topic_messages:
            enhanced_msg = EnhancedMessage(
                role="user",
                content=content,
                timestamp=datetime.now()
            )
            enhanced_messages.append(enhanced_msg)
        
        topics = memory._extract_topics(enhanced_messages)
        
        assert 'работа' in topics
        assert 'семья' in topics
        assert 'путешествия' in topics
    
    def test_memory_search(self, memory, sample_context):
        """Тест поиска в памяти"""
        # Добавляем сообщения
        messages = [
            "Я люблю программирование",
            "Python очень интересный язык",
            "Работаю в IT компании"
        ]
        
        for content in messages:
            message = Message(role="user", content=content, timestamp=datetime.now())
            memory.add_message(message, sample_context)
        
        # Поиск по запросу
        results = memory.search_memory("программирование", limit=5)
        
        assert len(results) > 0
        assert any("программирование" in result["content"].lower() for result in results)
        assert all("relevance" in result for result in results)
    
    def test_conversation_summarization(self, memory, sample_context):
        """Тест суммаризации диалога"""
        # Добавляем несколько сообщений
        messages = [
            Message(role="user", content="Привет! Как дела?", timestamp=datetime.now()),
            Message(role="assistant", content="Привет! У меня все отлично!", timestamp=datetime.now()),
            Message(role="user", content="Расскажи о себе", timestamp=datetime.now()),
            Message(role="assistant", content="Я AI-ассистент Агата", timestamp=datetime.now())
        ]
        
        summary = memory.summarize_conversation(messages)
        
        assert "4 сообщений" in summary
        assert "2 сообщений" in summary  # Пользователь написал 2
        assert "2 раз" in summary  # Ассистент ответил 2 раза
    
    @pytest.mark.asyncio
    async def test_summarization_trigger(self):
        """Тест триггера суммаризации (мок)"""
        memory = EnhancedBufferMemory(user_id="test_user", max_messages=3)
        context = MemoryContext(user_id="test_user")
        
        # Мокаем LLM
        with patch.object(memory, '_trigger_summarization', new_callable=AsyncMock) as mock_summarize:
            # Добавляем сообщения до триггера
            memory.add_message(Message(role="user", content="Сообщение 1", timestamp=datetime.now()), context)
            memory.add_message(Message(role="assistant", content="Ответ 1", timestamp=datetime.now()), context)
            
            # Это сообщение должно вызвать суммаризацию
            memory.add_message(Message(role="user", content="Сообщение 2", timestamp=datetime.now()), context)
            
            # Ждем завершения asyncio задач
            await asyncio.sleep(0.1)
    
    def test_memory_clearing(self, memory, sample_context):
        """Тест очистки памяти"""
        # Добавляем сообщения
        for i in range(3):
            message = Message(role="user", content=f"Сообщение {i}", timestamp=datetime.now())
            memory.add_message(message, sample_context)
        
        # Добавляем суммарную память
        summary = SummaryEntry(
            summary_text="Тестовое резюме",
            last_updated=datetime.now(),
            original_messages_count=2
        )
        memory.summary_memory.append(summary)
        
        # Очищаем
        memory.clear_memory()
        
        assert len(memory.messages) == 0
        assert len(memory.summary_memory) == 0
        assert memory.total_messages == 0
    
    def test_data_export_import(self, memory, sample_context):
        """Тест экспорта и импорта данных"""
        # Добавляем тестовые данные
        enhanced_msg = EnhancedMessage(
            role="user",
            content="Тестовое сообщение",
            timestamp=datetime.now(),
            emotion_tag=EmotionTag.HAPPY,
            importance_score=0.8
        )
        memory.add_message(enhanced_msg, sample_context)
        
        summary = SummaryEntry(
            summary_text="Тестовое резюме",
            last_updated=datetime.now(),
            original_messages_count=1,
            topics=['тест']
        )
        memory.summary_memory.append(summary)
        
        # Экспорт
        exported_data = memory.export_data()
        
        assert exported_data['user_id'] == "test_user"
        assert len(exported_data['messages']) == 1
        assert len(exported_data['summary_memory']) == 1
        
        # Импорт в новую память
        new_memory = EnhancedBufferMemory(user_id="test_user")
        assert new_memory.import_data(exported_data) is True
        
        # Проверяем восстановленные данные
        assert len(new_memory.messages) == 1
        assert len(new_memory.summary_memory) == 1
        assert new_memory.messages[0].emotion_tag == EmotionTag.HAPPY
        assert new_memory.summary_memory[0].summary_text == "Тестовое резюме"
    
    def test_metrics_collection(self, memory, sample_context):
        """Тест сбора метрик"""
        # Генерируем активность
        happy_msg = EnhancedMessage(
            role="user",
            content="Я рад! 😊",
            timestamp=datetime.now(),
            emotion_tag=EmotionTag.HAPPY
        )
        memory.add_message(happy_msg, sample_context)
        memory.get_context(sample_context)
        
        metrics = memory.get_metrics()
        
        assert metrics['messages_added'] == 1
        assert metrics['emotions_detected'] == 1
        assert metrics['context_requests'] == 1
        assert metrics['current_buffer_size'] == 1
        assert metrics['dominant_emotion'] == 'happy'
        assert 'config' in metrics
    
    def test_compatibility_with_base_interface(self, memory, sample_context):
        """Тест совместимости с базовым интерфейсом MemoryAdapter"""
        # Проверяем что все методы базового интерфейса работают
        
        # add_message
        message = Message(role="user", content="Тест", timestamp=datetime.now())
        memory.add_message(message, sample_context)
        
        # get_context
        context = memory.get_context(sample_context)
        assert isinstance(context, str)
        assert len(context) > 0
        
        # search_memory
        results = memory.search_memory("тест")
        assert isinstance(results, list)
        
        # summarize_conversation
        summary = memory.summarize_conversation([message])
        assert isinstance(summary, str)
        
        # clear_memory
        memory.clear_memory()
        assert len(memory.messages) == 0


class TestSummaryEntry:
    """Тесты для SummaryEntry"""
    
    def test_summary_creation(self):
        """Тест создания суммарной записи"""
        now = datetime.now()
        summary = SummaryEntry(
            summary_text="Пользователь говорил о работе",
            last_updated=now,
            original_messages_count=3,
            importance_score=0.7,
            topics=['работа'],
            emotions=['excited']
        )
        
        assert summary.summary_text == "Пользователь говорил о работе"
        assert summary.original_messages_count == 3
        assert summary.importance_score == 0.7
        assert 'работа' in summary.topics
        assert 'excited' in summary.emotions
    
    def test_summary_serialization(self):
        """Тест сериализации суммарной записи"""
        now = datetime.now()
        summary = SummaryEntry(
            summary_text="Краткое резюме",
            last_updated=now,
            original_messages_count=2
        )
        
        data = summary.to_dict()
        
        assert data['summary_text'] == "Краткое резюме"
        assert data['original_messages_count'] == 2
        assert data['last_updated'] == now.isoformat()


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])
