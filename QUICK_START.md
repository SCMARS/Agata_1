# 🚀 БЫСТРЫЙ ЗАПУСК AGATHA

## Один командный запуск всей системы

### Для Linux/Mac:
```bash
./start.sh
```

### Для Windows:
```cmd
start.bat
```

### Для Python (универсально):
```bash
python3 start_agatha.py
```

## Что запускается автоматически:

1. **API Сервер** на `http://localhost:8000`
   - Основной API для общения с Agatha
   - Система памяти (краткосрочная и долгосрочная)
   - Интеграция с OpenAI GPT

2. **Telegram Bot** 
   - Интерфейс для общения через Telegram
   - Автоматическое сохранение в память
   - Контекстные ответы

3. **Система мониторинга**
   - Автоматическое тестирование компонентов
   - Вывод статуса системы
   - Логирование ошибок

## Требования:

- Python 3.8+
- Виртуальное окружение в папке `venv/`
- Файл `config.env` с переменными:
  - `OPENAI_API_KEY=your_key_here`
  - `TELEGRAM_BOT_TOKEN=your_token_here`

## После запуска:

✅ **API доступен:** http://localhost:8000  
✅ **Telegram Bot:** https://t.me/YOUR_BOT_USERNAME  
✅ **Документация:** http://localhost:8000/api/info  

## Остановка системы:

Нажмите `Ctrl+C` - все процессы остановятся автоматически.

## Endpoints:

- `POST /api/chat` - общение с Agatha
- `POST /api/memory/<user_id>/add` - добавить в память  
- `POST /api/memory/<user_id>/search` - поиск в памяти
- `GET /api/memory/<user_id>/overview` - обзор памяти
- `POST /api/memory/<user_id>/clear` - очистить память

## Troubleshooting:

### Если что-то не работает:
1. Проверьте `config.env` - все ли переменные заданы
2. Убедитесь что виртуальное окружение активно
3. Установите зависимости: `pip install -r requirements.txt`
4. Проверьте логи в консоли

### Если порт 8000 занят:
Измените `PORT=8000` в `config.env` на другой порт.

---

**💡 Совет:** После запуска напишите любое сообщение в Telegram bot - Agatha ответит с полным контекстом и памятью!
