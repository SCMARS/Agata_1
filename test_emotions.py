#!/usr/bin/env python3
"""
Реальный тест эмоционального анализа
Проверяем как разные эмоции влияют на ответы модели
"""

import requests
import json
import time

def test_emotion(user_id, message, emotion_type):
    """Тестируем одну эмоцию"""
    print(f"\n{'='*60}")
    print(f"🧪 ТЕСТ: {emotion_type}")
    print(f"💬 Сообщение: '{message}'")
    print(f"{'='*60}")
    
    url = "http://localhost:8000/api/chat"
    data = {
        "user_id": user_id,
        "message": message,
        "messages": [
            {"role": "user", "content": message}
        ]
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            
            # Извлекаем ключевую информацию
            behavioral = result.get('behavioral_analysis', {})
            strategy_name = behavioral.get('strategy_name', 'Неизвестно')
            confidence = behavioral.get('confidence', 0)
            ai_response = result.get('parts', [''])[0] if result.get('parts') else ''
            
            print(f"🎭 Стратегия: {strategy_name}")
            print(f"📊 Confidence: {confidence}")
            print(f"🤖 Ответ ИИ: {ai_response[:100]}...")
            
            return {
                'emotion_type': emotion_type,
                'strategy_name': strategy_name,
                'confidence': confidence,
                'ai_response': ai_response,
                'message': message
            }
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def main():
    """Основной тест"""
    print("🚀 ЗАПУСК РЕАЛЬНОГО ТЕСТА ЭМОЦИОНАЛЬНОГО АНАЛИЗА")
    print("Проверяем как разные эмоции влияют на стратегии и ответы")
    
    # Ждем запуска сервера
    print("\n⏳ Ждем запуска сервера...")
    time.sleep(5)
    
    # Тестовые случаи с разными эмоциями
    test_cases = [
        ("test_neutral", "Привет! Как дела?", "Нейтральное"),
        ("test_positive", "Привет! У меня отличное настроение! Как дела? 😊", "Позитивное"),
        ("test_excited", "Привет! У меня супер настроение! Всё отлично! 🎉", "Возбужденное"),
        ("test_angry", "Ты дура! Почему не отвечаешь нормально?", "Злое"),
        ("test_rude", "Нахуй иди! Ты тупая!", "Грубое"),
        ("test_sad", "Привет... У меня плохое настроение, грустно...", "Грустное"),
        ("test_anxious", "Привет... Я очень волнуюсь, не знаю что делать...", "Тревожное"),
        ("test_playful", "Привет! Давай поиграем! 😄 Что будем делать?", "Игривое"),
        ("test_intellectual", "Привет. Интересно узнать твое мнение о квантовой физике.", "Интеллектуальное"),
        ("test_flirt", "Привет, красотка! Как дела? 😘", "Флирт")
    ]
    
    results = []
    
    for user_id, message, emotion_type in test_cases:
        result = test_emotion(user_id, message, emotion_type)
        if result:
            results.append(result)
        time.sleep(2)  # Пауза между тестами
    
    # Анализ результатов
    print(f"\n{'='*80}")
    print("📊 АНАЛИЗ РЕЗУЛЬТАТОВ")
    print(f"{'='*80}")
    
    # Группируем по стратегиям
    strategies = {}
    for result in results:
        strategy = result['strategy_name']
        if strategy not in strategies:
            strategies[strategy] = []
        strategies[strategy].append(result)
    
    print(f"\n🎭 НАЙДЕННЫЕ СТРАТЕГИИ:")
    for strategy, cases in strategies.items():
        print(f"  {strategy}: {len(cases)} случаев")
        for case in cases:
            print(f"    - {case['emotion_type']}: {case['confidence']:.2f}")
    
    # Проверяем разнообразие
    unique_strategies = len(strategies)
    print(f"\n📈 РАЗНООБРАЗИЕ СТРАТЕГИЙ: {unique_strategies} из {len(test_cases)} тестов")
    
    if unique_strategies == 1:
        print("⚠️  ПРОБЛЕМА: Система использует только одну стратегию!")
    elif unique_strategies < 3:
        print("⚠️  ПРОБЛЕМА: Мало разнообразия в стратегиях")
    else:
        print("✅ ХОРОШО: Система использует разные стратегии")
    
    # Проверяем confidence
    avg_confidence = sum(r['confidence'] for r in results) / len(results)
    print(f"📊 СРЕДНИЙ CONFIDENCE: {avg_confidence:.2f}")
    
    if avg_confidence == 1.0:
        print("⚠️  ПРОБЛЕМА: Все confidence = 1.0 (возможно хардкод)")
    elif avg_confidence > 0.8:
        print("⚠️  ВНИМАНИЕ: Высокий confidence, возможно мало разнообразия")
    else:
        print("✅ ХОРОШО: Confidence варьируется")
    
    print(f"\n🎯 ТЕСТ ЗАВЕРШЕН! Протестировано {len(results)} случаев")

if __name__ == "__main__":
    main()
