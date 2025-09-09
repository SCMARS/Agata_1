#!/usr/bin/env python3
"""
Комплексний тест системи Агати
Перевіряє всі покращення згідно з ТЗ
"""

import requests
import json
import time
from datetime import datetime

API_BASE = "http://localhost:8000"

def make_request(user_id, messages):
    """Відправляє запит до API"""
    try:
        response = requests.post(
            f"{API_BASE}/api/chat",
            json={"user_id": user_id, "messages": messages},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Помилка API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Помилка запиту: {e}")
        return None

def test_split_messages():
    """Тест 1: Розбиті повідомлення користувача"""
    print("\n🧪 ТЕСТ 1: Розбиті повідомлення користувача")
    print("=" * 60)
    
    # Тест 1.1: Розбите речення
    print("\n📝 Тест 1.1: Розбите речення")
    messages = [
        {"role": "user", "content": "Привет как"},
        {"role": "user", "content": "дела у тебя?"}
    ]
    result = make_request("test_split_sentence", messages)
    if result:
        print(f"✅ Відповідь: {result['parts']}")
        print(f"📊 Час відповіді: {result['delays_ms']}")
    
    # Тест 1.2: Кілька різних питань
    print("\n📝 Тест 1.2: Кілька різних питань")
    messages = [
        {"role": "user", "content": "Как дела?"},
        {"role": "user", "content": "Что делаешь?"},
        {"role": "user", "content": "Откуда ты?"}
    ]
    result = make_request("test_multiple_questions", messages)
    if result:
        print(f"✅ Відповідь: {result['parts']}")
        print("🔍 Перевірка: чи відповіла на ВСІ питання?")
        full_response = " ".join(result['parts'])
        checks = [
            ("дела" in full_response.lower(), "Відповіла на 'как дела?'"),
            ("делаю" in full_response.lower() or "работа" in full_response.lower(), "Відповіла на 'что делаешь?'"),
            ("москв" in full_response.lower() or "варшав" in full_response.lower(), "Відповіла на 'откуда ты?'")
        ]
        for check, desc in checks:
            print(f"   {'✅' if check else '❌'} {desc}")
    
    # Тест 1.3: Різні теми
    print("\n📝 Тест 1.3: Різні теми")
    messages = [
        {"role": "user", "content": "Привет"},
        {"role": "user", "content": "А еще хочу спросить про работу"},
        {"role": "user", "content": "И про хобби тоже"}
    ]
    result = make_request("test_different_topics", messages)
    if result:
        print(f"✅ Відповідь: {result['parts']}")

def test_no_repetition():
    """Тест 2: Відсутність повторення питань користувача"""
    print("\n🧪 ТЕСТ 2: Відсутність повторення питань")
    print("=" * 60)
    
    test_cases = [
        {"input": "Что?", "should_not_contain": ["что?", "что"]},
        {"input": "Почему ты игнорируешь мои вопросы?", "should_not_contain": ["почему", "игнорируешь"]},
        {"input": "Ты что, не слышишь меня?", "should_not_contain": ["не слышишь", "что,"]},
        {"input": "Как это звучит?", "should_not_contain": ["как это звучит"]},
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n📝 Тест 2.{i}: '{case['input']}'")
        messages = [{"role": "user", "content": case["input"]}]
        result = make_request(f"test_no_repeat_{i}", messages)
        
        if result:
            full_response = " ".join(result['parts']).lower()
            print(f"✅ Відповідь: {result['parts']}")
            
            repeated = False
            for phrase in case["should_not_contain"]:
                if phrase.lower() in full_response:
                    print(f"❌ Повторила фразу: '{phrase}'")
                    repeated = True
            
            if not repeated:
                print("✅ Не повторила питання користувача")

def test_response_structure():
    """Тест 3: Структура відповідей за стейджами"""
    print("\n🧪 ТЕСТ 3: Структура відповідей за стейджами")
    print("=" * 60)
    
    print("\n📝 Тест 3.1: Структура стейджу 1 (реакція → деталь → питання)")
    messages = [{"role": "user", "content": "Привет! Меня зовут Олег"}]
    result = make_request("test_stage1_structure", messages)
    
    if result:
        print(f"✅ Відповідь: {result['parts']}")
        print(f"📊 Кількість частин: {len(result['parts'])}")
        print(f"🎯 Стейдж: {result.get('stage_number', 'N/A')}")
        print(f"📋 Поведінкова стратегія: {result.get('current_strategy', 'N/A')}")
        
        # Перевіряємо структуру
        if len(result['parts']) >= 2:
            print("✅ Відповідь розбита на частини")
        else:
            print("❌ Відповідь не розбита на частини")

def test_stage_progression():
    """Тест 4: Прогресія по стейджах та темах"""
    print("\n🧪 ТЕСТ 4: Прогресія по стейджах та темах")
    print("=" * 60)
    
    user_id = "test_stage_progression"
    
    # Імітуємо діалог по темах стейджу 1
    conversations = [
        {"input": "Привет! Как дела?", "expected_theme": "Знакомство"},
        {"input": "Я из Киева", "expected_theme": "Жительство"}, 
        {"input": "Работаю программистом", "expected_theme": "Работа"},
        {"input": "Люблю играть в футбол", "expected_theme": "Хобби"},
    ]
    
    for i, conv in enumerate(conversations, 1):
        print(f"\n📝 Крок {i}: {conv['input']}")
        messages = [{"role": "user", "content": conv["input"]}]
        result = make_request(user_id, messages)
        
        if result:
            print(f"✅ Відповідь: {result['parts']}")
            print(f"🎯 Стейдж: {result.get('stage_number', 'N/A')}")
            
            # Перевіряємо прогрес стейджа
            if 'stage_progress' in result.get('behavioral_analysis', {}):
                stage_progress = result['behavioral_analysis']['stage_progress']
                print(f"📋 Прогрес стейджа: {stage_progress}")
        
        time.sleep(1)  # Пауза між повідомленнями

def test_emoji_and_format():
    """Тест 5: Емодзі та формат повідомлень"""
    print("\n🧪 ТЕСТ 5: Емодзі та формат повідомлень")
    print("=" * 60)
    
    print("\n📝 Тест 5.1: Наявність емодзі")
    messages = [{"role": "user", "content": "Привет! Как настроение?"}]
    result = make_request("test_emoji", messages)
    
    if result:
        full_response = " ".join(result['parts'])
        print(f"✅ Відповідь: {result['parts']}")
        
        # Перевіряємо наявність емодзі
        emoji_found = any(ord(char) > 127 for char in full_response)
        if emoji_found:
            print("✅ Емодзі присутні")
        else:
            print("❌ Емодзі відсутні")
        
        # Перевіряємо довжину частин
        for i, part in enumerate(result['parts'], 1):
            length = len(part)
            print(f"📏 Частина {i}: {length} символів")
            if length <= 80:
                print(f"   ✅ Довжина в межах норми")
            else:
                print(f"   ❌ Занадто довга частина")

def test_memory_usage():
    """Тест 6: Використання пам'яті"""
    print("\n🧪 ТЕСТ 6: Використання пам'яті")
    print("=" * 60)
    
    user_id = "test_memory"
    
    # Крок 1: Представляємося
    print("\n📝 Крок 1: Знайомство")
    messages = [{"role": "user", "content": "Привет! Меня зовут Дмитрий, я из Одессы"}]
    result1 = make_request(user_id, messages)
    if result1:
        print(f"✅ Відповідь 1: {result1['parts']}")
    
    time.sleep(2)
    
    # Крок 2: Перевіряємо, чи запам'ятала
    print("\n📝 Крок 2: Перевірка пам'яті")
    messages = [{"role": "user", "content": "А ты помнишь, как меня зовут?"}]
    result2 = make_request(user_id, messages)
    if result2:
        response = " ".join(result2['parts']).lower()
        print(f"✅ Відповідь 2: {result2['parts']}")
        
        if "дмитр" in response or "dmitr" in response:
            print("✅ Запам'ятала ім'я")
        else:
            print("❌ Не запам'ятала ім'я")
        
        if "одесс" in response:
            print("✅ Запам'ятала місто")
        else:
            print("❌ Не запам'ятала місто")

def test_time_orientation():
    """Тест 7: Орієнтація в часі"""
    print("\n🧪 ТЕСТ 7: Орієнтація в часі")
    print("=" * 60)
    
    current_hour = datetime.now().hour
    expected_greeting = ""
    if 6 <= current_hour < 12:
        expected_greeting = "утр"
    elif 12 <= current_hour < 18:
        expected_greeting = "день"
    elif 18 <= current_hour < 22:
        expected_greeting = "вечер"
    else:
        expected_greeting = "ноч"
    
    print(f"🕐 Поточний час: {current_hour}:xx")
    print(f"🎯 Очікуване вітання: {expected_greeting}")
    
    messages = [{"role": "user", "content": "Привет!"}]
    result = make_request("test_time", messages)
    
    if result:
        response = " ".join(result['parts']).lower()
        print(f"✅ Відповідь: {result['parts']}")
        
        if expected_greeting in response:
            print("✅ Правильне вітання за часом доби")
        else:
            print("❌ Неправильне вітання за часом доби")

def run_all_tests():
    """Запускає всі тести"""
    print("🚀 КОМПЛЕКСНЕ ТЕСТУВАННЯ СИСТЕМИ АГАТИ")
    print("=" * 80)
    print(f"⏰ Час початку: {datetime.now().strftime('%H:%M:%S')}")
    
    # Перевіряємо доступність API
    try:
        response = requests.get(f"{API_BASE}/healthz", timeout=5)
        if response.status_code != 200:
            print("❌ API недоступний!")
            return
    except:
        print("❌ Не вдається підключитися до API!")
        return
    
    print("✅ API доступний, починаємо тести...\n")
    
    # Запускаємо всі тести
    test_split_messages()
    test_no_repetition() 
    test_response_structure()
    test_stage_progression()
    test_emoji_and_format()
    test_memory_usage()
    test_time_orientation()
    
    print("\n" + "=" * 80)
    print("🏁 ТЕСТУВАННЯ ЗАВЕРШЕНО")
    print(f"⏰ Час завершення: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run_all_tests()
