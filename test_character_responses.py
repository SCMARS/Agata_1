#!/usr/bin/env python3
"""
Тест для проверки улучшенных ответов с характером и эмоциями
"""
import requests
import json
import time

API_URL = "http://localhost:8000/api/chat"

def test_character_responses():
    print("🎭 ТЕСТ УЛУЧШЕННЫХ ОТВЕТОВ С ХАРАКТЕРОМ И ЭМОЦИЯМИ")
    print("=" * 60)
    print("Проверяем: естественность, эмоции, характер, отсутствие роботических фраз")
    print("=" * 60)
    
    user_id = "test_character_responses"
    messages = []
    
    test_cases = [
        "привет",
        "как дела? из киева",
        "программистом работаю",
        "люблю кататься на лыжах",
        "а ты что делаешь в варшаве?",
        "интересно, а сколько тебе лет?",
        "круто, у меня тоже хорошее настроение",
        "что планируешь на выходные?",
        "люблю читать книги",
        "а какой у тебя любимый фильм?"
    ]
    
    for i, user_message in enumerate(test_cases, 1):
        print(f"\n📨 СООБЩЕНИЕ {i}: '{user_message}'")
        
        # Добавляем сообщение пользователя
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = requests.post(
                API_URL,
                json={
                    "user_id": user_id,
                    "messages": messages
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                bot_response = data.get("response", "Нет ответа")
                
                # Добавляем ответ бота в историю
                messages.append({"role": "assistant", "content": bot_response})
                
                print(f"   Ответ: {bot_response}")
                
                # Анализируем ответ
                has_question = "?" in bot_response
                starts_with_hello = bot_response.startswith("Привет")
                has_robotic_phrases = any(phrase in bot_response.lower() for phrase in [
                    "приятно слышать", "у тебя, наверное", "отличное настроение, спасибо"
                ])
                has_emotions = any(word in bot_response.lower() for word in [
                    "круто", "классно", "ого", "вау", "интересно", "любопытно"
                ])
                has_personal = any(word in bot_response.lower() for word in [
                    "у меня", "мне", "я", "чувствую", "настроение"
                ])
                
                # Статус
                question_status = "✅ ВОПРОС" if has_question else "❌ НЕТ ВОПРОСА"
                hello_status = "❌ НАЧИНАЕТ С ПРИВЕТ" if starts_with_hello else "✅ НЕ НАЧИНАЕТ С ПРИВЕТ"
                robotic_status = "❌ РОБОТИЧЕСКИЕ ФРАЗЫ" if has_robotic_phrases else "✅ НЕТ РОБОТИЧЕСКИХ ФРАЗ"
                emotion_status = "✅ ЕСТЬ ЭМОЦИИ" if has_emotions else "❌ НЕТ ЭМОЦИЙ"
                personal_status = "✅ ЛИЧНОЕ" if has_personal else "❌ НЕТ ЛИЧНОГО"
                
                print(f"   {question_status} | {hello_status} | {robotic_status}")
                print(f"   {emotion_status} | {personal_status}")
                
                # Проверяем частоту вопросов (каждое 2-е сообщение)
                expected_question = (i % 2) == 0 and i >= 2
                question_correct = has_question == expected_question
                print(f"   Частота вопросов: {'✅ ПРАВИЛЬНО' if question_correct else '❌ НЕПРАВИЛЬНО'} (ожидалось: {expected_question})")
                
            else:
                print(f"   ❌ ОШИБКА: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ ОШИБКА: {e}")
        
        time.sleep(1)  # Пауза между сообщениями
    
    print("\n" + "=" * 60)
    print("🎯 ИТОГИ ТЕСТА:")
    print("- Проверены естественные ответы")
    print("- Проверены эмоции и характер")
    print("- Проверено отсутствие роботических фраз")
    print("- Проверена частота вопросов")
    print("=" * 60)

if __name__ == "__main__":
    test_character_responses()
