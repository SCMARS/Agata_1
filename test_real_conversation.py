#!/usr/bin/env python3
"""
Тест реального діалогу з Агатою
Імітує справжню розмову в Telegram
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def send_message(user_id, content):
    """Відправляє повідомлення та показує відповідь"""
    try:
        response = requests.post(
            f"{API_BASE}/api/chat",
            json={"user_id": user_id, "messages": [{"role": "user", "content": content}]},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            parts = result.get('parts', [])
            delays = result.get('delays_ms', [])
            
            print(f"👤 Користувач: {content}")
            print(f"🤖 Агата:")
            
            for i, (part, delay) in enumerate(zip(parts, delays)):
                if i > 0:
                    time.sleep(delay / 1000)  # Імітуємо затримку
                print(f"   {part}")
            
            # Показуємо додаткову інформацію
            print(f"📊 Стейдж: {result.get('stage_number', 'N/A')}")
            print(f"📅 День: {result.get('day_number', 'N/A')}")
            print(f"🎭 Стратегія: {result.get('current_strategy', 'N/A')}")
            
            if 'behavioral_analysis' in result:
                ba = result['behavioral_analysis']
                if 'stage_progress' in ba:
                    sp = ba['stage_progress']
                    print(f"📋 Прогрес стейджа: {sp.get('stage_name', 'N/A')}")
                    if 'next_theme_slot' in ba:
                        nts = ba['next_theme_slot']
                        print(f"🎯 Наступна тема: {nts.get('theme_name', 'N/A')}")
                        print(f"🔍 Наступний слот: {nts.get('next_slot', 'N/A')}")
            
            print("-" * 50)
            return result
        else:
            print(f"❌ Помилка API: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return None

def simulate_real_conversation():
    """Імітує реальну розмову в Telegram"""
    print("🎭 ІМІТАЦІЯ РЕАЛЬНОГО ДІАЛОГУ В TELEGRAM")
    print("=" * 70)
    
    user_id = "real_user_test"
    
    # Діалог згідно зі стейджами
    conversation = [
        # Знайомство
        "Привет!",
        "Меня зовут Алексей",
        "Как дела?",
        
        # Жительство  
        "Я из Киева",
        "Живу здесь уже 25 лет",
        "А ты откуда?",
        
        # Робота
        "Работаю программистом",
        "Уже 5 лет в IT",
        "А ты кем работаешь?",
        
        # Хобби
        "Люблю играть в теннис",
        "А еще читаю книги",
        "А ты чем увлекаешься?",
    ]
    
    for i, message in enumerate(conversation, 1):
        print(f"\n🔄 Крок {i}:")
        send_message(user_id, message)
        time.sleep(2)  # Пауза між повідомленнями

def test_split_messages_real():
    """Тест розбитих повідомлень як в реальному Telegram"""
    print("\n🎭 ТЕСТ РОЗБИТИХ ПОВІДОМЛЕНЬ (як в Telegram)")
    print("=" * 70)
    
    user_id = "split_test_real"
    
    # Імітуємо швидке написання кількох повідомлень
    messages = [
        {"role": "user", "content": "Привет"},
        {"role": "user", "content": "как дела?"},
        {"role": "user", "content": "что делаешь?"}
    ]
    
    print("👤 Користувач (швидко підряд):")
    for msg in messages:
        print(f"   {msg['content']}")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/chat",
            json={"user_id": user_id, "messages": messages},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            parts = result.get('parts', [])
            
            print(f"\n🤖 Агата:")
            for part in parts:
                print(f"   {part}")
            
            # Аналіз відповіді
            full_response = " ".join(parts).lower()
            print(f"\n🔍 Аналіз відповіді:")
            
            checks = [
                ("привет" in full_response or "добрый" in full_response, "Привіталася"),
                ("дела" in full_response or "хорошо" in full_response, "Відповіла на 'как дела?'"),
                ("делаю" in full_response or "работа" in full_response or "отдых" in full_response, "Відповіла на 'что делаешь?'"),
                (len(parts) <= 3, "Короткі повідомлення (≤3 частини)"),
                ("добрый вечер" not in full_response, "Немає повторення 'Добрый вечер'")
            ]
            
            for check, desc in checks:
                print(f"   {'✅' if check else '❌'} {desc}")
                
        else:
            print(f"❌ Помилка API: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Помилка: {e}")

if __name__ == "__main__":
    # Спочатку тест розбитих повідомлень
    test_split_messages_real()
    
    print("\n" + "="*70)
    input("📱 Натисніть Enter для продовження з повним діалогом...")
    
    # Потім повний діалог
    simulate_real_conversation()
