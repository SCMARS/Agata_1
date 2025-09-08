#!/usr/bin/env python3
"""
Запуск сервера Agatha
"""
import sys
import os

# Добавляем путь к проекту
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Настройка окружения
os.environ.setdefault('PYTHONPATH', PROJECT_ROOT)

# Загружаем переменные из config.env
def load_env_file():
    """Загружает переменные окружения из config.env"""
    env_file = os.path.join(PROJECT_ROOT, 'config.env')
    if os.path.exists(env_file):
        print(f"📁 Загружаем config.env: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Переменные окружения загружены из config.env")
    else:
        print("⚠️ config.env не найден")

# Загружаем переменные окружения
load_env_file()

# Явно устанавливаем OpenAI API ключ если он есть в окружении
if 'OPENAI_API_KEY' in os.environ:
    print(f"🔑 OpenAI API Key found: {os.environ['OPENAI_API_KEY'][:20]}...")
else:
    print("⚠️ No OPENAI_API_KEY in environment")

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Configure logging with quiet mode option
QUIET_MODE = os.getenv('AGATHA_QUIET', 'false').lower() == 'true'

if QUIET_MODE:
    # Quiet mode - только критические ошибки
    logging.basicConfig(level=logging.ERROR)
    # Отключаем httpx логи
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.WARNING)
else:
    # Normal mode - полная информация для разработки
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


_pipeline = None
_executor = None

def get_pipeline():
    """Получить singleton instance pipeline - ТОЛЬКО ПОЛНЫЙ LANGGRAPH!"""
    global _pipeline
    if _pipeline is None:
        print("🚀 Initializing FULL LangGraph Pipeline...")
        try:
            from app.graph.pipeline import AgathaPipeline
            print("🔧 Creating AgathaPipeline instance...")
            _pipeline = AgathaPipeline()
            print("✅ FULL LangGraph Pipeline initialized successfully!")
            print("🎯 All components loaded: Memory, Behavioral Analysis, Prompt Composer")
            print(f"🤖 LLM Status: {'OpenAI API' if _pipeline.llm else 'Mock LLM'}")
        except Exception as e:
            print(f"❌ CRITICAL: Full pipeline failed: {e}")
            print("🔥 NO FALLBACKS! System requires full LangGraph to work!")
            import traceback
            traceback.print_exc()
            raise Exception(f"Pipeline initialization failed: {e}")
    return _pipeline

def get_executor():
    """Получить ThreadPoolExecutor"""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4)
    return _executor

def async_pipeline_wrapper(pipeline, user_id, messages, meta_time):
    """Wrapper для асинхронного вызова pipeline"""
    import asyncio
    try:
        # Создаем event loop для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(pipeline.process_chat(user_id, messages, meta_time))
    finally:
        loop.close()

