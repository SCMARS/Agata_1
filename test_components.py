#!/usr/bin/env python3
"""
Тест компонентов системы живого общения
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.short_message_processor import short_message_processor
from app.utils.stage_controller import stage_controller
from app.utils.message_splitter import message_splitter

def test_short_message_processor():
    """Тест процессора коротких сообщений"""
    print("🧪 Тестируем ShortMessageProcessor...")
    
    messages = [
        {"role": "user", "content": "Привет"},
        {"role": "user", "content": "как дела"},
        {"role": "user", "content": "что делаешь"}
    ]
    
    result = short_message_processor.process_user_messages("test_user", messages)
    print(f"   Результат: {result}")
    return result

def test_stage_controller():
    """Тест контроллера стейджей"""
    print("🧪 Тестируем StageController...")
    
    stage = stage_controller.get_user_stage("test_user", 1)
    print(f"   Стейдж для 1 сообщения: {stage}")
    
    stage = stage_controller.get_user_stage("test_user", 5)
    print(f"   Стейдж для 5 сообщений: {stage}")
    
    stage = stage_controller.get_user_stage("test_user", 10)
    print(f"   Стейдж для 10 сообщений: {stage}")
    
    return stage

def test_message_splitter():
    """Тест разбивателя сообщений"""
    print("🧪 Тестируем MessageSplitter...")
    
    text = "Привет! Как дела? Я работаю над новыми проектами в маркетинге и изучаю трейдинг."
    result = message_splitter.split_message(text)
    print(f"   Исходный текст: {text}")
    print(f"   Результат: {result}")
    return result

if __name__ == "__main__":
    print("🚀 ТЕСТИРОВАНИЕ КОМПОНЕНТОВ СИСТЕМЫ")
    print("="*50)
    
    test_short_message_processor()
    print()
    test_stage_controller()
    print()
    test_message_splitter()
    
    print("\n✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
