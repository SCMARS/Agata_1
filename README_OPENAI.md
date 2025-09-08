# 🔑 Получение OpenAI API ключа для Agatha

## 📋 Пошаговая инструкция:

### 1. Зарегистрируйтесь на OpenAI
- Перейдите на https://platform.openai.com/
- Нажмите "Sign up" и создайте аккаунт

### 2. Получите API ключ
- Войдите в аккаунт
- Перейдите в раздел "API Keys": https://platform.openai.com/api-keys
- Нажмите "Create new secret key"
- Скопируйте сгенерированный ключ

### 3. Добавьте ключ в config.env
```bash
# Откройте файл config.env
nano config.env

# Замените строку:
OPENAI_API_KEY=sk-REDACTED

# На ваш реальный ключ:
OPENAI_API_KEY=sk-REDACTED
```

### 4. Проверьте работу
```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите тест
python3 -c "
from app.memory.vector_memory import VectorMemory
from app.memory.base import Message, MemoryContext
from datetime import datetime
import asyncio

async def test():
    memory = VectorMemory('test_user')
    message = Message('user', 'Меня зовут Иван', datetime.utcnow())
    context = MemoryContext(user_id='test_user', day_number=1)
    await memory.add_message(message, context)

asyncio.run(test())
"
```
