#!/usr/bin/env python3
"""
Тестуємо функціональність логування для всіх модулів
"""
import requests
import json
import time

def test_api_with_logging():
    """Тестуємо API з детальним логуванням"""
    
    print("🧪 Тестування API з детальним логуванням...")
    print("=" * 60)
    
    # Перевіряемо здоров'я API
    try:
        response = requests.get("http://localhost:8000/healthz")
        if response.status_code == 200:
            print("✅ API сервер здоровий")
        else:
            print(f"❌ API сервер не відповідає: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Не можу підключитися до API: {e}")
        return
    
    # Тестові сценарії
    test_scenarios = [
        {
            "name": "Знайомство (stage 1)",
            "user_id": "test_stage_1_user",
            "messages": [
                {"role": "user", "content": "привет"},
                {"role": "user", "content": "как дела?"}
            ]
        },
        {
            "name": "Продовження розмови (stage 1 -> stage 2)",
            "user_id": "test_stage_2_user", 
            "messages": [
                {"role": "user", "content": "привет"},
                {"role": "user", "content": "расскажи о себе"},
                {"role": "user", "content": "интересно"},
                {"role": "user", "content": "а что любишь делать?"},
                {"role": "user", "content": "круто"},
                {"role": "user", "content": "а работаешь где?"}
            ]
        },
        {
            "name": "Тест емоційної реакції",
            "user_id": "test_emotions_user",
            "messages": [
                {"role": "user", "content": "мне грустно сегодня"},
                {"role": "user", "content": "не знаю что делать"}
            ]
        },
        {
            "name": "Тест часових питань (вечір)", 
            "user_id": "test_time_user",
            "messages": [
                {"role": "user", "content": "как дела"},
                {"role": "user", "content": "что делаешь вечером?"}
            ]
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🎯 Сценарій {i}: {scenario['name']}")
        print("-" * 40)
        
        try:
            response = requests.post(
                "http://localhost:8000/api/chat",
                headers={"Content-Type": "application/json"},
                json={
                    "user_id": scenario["user_id"],
                    "messages": scenario["messages"]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Відповідь отримана: {len(result.get('parts', []))} частин")
                print(f"📊 Поведінкова стратегія: {result.get('current_strategy', 'Unknown')}")
                print(f"🎭 Стейдж: {result.get('stage_number', 'Unknown')}")
                print(f"📅 День: {result.get('day_number', 'Unknown')}")
                
                # Показуємо частину відповіді
                parts = result.get('parts', [])
                if parts:
                    print(f"💬 Перша частина: '{parts[0][:50]}...'")
                
            else:
                print(f"❌ Помилка API: {response.status_code}")
                print(f"   Відповідь: {response.text}")
                
        except Exception as e:
            print(f"❌ Помилка запиту: {e}")
        
        # Пауза між тестами
        time.sleep(2)
    
    print("\n" + "=" * 60)
    print("🔍 Перевірте логи сервера на наявність:")
    print("   🎭 [BEHAVIORAL] - аналіз поведінки")
    print("   📊 [STAGE_PROGRESS] - прогрес стейджів") 
    print("   ⏰ [TIME] - часові дані")
    print("   ⏰ [DAILY_QUESTIONS] - генерація питань")
    print("   📈 [STAGE] - інформація про стейджі")

if __name__ == "__main__":
    test_api_with_logging()
