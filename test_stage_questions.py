#!/usr/bin/env python3
"""
Тест для проверки задавания вопросов из стейджей
Проверяем 12 сообщений подряд
"""

import requests
import json
import time

API_URL = "http://localhost:8000/api/chat"

def test_stage_questions():
    """Тестируем задавание вопросов из стейджей"""
    
    user_id = "test_stage_questions"
    messages = []
    
    print("🧪 ТЕСТ: Проверка вопросов из стейджей")
    print("=" * 50)
    
    # Список тестовых сообщений
    test_messages = [
        "привет",
        "меня зовут Глеб", 
        "мне 30 лет",
        "я из Киева",
        "живу здесь 5 лет",
        "работаю программистом",
        "занимаюсь этим 8 лет",
        "нравится создавать проекты",
        "зарабатываю хорошо",
        "люблю спорт",
        "играю в футбол",
        "читаю книги"
    ]
    
    for i, user_message in enumerate(test_messages, 1):
        print(f"\n📝 Сообщение {i}: '{user_message}'")
        
        # Добавляем сообщение пользователя
        messages.append({"role": "user", "content": user_message})
        
        # Отправляем запрос
        response = requests.post(API_URL, json={
            "user_id": user_id,
            "messages": messages
        })
        
        if response.status_code == 200:
            data = response.json()
            assistant_response = data.get("response", "")
            has_question = data.get("has_question", False)
            
            print(f"🤖 Ответ Агаты: '{assistant_response}'")
            print(f"❓ Есть вопрос: {has_question}")
            
            # Проверяем, должен ли быть вопрос (каждое 2-е сообщение начиная с 2-го)
            should_have_question = (i % 2) == 0 and i >= 2
            print(f"🎯 Должен быть вопрос: {should_have_question}")
            
            if should_have_question and not has_question:
                print(f"❌ ОШИБКА! Сообщение {i} должно содержать вопрос, но его нет!")
            elif not should_have_question and has_question:
                print(f"❌ ОШИБКА! Сообщение {i} не должно содержать вопрос, но он есть!")
            else:
                print(f"✅ ОК")
            
            # Добавляем ответ ассистента
            messages.append({"role": "assistant", "content": assistant_response})
            
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            print(f"Ответ: {response.text}")
            break
        
        # Небольшая пауза между запросами
        time.sleep(1)
    
    print("\n" + "=" * 50)
    print("🏁 Тест завершен!")

if __name__ == "__main__":
    test_stage_questions()
