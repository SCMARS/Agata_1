#!/bin/bash

# Тест для проверки задавания вопросов из стейджей
# Проверяем 12 сообщений подряд

API_URL="http://localhost:8000/api/chat"
USER_ID="test_stage_questions"

echo "🧪 ТЕСТ: Проверка вопросов из стейджей"
echo "=================================================="

# Массив тестовых сообщений
declare -a messages=(
    "привет"
    "меня зовут Глеб"
    "мне 30 лет"
    "я из Киева"
    "живу здесь 5 лет"
    "работаю программистом"
    "занимаюсь этим 8 лет"
    "нравится создавать проекты"
    "зарабатываю хорошо"
    "люблю спорт"
    "играю в футбол"
    "читаю книги"
)

# Инициализируем массив сообщений для API
declare -a api_messages=()

for i in "${!messages[@]}"; do
    message_num=$((i + 1))
    user_message="${messages[i]}"
    
    echo ""
    echo "📝 Сообщение $message_num: '$user_message'"
    
    # Добавляем сообщение пользователя
    api_messages+=("{\"role\":\"user\",\"content\":\"$user_message\"}")
    
    # Формируем JSON для запроса
    json_messages=""
    for j in "${!api_messages[@]}"; do
        if [ $j -gt 0 ]; then
            json_messages+=","
        fi
        json_messages+="${api_messages[j]}"
    done
    
    # Отправляем запрос
    response=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{\"user_id\":\"$USER_ID\",\"messages\":[$json_messages]}")
    
    if [ $? -eq 0 ]; then
        # Извлекаем ответ и информацию о вопросе
        assistant_response=$(echo "$response" | grep -o '"response":"[^"]*"' | cut -d'"' -f4)
        has_question=$(echo "$response" | grep -o '"has_question":[^,]*' | cut -d':' -f2)
        
        echo "🤖 Ответ Агаты: '$assistant_response'"
        echo "❓ Есть вопрос: $has_question"
        
        # Проверяем, должен ли быть вопрос (каждое 2-е сообщение начиная с 2-го)
        should_have_question="false"
        if [ $((message_num % 2)) -eq 0 ] && [ $message_num -ge 2 ]; then
            should_have_question="true"
        fi
        
        echo "🎯 Должен быть вопрос: $should_have_question"
        
        if [ "$should_have_question" = "true" ] && [ "$has_question" = "false" ]; then
            echo "❌ ОШИБКА! Сообщение $message_num должно содержать вопрос, но его нет!"
        elif [ "$should_have_question" = "false" ] && [ "$has_question" = "true" ]; then
            echo "❌ ОШИБКА! Сообщение $message_num не должно содержать вопрос, но он есть!"
        else
            echo "✅ ОК"
        fi
        
        # Добавляем ответ ассистента
        api_messages+=("{\"role\":\"assistant\",\"content\":\"$assistant_response\"}")
        
    else
        echo "❌ Ошибка API запроса"
        break
    fi
    
    # Пауза между запросами
    sleep 1
done

echo ""
echo "=================================================="
echo "🏁 Тест завершен!"
