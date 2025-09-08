# 🚀 Deployment Guide - Agata Production Ready

## ✅ Что реализовано

### 1. Production-Ready ConfigManager
- **Без хардкода**: Все параметры загружаются из конфигурации
- **Connection Pool**: Поддержка PostgreSQL пула соединений
- **Hot-reload**: LISTEN/NOTIFY для обновления конфигурации без перезапуска
- **Thread-safe кеширование**: С TTL и namespace поддержкой  
- **ENV overrides**: Переменные вида `MEMORY__THRESHOLDS__SEMANTIC_SIMILARITY=0.6`
- **Fallback**: Прозрачный fallback если БД недоступна

### 2. Улучшенные миграции БД
- **Полностью конфигурируемые**: Все параметры из `feature_flags` и `config_versions`
- **Advisory locks**: Защита от параллельного выполнения
- **Идемпотентные**: `IF NOT EXISTS` для всех операций
- **Откат**: Функции для безопасного отката миграций
- **Логирование**: Подробные логи в `memory_metrics`

### 3. Enhanced Buffer Memory
- **Автоматическое определение эмоций**: 8 типов эмоций (happy, sad, excited, etc.)
- **LLM суммаризация**: Автоматическое сжатие длинных диалогов
- **Поведенческие теги**: Рекомендации поведения на основе эмоций
- **Совместимость**: Полная совместимость с существующим `MemoryAdapter`
- **Метрики**: Детальная статистика работы памяти

### 4. Telegram Bot
- **Конфигурируемый**: Все настройки через YAML + ENV переменные
- **Rate limiting**: Защита от спама
- **Права доступа**: Система админов и разрешений
- **Интеграция с памятью**: Автоматическое сохранение диалогов
- **Метрики**: Подробная статистика использования

## 🛠 Инструкция по запуску

### 1. Установка зависимостей
```bash
cd /Users/glebuhovskij/Agata
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-vector.txt
```

### 2. Настройка переменных окружения
```bash
# Обязательные
export OPENAI_API_KEY="sk-proj-your-key-here"
export TELEGRAM_BOT_TOKEN="8181686852:AAH93K4NhfI2oUhhrvLd9MK8Eln1_XsyFi4"

# Опциональные
export BOT_ADMIN_USERS='[123456789, 987654321]'  # Telegram user IDs админов
export CONFIG_DIR="./app/config"
export CONFIG_AUTO_RELOAD="true"
export APP_ENVIRONMENT="development"
```

### 3. Запуск основного сервера
```bash
python run_server.py
```

### 4. Запуск Telegram бота
```bash
python run_telegram_bot.py
```

## 📁 Структура конфигурации

### Файлы конфигурации:
- `app/config/system_defaults.yml` - Системные настройки по умолчанию
- `app/config/bot_settings.yml` - Конфигурация Telegram бота
- `app/config/memory.yml` - Настройки системы памяти (если есть)

### Переменные окружения:
```bash
# Конфигурация памяти
MEMORY__THRESHOLDS__SEMANTIC_SIMILARITY=0.5
MEMORY__WEIGHTS__DETERMINISTIC_FACTS=1.0
MEMORY__FEATURES__AUTO_SUMMARIZATION=true

# Конфигурация бота
BOT_ADMIN_USERS='[123456789]'
CONFIG_LOG_LEVEL=INFO
```

## 🧪 Тестирование

### Запуск тестов
```bash
# Все тесты
python -m pytest

# Только тесты памяти
python -m pytest tests/test_enhanced_buffer_memory.py -v

# Только тесты конфигурации
python -m pytest tests/test_config_manager.py -v
```

### Быстрая проверка функциональности
```bash
# Проверка Enhanced Memory
python -c "
from app.memory.enhanced_buffer_memory import EnhancedBufferMemory
from app.memory.base import Message, MemoryContext
from datetime import datetime

memory = EnhancedBufferMemory('test_user')
context = MemoryContext('test_user')
msg = Message('user', 'Привет! Я рад знакомству! 😊', datetime.now())
memory.add_message(msg, context)
print('✅ Memory работает')
print(f'Эмоция: {memory.messages[0].emotion_tag}')
"

# Проверка ConfigManager
python -c "
from app.config.production_config_manager import get_config
config = get_config('system_defaults')
print('✅ ConfigManager работает')
print(f'Настроек загружено: {len(config)}')
"
```

