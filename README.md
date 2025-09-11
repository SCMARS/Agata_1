# 🤖 Agatha — AI-компаньон с памятью

AI-компаньон с LangGraph, который помнит контекст и адаптируется под пользователя.

## 🚀 Быстрый запуск

### Вариант 1: Автоматический запуск (РЕКОМЕНДУЕТСЯ)

**Один скрипт запускает всё:**
```bash
./start_local.sh
```

**Остановка:**
```bash
./stop_all.sh
```

### Вариант 2: Полная система с Docker

**Запуск всей системы включая базу данных:**
```bash
./start_all.sh
```

**Остановка:**
```bash
./stop_all.sh
```

### Вариант 3: Ручной запуск

**1. Установка (только первый раз):**
```bash
# Создайте виртуальное окружение
python3 -m venv venv

# Активируйте его
source venv/bin/activate  # Linux/Mac
# или .\\venv\\Scripts\\activate  # Windows

# Установите зависимости
pip install -r requirements.txt
```

**2. Настройка API ключей:**

Получите ключи:
- OpenAI: https://platform.openai.com/api-keys
- Telegram: @BotFather в Telegram

Настройте `config.env` (уже настроен):
```bash
OPENAI_API_KEY=sk-proj-ваш-ключ-здесь
TELEGRAM_BOT_TOKEN=ваш-токен-здесь
HOST=0.0.0.0
PORT=8000
LLM_MODEL=gpt-4o-mini
```

**3. Запуск:**
```bash
# Терминал 1 - API сервер
source venv/bin/activate
python run_server.py

# Терминал 2 - Telegram бот
source venv/bin/activate
python simple_telegram_bot.py
```

## ✅ Проверка работы

**Проверка API:**
```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

**Тест чата:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","messages":[{"role":"user","content":"Привет"}]}'
```

**Проверка логов:**
```bash
tail -f api.log    # Логи API сервера
tail -f bot.log    # Логи Telegram бота
```

## 🔧 Что умеет

- **💭 Память:** Помнит ваше имя и предыдущие разговоры
- **🎭 Поведение:** 5 стратегий поведения (от загадочной до поддерживающей)
- **📈 Стейджи:** Этапы развития отношений (знакомство → дружба → близость)
- **⏰ Время:** Реагирует на перерывы в общении и время дня
- **💬 Живое общение:** Короткие сообщения как в реальном Telegram
- **🧠 Контекст:** Собирает разбитые сообщения в единый контекст
- **😊 Эмоции:** Показывает характер и эмоции через общение
- **🔄 Адаптация:** Подстраивается под стиль общения пользователя
- **🤖 Интерфейсы:** Telegram бот + REST API

## 🛠️ Скрипты управления

| Скрипт | Описание |
|--------|----------|
| `./start_local.sh` | 🚀 **Быстрый запуск** - API + бот (без Docker) |
| `./start_all.sh` | 🐳 **Полный запуск** - API + бот + база данных (Docker) |
| `./stop_all.sh` | 🛑 **Остановка** - все процессы |
| `./stop_all.sh --force` | ⚡ **Принудительная остановка** |

## 🐛 Решение проблем

**API не запускается:**
```bash
# Проверьте порт
lsof -ti:8000 | xargs kill -9

# Перезапустите
./start_local.sh
```

**Telegram бот не подключается:**
```bash
# Проверьте API
curl http://localhost:8000/healthz

# Проверьте логи бота
tail -f bot.log
```

**Ошибки зависимостей:**
```bash
# Переустановите зависимости
source venv/bin/activate
pip install -r requirements.txt
```

**Проблемы с Docker:**
```bash
# Запустите Docker Desktop
# Или используйте локальный режим:
./start_local.sh
```

**Очистка системы:**
```bash
# Остановить всё
./stop_all.sh --force

# Очистить логи
rm -f api.log bot.log api.pid bot.pid
```

## 💬 Примеры использования

**Через API:**
```bash
# Простое сообщение
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","messages":[{"role":"user","content":"Привет! Меня зовут Анна"}]}'

# Диалог с контекстом
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id":"user123",
    "messages":[
      {"role":"user","content":"Привет! Меня зовут Анна"},
      {"role":"assistant","content":"Привет, Анна! Рада познакомиться."},
      {"role":"user","content":"Как дела?"}
    ]
  }'
```

**Через Telegram:**
1. Найдите бота в Telegram по токену
2. Напишите `/start`
3. Общайтесь с Агатой!

**Особенности живого общения:**
- Можете писать несколько коротких сообщений подряд - Агата их объединит
- Она отвечает короткими частями с эмодзи, как живой человек
- Реагирует на время дня и длительность пауз
- Следует стейджам знакомства и задает релевантные вопросы

## 📁 Структура проекта

```
Agata_1-2/
├── 🚀 start_local.sh      # Быстрый запуск (API + бот)
├── 🐳 start_all.sh        # Полный запуск (с Docker)
├── 🛑 stop_all.sh         # Остановка системы
├── 📝 config.env          # Настройки и API ключи
├── 📋 requirements.txt    # Python зависимости
├── 🐳 docker-compose.yml  # Docker конфигурация
│
├── app/                   # Основной код
│   ├── api/main.py        # Flask API сервер
│   ├── bots/telegram_bot.py # Telegram бот
│   ├── graph/pipeline.py  # LangGraph пайплайн
│   ├── memory/            # Система памяти
│   └── utils/             # Утилиты
│
├── agata_prompt_data/     # Личность Агаты
└── venv/                  # Виртуальное окружение
```

## 🎯 Быстрый старт (30 секунд)

```bash
# 1. Клонируйте репозиторий
git clone <repo-url>
cd Agata_1-2

# 2. Запустите всё одной командой
./start_local.sh

# 3. Готово! Система работает
# API: http://localhost:8000
# Telegram бот: активен
```

**Всё. Запускайте и пользуйтесь! 🚀**