#!/usr/bin/env python3
"""
Швидкий тест покращень системи Агати
"""

import requests
import json

API_BASE = "http://localhost:8000"

def test(user_id, messages, description):
    """Швидкий тест"""
    print(f"\n🧪 {description}")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{API_BASE}/api/chat",
            json={"user_id": user_id, "messages": messages},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            parts = result.get('parts', [])
            print(f"✅ Відповідь: {parts}")
            
            # Перевіряємо відсутність "Добрый вечер"
            full_response = " ".join(parts)
            if "добрый вечер" in full_response.lower():
                print("❌ Містить 'Добрый вечер'")
            else:
                print("✅ Немає 'Добрый вечер'")
            
            # Перевіряємо довжину частин
            for i, part in enumerate(parts, 1):
                length = len(part)
                status = "✅" if length <= 80 else "❌"
                print(f"{status} Частина {i}: {length} символів")
            
            return result
        else:
            print(f"❌ Помилка: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return None

def main():
    print("🚀 ШВИДКИЙ ТЕСТ ПОКРАЩЕНЬ АГАТИ")
    print("=" * 60)
    
    # Тест 1: Просте питання
    test("test1", [{"role": "user", "content": "Откуда ты?"}], 
         "Пряме питання")
    
    # Тест 2: Розбиті повідомлення
    test("test2", [
        {"role": "user", "content": "Привет как"}, 
        {"role": "user", "content": "дела?"}
    ], "Розбите повідомлення")
    
    # Тест 3: Кілька питань
    test("test3", [
        {"role": "user", "content": "Как дела?"}, 
        {"role": "user", "content": "Что делаешь?"}, 
        {"role": "user", "content": "Откуда ты?"}
    ], "Кілька питань підряд")
    
    # Тест 4: Проблемне питання зі скріншоту
    test("test4", [{"role": "user", "content": "Что?"}], 
         "Коротке питання 'Что?'")
    
    # Тест 5: Знайомство
    test("test5", [{"role": "user", "content": "Привет! Меня зовут Андрей"}], 
         "Знайомство з ім'ям")

if __name__ == "__main__":
    main()