def create_app():
    """Application factory - используем обновленный main.py"""
    try:
        # Импортируем обновленный app из main.py
        from app.api.main import create_app as create_main_app
        print("✅ Используем обновленный API с памятью")
        return create_main_app()
    except Exception as e:
        print(f"⚠️ Fallback к базовому API: {e}")
        
        # Fallback к базовому app
        app = Flask(__name__)
        CORS(app)
        
        # Health check endpoints
        @app.route('/healthz')
        def health_check():
            """Basic health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'service': 'agatha-api'
            }), 200
    
    @app.route('/readyz')
    def readiness_check():
        """Readiness check endpoint"""
        try:
            # Проверяем pipeline
            pipeline = get_pipeline()
            
            return jsonify({
                'status': 'ready',
                'checks': {
                    'pipeline': 'ok',
                    'memory': 'ok'
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 200
            
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return jsonify({
                'status': 'not_ready',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503
    
    # API Info endpoint
    @app.route('/api/info')
    def api_info():
        """API information endpoint"""
        return jsonify({
            'name': 'Agatha AI Companion API',
            'version': '1.0.0',
            'description': 'Virtual AI companion with modular pipeline',
            'endpoints': {
                'health': '/healthz',
                'readiness': '/readyz',
                'chat': '/api/chat',
                'memory_add': '/api/memory/<user_id>/add',
                'memory_search': '/api/memory/<user_id>/search',
                'memory_overview': '/api/memory/<user_id>/overview',
                'memory_clear': '/api/memory/<user_id>/clear',
                'swagger': '/api/docs'
            }
        })
    
    # Главный chat endpoint
    @app.route('/api/chat', methods=['POST'])
    def chat():
        """Main chat endpoint with Agatha pipeline"""
        try:
            data = request.get_json()
            
            # Validate input
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            user_id = data.get('user_id')
            messages = data.get('messages', [])
            meta_time = data.get('metaTime')
            
            if not user_id:
                return jsonify({'error': 'user_id is required'}), 400
            
            if not messages:
                return jsonify({'error': 'messages are required'}), 400
            
            # Получить pipeline singleton
            pipeline = get_pipeline()

            # Запустить async pipeline через executor
            executor = get_executor()
            response = executor.submit(async_pipeline_wrapper, pipeline, user_id, messages, meta_time).result(timeout=60)
            
            logger.info(f"✅ Chat request from user {user_id} with {len(messages)} messages processed")
            
            return jsonify(response)
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Chat endpoint error: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            print(f"🚨 DETAILED ERROR:")
            print(f"   Exception: {type(e).__name__}: {str(e)}")
            print(f"   Traceback:")
            traceback.print_exc()
            return jsonify({
                'error': 'Internal server error',
                'debug': str(e),
                'type': type(e).__name__
            }), 500

    # Memory endpoints
    @app.route('/api/memory/<user_id>/add', methods=['POST'])
    def add_to_memory(user_id):
        """Добавляет сообщение в память пользователя"""
        try:
            from app.memory.memory_levels import MemoryLevelsManager
            from app.memory.base import Message, MemoryContext
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'JSON data is required'}), 400
                
            content = data.get('content')
            if not content:
                return jsonify({'error': 'content is required'}), 400
            
            role = data.get('role', 'user')
            metadata = data.get('metadata', {})
            conversation_id = data.get('conversation_id', 'default')
            day_number = data.get('day_number', 1)
            
            # Создаем сообщение и контекст
            message = Message(
                content=content,
                role=role,
                metadata=metadata
            )
            
            context = MemoryContext(
                user_id=user_id,
                conversation_id=conversation_id,
                day_number=day_number
            )
            
            # Добавляем в память
            memory_manager = MemoryLevelsManager(user_id)
            result = memory_manager.add_message(message, context)
            
            return jsonify({
                'success': True,
                'message': 'Added to memory',
                'result': result,
                'user_id': user_id
            })
            
        except Exception as e:
            return jsonify({'error': str(e), 'type': type(e).__name__}), 500

    @app.route('/api/memory/<user_id>/search', methods=['POST'])
    def search_memory(user_id):
        """Поиск в памяти пользователя"""
        try:
            from app.memory.memory_levels import MemoryLevelsManager
            from app.memory.base import MemoryLevel
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'JSON data is required'}), 400
                
            query = data.get('query')
            if not query:
                return jsonify({'error': 'query is required'}), 400
            
            level = data.get('level', 'all')
            max_results = data.get('limit', 10)
            
            # Конвертируем уровень в enum если указан
            levels = None
            if level and level != 'all':
                level_enums = []
                if isinstance(level, list):
                    for l in level:
                        try:
                            level_enums.append(MemoryLevel(l))
                        except ValueError:
                            pass
                else:
                    try:
                        level_enums.append(MemoryLevel(level))
                    except ValueError:
                        pass
                levels = level_enums if level_enums else None

            # Выполняем поиск
            memory_manager = MemoryLevelsManager(user_id)
            results = memory_manager.search_memory(query, levels=levels, max_results=max_results)
            
            # Конвертируем результаты в JSON-совместимый формат
            serializable_results = []
            for result in results:
                serializable_results.append({
                    'content': result.content,
                    'source_level': result.source_level.value,
                    'relevance_score': result.relevance_score,
                    'metadata': result.metadata,
                    'created_at': result.created_at.isoformat() if result.created_at else None
                })

            return jsonify({
                'success': True,
                'query': query,
                'results': serializable_results,
                'total_found': len(serializable_results),
                'user_id': user_id
            })

        except Exception as e:
            return jsonify({'error': str(e), 'type': type(e).__name__}), 500

    @app.route('/api/memory/<user_id>/overview', methods=['GET'])
    def get_memory_overview(user_id):
        """Получает обзор памяти пользователя"""
        try:
            from app.memory.memory_levels import MemoryLevelsManager
            
            memory_manager = MemoryLevelsManager(user_id)
            overview = memory_manager.get_memory_overview()
            
            return jsonify({
                'success': True,
                'user_id': user_id,
                'overview': overview
            })

        except Exception as e:
            return jsonify({'error': str(e), 'type': type(e).__name__}), 500

    @app.route('/api/memory/<user_id>/clear', methods=['POST'])
    def clear_memory(user_id):
        """Очищает память пользователя"""
        try:
            from app.memory.memory_levels import MemoryLevelsManager
            
            memory_manager = MemoryLevelsManager(user_id)
            memory_manager.clear_all_memory()
            
            return jsonify({
                'success': True,
                'message': 'Memory cleared',
                'user_id': user_id
            })

        except Exception as e:
            return jsonify({'error': str(e), 'type': type(e).__name__}), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    print("🚀 Starting Agatha AI Companion Server...")
    print(f"📁 Project root: {PROJECT_ROOT}")
    
    app = create_app()
    
    # Инициализируем pipeline при запуске
    pipeline = get_pipeline()
    
    print("🎯 Server ready! Endpoints:")
    print("   - Health: http://localhost:8000/healthz")
    print("   - API Info: http://localhost:8000/api/info")
    print("   - Chat: POST http://localhost:8000/api/chat")
    
    # Используем настройки из settings
    from app.config.settings import settings
    app.run(
        host=settings.HOST,
        port=settings.PORT,
        debug=settings.DEBUG
    ) 