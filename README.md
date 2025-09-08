# 🤖 Agatha — AI-компаньон с памятью

AI-компаньон с LangGraph, который помнит контекст и адаптируется под пользователя.

## 🚀 Быстрый запуск

### 1. Установка

```bash
git clone <repo-url>
cd Agata

# Создайте виртуальное окружение
python3 -m venv venv

# ОБЯЗАТЕЛЬНО активируйте его
source venv/bin/activate  # Linux/Mac
# или .\\venv\\Scripts\\activate  # Windows

# Установите зависимости
pip install -r requirements.txt
```

### 2. API ключи

Получите ключи:
- OpenAI: https://platform.openai.com/api-keys
- Telegram: @BotFather в Telegram

### 3. Настройка

Создайте `config.env`:
```bash
OPENAI_API_KEY=sk-proj-ваш-ключ-здесь
TELEGRAM_BOT_TOKEN=ваш-токен-здесь
HOST=0.0.0.0
PORT=8000
API_PORT=8000
LLM_MODEL=gpt-4o-mini
```

### 4. Запуск проекта

**ПЕРВЫЙ ЗАПУСК (только один раз):**
```bash
cd Agata
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**КАЖДЫЙ ПОСЛЕДУЮЩИЙ ЗАПУСК:**
```bash
cd Agata
source venv/bin/activate

# Терминал 1 - запустить API сервер ПЕРВЫМ
python3 run_server.py

# Терминал 2 - запустить Telegram бота ВТОРЫМ  
python3 run_telegram_bot.py
```

**Простые скрипты (после первой настройки):**
```bash
./start_api.sh    # Запуск API
./start_bot.sh    # Запуск бота
```

## ✅ Проверка

```bash
# Проверить API
curl http://localhost:8001/healthz

# Тест чата
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","messages":[{"role":"user","content":"Привет"}]}'
```

## 🔧 Что умеет

- Помнит ваше имя и предыдущие разговоры
- 5 стратегий поведения (от загадочной до поддерживающей)
- Этапы развития отношений (знакомство → развитие → углубление)
- Реагирует на перерывы в общении
- Telegram бот + REST API

## 🐛 Проблемы

**ModuleNotFoundError: No module named 'flask'**
```bash
# НЕ создавайте новое venv! Активируйте существующее:
source venv/bin/activate
# Если зависимости не установлены:
pip install -r requirements.txt
```

**Telegram бот показывает "All connection attempts failed":**
```bash
# 1. Остановите процесс на порту 8000:
lsof -ti:8000 | xargs kill -9

# 2. Запустите API сервер:
source venv/bin/activate
python3 run_server.py

# 3. Проверьте что API работает:
curl http://localhost:8000/healthz

# 4. Если работает, Telegram бот автоматически подключится
```

**Порт занят:**
```bash
lsof -ti:8000 | xargs kill -9
```

**Нет ключей:**
```bash
export OPENAI_API_KEY="sk-proj-ваш-ключ"
export TELEGRAM_BOT_TOKEN="ваш-токен"
```

**Бот не подключается к API:**
```bash
# Проверьте что API работает на 8000
curl http://localhost:8000/healthz
```

## 📁 Структура

```
app/
├── api/main.py          # Flask API
├── bots/telegram_bot.py # Telegram бот
├── graph/pipeline.py    # LangGraph пайплайн
├── memory/              # Система памяти
└── utils/               # Поведенческий анализ

agata_prompt_data/       # Личность Агаты
config.env              # Переменные окружения
```

Всё. Запускайте и пользуйтесь! 🚀