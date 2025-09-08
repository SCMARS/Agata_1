#!/usr/bin/env python3
"""
Простой тестовый сервер для проверки работы
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/healthz')
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Test server is working'
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_id = data.get('user_id', 'unknown')
    messages = data.get('messages', [])
    
    # Простой ответ
    response = {
        'response': 'Привет! Я тестовый сервер. Всё работает!',
        'user_id': user_id,
        'status': 'success'
    }
    
    return jsonify(response)

if __name__ == '__main__':
    print("🚀 Запуск тестового сервера...")
    print("🌐 http://localhost:8000")
    app.run(host='0.0.0.0', port=8000, debug=True)