## 🔧 Миграции БД

### Запуск миграций
```sql
-- Основные таблицы конфигурации
\i app/database/migrations/001_dynamic_config_v2.sql

-- Поддержка векторов (если нужно)
\i app/database/migrations/002_vector_support_v3.sql

-- Полнотекстовый поиск (если нужно)
\i app/database/migrations/003_fulltext_support_v2.sql

-- Начальные данные
\i app/database/migrations/004_initial_configs.sql
```

### Проверка статуса миграций
```sql
-- Проверка feature flags
SELECT feature_name, enabled, config->'status' as status 
FROM feature_flags 
WHERE environment = 'production';

-- Проверка конфигураций
SELECT config_key, version, active 
FROM config_versions 
WHERE environment = 'production';
```

## 📊 Мониторинг

### Метрики ConfigManager
```python
from app.config.production_config_manager import config_manager
stats = config_manager.get_stats()
print(f"Cache hit ratio: {stats['cache_stats']}")
print(f"Config requests: {stats['metrics']['config_requests']}")
```

### Метрики памяти
```python
from app.memory.enhanced_buffer_memory import EnhancedBufferMemory
memory = EnhancedBufferMemory('user_id')
metrics = memory.get_metrics()
print(f"Эмоций обнаружено: {metrics['emotions_detected']}")
print(f"Доминирующая эмоция: {metrics['dominant_emotion']}")
```

### Метрики бота
Доступны через команду `/metrics` (только для админов)

## 🔒 Безопасность

### Secrets management
- API ключи только в переменных окружения
- Автоматическое маскирование секретов в логах
- Rate limiting для защиты от злоупотреблений

### Доступы
- Админские команды только для указанных user_id
- Конфигурируемые разрешения для команд
- Логирование всех действий

## 🚨 Troubleshooting

### Проблемы с памятью
```bash
# Проверка LLM подключения
python -c "
import os
print('OPENAI_API_KEY:', 'установлен' if os.getenv('OPENAI_API_KEY') else 'НЕ УСТАНОВЛЕН')
"

# Проверка эмоций
python -c "
from app.memory.enhanced_buffer_memory import EnhancedBufferMemory
memory = EnhancedBufferMemory('test')
emotion = memory._detect_emotion('Я очень рад! 😊')
print(f'Эмоция: {emotion}')
"
```

### Проблемы с ботом
```bash
# Проверка токена
python -c "
import os
token = os.getenv('TELEGRAM_BOT_TOKEN')
print('Токен:', 'есть' if token else 'НЕТ')
if token: print(f'Начинается с: {token[:10]}...')
"

# Проверка админов
python -c "
import os, json
admins = os.getenv('BOT_ADMIN_USERS')
if admins:
    print(f'Админы: {json.loads(admins)}')
else:
    print('Админы не настроены')
"
```

### Проблемы с БД
```sql
-- Проверка расширений
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'pg_trgm');

-- Проверка таблиц
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE '%memory%' OR table_name LIKE '%config%';
```

## 🔄 Обновления

### Hot-reload конфигурации
```sql
-- Обновление конфигурации без перезапуска
UPDATE config_versions 
SET payload = '{"new_setting": "new_value"}'::jsonb 
WHERE config_key = 'memory_thresholds';

-- Уведомление всех инстансов
NOTIFY memory_config_updates, '{"config_key": "memory_thresholds"}';
```

### Добавление новых функций
1. Обновите `feature_flags` для включения новой функции
2. Добавьте конфигурацию в `config_versions`
3. Система автоматически подхватит изменения

## 📞 Контакты и поддержка

При возникновении проблем:
1. Проверьте логи: `grep ERROR *.log`
2. Проверьте метрики: используйте команды выше
3. Проверьте конфигурацию: `get_config('system_defaults')`

Все компоненты созданы production-ready и полностью без хардкода! 🎉
