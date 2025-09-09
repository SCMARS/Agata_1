#!/usr/bin/env python3
"""
Тестирование системы живого общения Agatha AI
"""
import requests
import json
import time
import sys
from datetime import datetime

# Конфигурация
API_BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_living_chat"

def log_test(message, level="INFO"):
    """Логирование тестов"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def test_api_health():
    """Тест здоровья API"""
    log_test("🔍 Тестируем здоровье API...")
    try:
        response = requests.get(f"{API_BASE_URL}/healthz", timeout=5)
        if response.status_code == 200:
            log_test("✅ API здоров", "SUCCESS")
            return True
        else:
            log_test(f"❌ API нездоров: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        log_test(f"❌ Ошибка подключения к API: {e}", "ERROR")
        return False

def test_api_ready():
    """Тест готовности API"""
    log_test("🔍 Тестируем готовность API...")
    try:
        response = requests.get(f"{API_BASE_URL}/readyz", timeout=5)
        if response.status_code == 200:
            log_test("✅ API готов", "SUCCESS")
            return True
        else:
            log_test(f"❌ API не готов: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        log_test(f"❌ Ошибка проверки готовности: {e}", "ERROR")
        return False

def send_message(messages, description=""):
    """Отправка сообщения и анализ ответа"""
    log_test(f"📤 Отправляем сообщение: {description}")
    log_test(f"   Сообщения: {[msg['content'] for msg in messages]}")
    
    try:
        payload = {
            "user_id": TEST_USER_ID,
            "messages": messages
        }
        
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            
            # Анализируем ответ
            log_test(f"📥 Получен ответ за {end_time - start_time:.2f}с", "SUCCESS")
            log_test(f"   Частей сообщения: {len(data.get('parts', []))}")
            log_test(f"   Есть вопрос: {data.get('has_question', False)}")
            log_test(f"   Задержки: {data.get('delays_ms', [])}")
            
            # Показываем части сообщения
            for i, part in enumerate(data.get('parts', []), 1):
                log_test(f"   Часть {i}: {part}")
            
            # Анализ поведенческой адаптации
            behavioral = data.get('behavioral_analysis', {})
            if behavioral:
                log_test(f"   Эмоция: {behavioral.get('dominant_emotion', 'unknown')}")
                log_test(f"   Интенсивность: {behavioral.get('emotional_intensity', 0)}")
                log_test(f"   Стратегия: {behavioral.get('recommended_strategy', 'unknown')}")
            
            return data
        else:
            log_test(f"❌ Ошибка API: {response.status_code}", "ERROR")
            log_test(f"   Ответ: {response.text}")
            return None
            
    except Exception as e:
        log_test(f"❌ Ошибка отправки сообщения: {e}", "ERROR")
        return None

def test_basic_greeting():
    """Тест базового приветствия"""
    log_test("\n" + "="*50)
    log_test("🧪 ТЕСТ 1: Базовое приветствие")
    log_test("="*50)
    
    messages = [{"role": "user", "content": "Привет! Меня зовут Глеб"}]
    result = send_message(messages, "Простое приветствие с именем")
    
    if result:
        parts = result.get('parts', [])
        stage = result.get('stage_number', 1)
        
        # Проверяем количество частей (должно быть больше)
        if len(parts) >= 1:
            log_test(f"✅ Тест пройден: получен ответ из {len(parts)} частей", "SUCCESS")
            log_test(f"   📊 Стейдж: {stage}")
            
            # Проверяем длину частей (должны быть короче)
            for i, part in enumerate(parts, 1):
                if len(part) <= 80:
                    log_test(f"   ✅ Часть {i}: {len(part)} символов (короткая)", "SUCCESS")
                else:
                    log_test(f"   ⚠️ Часть {i}: {len(part)} символов (слишком длинная)", "WARNING")
        else:
            log_test("❌ Тест провален: нет частей ответа", "ERROR")
    else:
        log_test("❌ Тест провален: нет ответа от API", "ERROR")

def test_short_messages():
    """Тест коротких сообщений"""
    log_test("\n" + "="*50)
    log_test("🧪 ТЕСТ 2: Короткие сообщения")
    log_test("="*50)
    
    messages = [
        {"role": "user", "content": "Привет"},
        {"role": "user", "content": "как дела"},
        {"role": "user", "content": "что делаешь"}
    ]
    result = send_message(messages, "Три коротких сообщения подряд")
    
    if result:
        parts = result.get('parts', [])
        if len(parts) >= 1:
            log_test("✅ Тест пройден: короткие сообщения обработаны", "SUCCESS")
        else:
            log_test("❌ Тест провален: короткие сообщения не обработаны", "ERROR")
    else:
        log_test("❌ Тест провален: нет ответа от API", "ERROR")

def test_emotional_responses():
    """Тест эмоциональных ответов"""
    log_test("\n" + "="*50)
    log_test("🧪 ТЕСТ 3: Эмоциональные ответы")
    log_test("="*50)
    
    messages = [{"role": "user", "content": "Круто! Вау! Ого!"}]
    result = send_message(messages, "Эмоциональное сообщение")
    
    if result:
        parts = result.get('parts', [])
        behavioral = result.get('behavioral_analysis', {})
        
        # Проверяем наличие эмодзи
        has_emoji = any('😊' in part or '😄' in part or '!' in part for part in parts)
        if has_emoji:
            log_test("✅ Тест пройден: найдены эмодзи/эмоции", "SUCCESS")
        else:
            log_test("⚠️ Тест частично пройден: эмодзи не найдены", "WARNING")
        
        # Проверяем эмоциональный анализ
        emotion = behavioral.get('dominant_emotion', 'unknown')
        if emotion != 'unknown':
            log_test(f"✅ Тест пройден: эмоция определена ({emotion})", "SUCCESS")
        else:
            log_test("⚠️ Тест частично пройден: эмоция не определена", "WARNING")
    else:
        log_test("❌ Тест провален: нет ответа от API", "ERROR")

def test_question_generation():
    """Тест генерации вопросов"""
    log_test("\n" + "="*50)
    log_test("🧪 ТЕСТ 4: Генерация вопросов")
    log_test("="*50)
    
    messages = [{"role": "user", "content": "Расскажи о себе"}]
    result = send_message(messages, "Запрос информации о боте")
    
    if result:
        has_question = result.get('has_question', False)
        parts = result.get('parts', [])
        
        # Проверяем наличие вопросов в ответе
        has_question_mark = any('?' in part for part in parts)
        
        if has_question or has_question_mark:
            log_test("✅ Тест пройден: вопрос сгенерирован", "SUCCESS")
        else:
            log_test("⚠️ Тест частично пройден: вопрос не сгенерирован", "WARNING")
    else:
        log_test("❌ Тест провален: нет ответа от API", "ERROR")

def test_message_splitting():
    """Тест разбиения сообщений"""
    log_test("\n" + "="*50)
    log_test("🧪 ТЕСТ 5: Разбиение сообщений")
    log_test("="*50)
    
    messages = [{"role": "user", "content": "Расскажи подробно о своей работе, увлечениях и планах на будущее"}]
    result = send_message(messages, "Длинное сообщение для разбиения")
    
    if result:
        parts = result.get('parts', [])
        delays = result.get('delays_ms', [])
        
        if len(parts) > 1:
            log_test(f"✅ Тест пройден: сообщение разбито на {len(parts)} частей", "SUCCESS")
            log_test(f"   Задержки: {delays}")
        else:
            log_test("⚠️ Тест частично пройден: сообщение не разбито", "WARNING")
    else:
        log_test("❌ Тест провален: нет ответа от API", "ERROR")

def test_stage_progression():
    """Тест прогрессии стейджей"""
    log_test("\n" + "="*50)
    log_test("🧪 ТЕСТ 6: Прогрессия стейджей")
    log_test("="*50)
    
    # Тестируем разные стейджи
    test_cases = [
        (1, "Привет! Меня зовут Анна", "Стейдж 1: Знакомство"),
        (2, "Как дела? Что делаешь?", "Стейдж 2: Развитие"),
        (3, "Расскажи о себе подробнее", "Стейдж 3: Углубление")
    ]
    
    for expected_stage, message, description in test_cases:
        log_test(f"📝 Тестируем: {description}")
        messages = [{"role": "user", "content": message}]
        result = send_message(messages, description)
        
        if result:
            actual_stage = result.get('stage_number', 1)
            parts = result.get('parts', [])
            
            log_test(f"   📊 Ожидаемый стейдж: {expected_stage}, фактический: {actual_stage}")
            log_test(f"   📝 Частей ответа: {len(parts)}")
            
            # Проверяем длину частей
            for i, part in enumerate(parts, 1):
                if len(part) <= 80:
                    log_test(f"   ✅ Часть {i}: {len(part)} символов", "SUCCESS")
                else:
                    log_test(f"   ⚠️ Часть {i}: {len(part)} символов (длинная)", "WARNING")
        else:
            log_test(f"   ❌ Ошибка в тесте: {description}", "ERROR")

def test_conversation_flow():
    """Тест потока беседы"""
    log_test("\n" + "="*50)
    log_test("🧪 ТЕСТ 7: Поток беседы")
    log_test("="*50)
    
    # Первое сообщение
    log_test("📝 Шаг 1: Первое сообщение")
    messages1 = [{"role": "user", "content": "Привет! Меня зовут Анна"}]
    result1 = send_message(messages1, "Знакомство")
    
    time.sleep(1)  # Пауза между сообщениями
    
    # Второе сообщение
    log_test("📝 Шаг 2: Второе сообщение")
    messages2 = [
        {"role": "user", "content": "Привет! Меня зовут Анна"},
        {"role": "user", "content": "Как дела?"}
    ]
    result2 = send_message(messages2, "Продолжение беседы")
    
    if result1 and result2:
        log_test("✅ Тест пройден: поток беседы работает", "SUCCESS")
    else:
        log_test("❌ Тест провален: поток беседы не работает", "ERROR")

def run_all_tests():
    """Запуск всех тестов"""
    log_test("🚀 ЗАПУСК ТЕСТОВ СИСТЕМЫ ЖИВОГО ОБЩЕНИЯ")
    log_test("="*60)
    
    # Проверяем API
    if not test_api_health():
        log_test("❌ API недоступен, тесты прерваны", "ERROR")
        return False
    
    if not test_api_ready():
        log_test("❌ API не готов, тесты прерваны", "ERROR")
        return False
    
    # Запускаем тесты
    test_basic_greeting()
    test_short_messages()
    test_emotional_responses()
    test_question_generation()
    test_message_splitting()
    test_stage_progression()
    test_conversation_flow()
    
    log_test("\n" + "="*60)
    log_test("🏁 ТЕСТЫ ЗАВЕРШЕНЫ")
    log_test("="*60)

if __name__ == "__main__":
    run_all_tests()
