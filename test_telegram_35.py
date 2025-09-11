#!/usr/bin/env python3
"""
Полный тест Telegram бота - 35 сообщений
Проверяем: частота вопросов, смены стейджей, правильность вопросов
"""

import requests
import json
import time

def test_message(user_id, messages):
    """Отправляет сообщение и возвращает результат"""
    url = "http://localhost:8000/api/chat"
    data = {
        "user_id": user_id,
        "messages": messages
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "response": result.get("response", ""),
                "stage_number": result.get("stage_number", 1),
                "has_question": result.get("has_question", False)
            }
        else:
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    user_id = "telegram_test_35"
    messages = []
    
    print("🚀 НАЧИНАЕМ ПОЛНЫЙ ТЕСТ TELEGRAM БОТА - 35 СООБЩЕНИЙ")
    print("=" * 60)
    print("Проверяем: частота вопросов (каждое 2-е), смены стейджей (1→2→3), правильность вопросов")
    print("=" * 60)
    
    # Ожидаемые результаты
    expected_questions = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34]  # четные сообщения
    expected_stage1 = list(range(1, 11))  # сообщения 1-10
    expected_stage2 = list(range(11, 21))  # сообщения 11-20
    expected_stage3 = list(range(21, 36))  # сообщения 21-35
    
    results = []
    
    for i in range(1, 36):  # 35 сообщений
        print(f"\n📨 СООБЩЕНИЕ {i}:")
        
        # Добавляем сообщение пользователя
        messages.append({"role": "user", "content": str(i)})
        
        # Отправляем запрос
        result = test_message(user_id, messages.copy())
        
        if result["success"]:
            stage = result["stage_number"]
            has_q = result["has_question"]
            response = result["response"][:100] + "..." if len(result["response"]) > 100 else result["response"]
            
            # Анализируем результат
            should_have_question = i in expected_questions
            question_status = "✅ ВОПРОС" if has_q else "❌ НЕТ ВОПРОСА"
            if should_have_question and not has_q:
                question_status += " (ОШИБКА!)"
            elif not should_have_question and has_q:
                question_status += " (ОШИБКА!)"
            
            # Проверяем стейдж
            if i in expected_stage1 and stage == 1:
                stage_status = "✅ STAGE 1"
            elif i in expected_stage2 and stage == 2:
                stage_status = "✅ STAGE 2"
            elif i in expected_stage3 and stage == 3:
                stage_status = "✅ STAGE 3"
            else:
                stage_status = f"❌ STAGE {stage} (ОШИБКА!)"
            
            print(f"   Ответ: {response}")
            print(f"   {question_status} | {stage_status}")
            
            results.append({
                "message": i,
                "stage": stage,
                "has_question": has_q,
                "should_have_question": should_have_question,
                "correct_stage": i in expected_stage1 and stage == 1 or i in expected_stage2 and stage == 2 or i in expected_stage3 and stage == 3
            })
            
            # Добавляем ответ бота в историю
            messages.append({"role": "assistant", "content": result["response"]})
            
        else:
            print(f"   ❌ ОШИБКА: {result['error']}")
            break
        
        # Небольшая пауза между запросами
        time.sleep(0.5)
    
    # Итоговая статистика
    print("\n" + "=" * 60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА:")
    print("=" * 60)
    
    total_messages = len(results)
    correct_questions = sum(1 for r in results if r["has_question"] == r["should_have_question"])
    correct_stages = sum(1 for r in results if r["correct_stage"])
    
    print(f"Всего сообщений: {total_messages}")
    print(f"Правильные вопросы: {correct_questions}/{total_messages} ({correct_questions/total_messages*100:.1f}%)")
    print(f"Правильные стейджи: {correct_stages}/{total_messages} ({correct_stages/total_messages*100:.1f}%)")
    
    # Детальный анализ
    print("\n🔍 ДЕТАЛЬНЫЙ АНАЛИЗ:")
    
    # Анализ вопросов
    question_errors = [r for r in results if r["has_question"] != r["should_have_question"]]
    if question_errors:
        print(f"❌ Ошибки в вопросах ({len(question_errors)}):")
        for error in question_errors:
            status = "был" if error["has_question"] else "не было"
            should = "должен" if error["should_have_question"] else "не должен"
            print(f"   Сообщение {error['message']}: вопрос {status}, но {should} быть")
    else:
        print("✅ Все вопросы правильные!")
    
    # Анализ стейджей
    stage_errors = [r for r in results if not r["correct_stage"]]
    if stage_errors:
        print(f"❌ Ошибки в стейджах ({len(stage_errors)}):")
        for error in stage_errors:
            print(f"   Сообщение {error['message']}: STAGE {error['stage']} (должен быть другой)")
    else:
        print("✅ Все стейджи правильные!")
    
    # Переходы между стейджами
    print("\n🔄 ПЕРЕХОДЫ МЕЖДУ СТЕЙДЖАМИ:")
    stage_transitions = []
    prev_stage = None
    for r in results:
        if prev_stage is not None and r["stage"] != prev_stage:
            stage_transitions.append(f"Сообщение {r['message']}: STAGE {prev_stage} → STAGE {r['stage']}")
        prev_stage = r["stage"]
    
    for transition in stage_transitions:
        print(f"   {transition}")
    
    print("\n🎯 ТЕСТ ЗАВЕРШЕН!")

if __name__ == "__main__":
    main()
