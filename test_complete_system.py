

import requests
import json
import time
import sys
from datetime import datetime

def test_emotional_analysis():

    print("🧠 ТЕСТ ЭМОЦИОНАЛЬНОГО АНАЛИЗА")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Грубое сообщение",
            "message": "Ты дура!",
            "expected_emotion": "rude",
            "expected_strategy": "reserved"
        },
        {
            "name": "Позитивное сообщение", 
            "message": "Привет! Как дела? У меня отличное настроение!",
            "expected_emotion": "positive",
            "expected_strategy": "playful"
        },
        {
            "name": "Нейтральное сообщение",
            "message": "Как дела?",
            "expected_emotion": "neutral", 
            "expected_strategy": "mysterious"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Сообщение: '{test_case['message']}'")
        
        try:
            response = requests.post(
                "http://localhost:8000/api/chat",
                json={
                    "user_id": f"test_emotional_{i}",
                    "message": test_case['message'],
                    "messages": [{"role": "user", "content": test_case['message']}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                behavioral_analysis = data.get('behavioral_analysis', {})
                
                emotion = behavioral_analysis.get('dominant_emotion', 'unknown')
                strategy = behavioral_analysis.get('recommended_strategy', 'unknown')
                
                print(f"   ✅ Эмоция: {emotion} (ожидалось: {test_case['expected_emotion']})")
                print(f"   ✅ Стратегия: {strategy} (ожидалось: {test_case['expected_strategy']})")
                
                # Проверяем соответствие ожиданиям
                emotion_match = emotion == test_case['expected_emotion']
                strategy_match = strategy == test_case['expected_strategy']
                
                if emotion_match and strategy_match:
                    print(f"   🎯 РЕЗУЛЬТАТ: УСПЕХ")
                    results.append(True)
                else:
                    print(f"   ❌ РЕЗУЛЬТАТ: ОШИБКА")
                    results.append(False)
                    
            else:
                print(f"   ❌ HTTP ошибка: {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ Исключение: {e}")
            results.append(False)
    
    print(f"\n📊 ИТОГИ ЭМОЦИОНАЛЬНОГО АНАЛИЗА:")
    print(f"   Успешно: {sum(results)}/{len(results)}")
    print(f"   Успешность: {sum(results)/len(results)*100:.1f}%")
    
    return sum(results) == len(results)

def test_response_quality():
    """Тест качества ответов модели"""
    print("\n\n🎭 ТЕСТ КАЧЕСТВА ОТВЕТОВ")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Грубое сообщение (reserved strategy)",
            "message": "Ты тупая!",
            "should_be_reserved": True
        },
        {
            "name": "Позитивное сообщение (playful strategy)", 
            "message": "Привет! Как дела? У меня отличное настроение!",
            "should_be_playful": True
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        
        try:
            response = requests.post(
                "http://localhost:8000/api/chat",
                json={
                    "user_id": f"test_response_{i}",
                    "message": test_case['message'],
                    "messages": [{"role": "user", "content": test_case['message']}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                model_response = data.get('response', '')
                
                print(f"   Ответ модели: '{model_response[:100]}...'")
                
                # Простая проверка качества ответа
                if len(model_response) > 10 and len(model_response) < 1000:
                    print(f"   ✅ Длина ответа: {len(model_response)} символов")
                    results.append(True)
                else:
                    print(f"   ❌ Неподходящая длина ответа: {len(model_response)} символов")
                    results.append(False)
                    
            else:
                print(f"   ❌ HTTP ошибка: {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ Исключение: {e}")
            results.append(False)
    
    print(f"\n📊 ИТОГИ КАЧЕСТВА ОТВЕТОВ:")
    print(f"   Успешно: {sum(results)}/{len(results)}")
    print(f"   Успешность: {sum(results)/len(results)*100:.1f}%")
    
    return sum(results) == len(results)

def test_logging():
    """Тест логирования"""
    print("\n\n📝 ТЕСТ ЛОГИРОВАНИЯ")
    print("=" * 50)
    
    # Проверяем наличие лог файлов
    import os
    
    log_files = [
        "telegram_bot.log",
        "logs/api.log"
    ]
    
    results = []
    
    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            print(f"   ✅ {log_file}: {size} байт")
            results.append(True)
        else:
            print(f"   ❌ {log_file}: не найден")
            results.append(False)
    
    print(f"\n📊 ИТОГИ ЛОГИРОВАНИЯ:")
    print(f"   Найдено файлов: {sum(results)}/{len(results)}")
    
    return sum(results) > 0

def main():
    """Главная функция тестирования"""
    print("🚀 КОМПЛЕКСНЫЙ ТЕСТ СИСТЕМЫ AGATHA")
    print("=" * 60)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Проверяем доступность API
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 404:  # Ожидаем 404 для корневого пути
            print("✅ API сервер доступен")
        else:
            print("❌ API сервер недоступен")
            return
    except Exception as e:
        print(f"❌ Не удается подключиться к API: {e}")
        return
    
    # Запускаем тесты
    test_results = []
    
    # Тест 1: Эмоциональный анализ
    test_results.append(test_emotional_analysis())
    
    # Тест 2: Качество ответов
    test_results.append(test_response_quality())
    
    # Тест 3: Логирование
    test_results.append(test_logging())
    
    # Итоговые результаты
    print("\n\n🏆 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 60)
    
    test_names = [
        "Эмоциональный анализ",
        "Качество ответов", 
        "Логирование"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, test_results), 1):
        status = "✅ УСПЕХ" if result else "❌ ОШИБКА"
        print(f"{i}. {name}: {status}")
    
    overall_success = sum(test_results) == len(test_results)
    
    print(f"\n🎯 ОБЩИЙ РЕЗУЛЬТАТ:")
    if overall_success:
        print("   🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("   ✅ Система работает корректно")
    else:
        print("   ⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("   ❌ Требуется исправление")
    
    print(f"\nВремя завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
