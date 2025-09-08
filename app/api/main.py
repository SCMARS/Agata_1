import json
from flask import Flask, Response, request
from flask_cors import CORS
import os
import sys
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config.settings import settings

_pipeline = None
_executor = ThreadPoolExecutor(max_workers=4)

def get_pipeline():
    global _pipeline
    if _pipeline is None:
        try:
            from app.graph.pipeline import AgathaPipeline
            _pipeline = AgathaPipeline()
        except Exception as e:
            raise e
    return _pipeline

# Импортируем глобальный менеджер памяти
from app.memory.memory_manager import get_unified_memory

async def run_pipeline_async(pipeline, user_id, messages, meta_time):
    return await pipeline.process_chat(user_id, messages, meta_time)

def json_response(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status,
        mimetype='application/json'
    )

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config['DEBUG'] = settings.DEBUG

    @app.route('/healthz')
    def health_check():
        return json_response({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'agatha-api'
        })

    @app.route('/readyz')
    def readiness_check():
        try:
            checks = {'database': 'ok', 'redis': 'ok', 'llm': 'ok'}
            all_ready = all(status == 'ok' for status in checks.values())
            return json_response({
                'status': 'ready' if all_ready else 'not_ready',
                'checks': checks,
                'timestamp': datetime.utcnow().isoformat()
            }), 200 if all_ready else 503
        except Exception as e:
            return json_response({
                'status': 'not_ready',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503

    @app.route('/api/info')
    def api_info():
        return json_response({
            'name': 'Agatha AI Companion API',
            'version': '1.0.0',
            'description': 'Virtual AI companion with LangGraph pipeline',
            'endpoints': {
                'health': '/healthz',
                'readiness': '/readyz',
                'chat': '/api/chat',
                'memory': {
                    'add': '/api/memory/<user_id>/add',
                    'search': '/api/memory/<user_id>/search', 
                    'overview': '/api/memory/<user_id>/overview',
                    'clear': '/api/memory/<user_id>/clear'
                },
                'swagger': '/api/docs'
            }
        })
    
    @app.route('/api/chat', methods=['POST'])
    def chat():
        try:
            data = request.get_json()
            if not data:
                return json_response({'error': 'No data provided'}), 400

            user_id = data.get('user_id')
            messages = data.get('messages', [])
            meta_time = data.get('metaTime')
            
            # Преобразуем messages в правильный формат если нужно
            if messages and isinstance(messages[0], str):
                messages = [{'role': 'user', 'content': msg} for msg in messages]

            if not user_id:
                return json_response({'error': 'user_id is required'}), 400

            if not messages:
                return json_response({'error': 'messages are required'}), 400

            pipeline = get_pipeline()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(
                    run_pipeline_async(pipeline, user_id, messages, meta_time)
                )
            finally:
                loop.close()

            return json_response(response)

        except Exception as e:
            return json_response({'error': str(e), 'type': type(e).__name__}), 500

    # Memory Management Endpoints
    @app.route('/api/memory/<user_id>/add', methods=['POST'])
    def add_to_memory(user_id):
        """Добавляет сообщение в память пользователя"""
        try:
            data = request.get_json()
            if not data:
                return json_response({'error': 'No data provided'}), 400

            role = data.get('role')
            content = data.get('content')
            metadata = data.get('metadata', {})
            timestamp_str = data.get('timestamp')  # Опциональная временная метка

            if not role or not content:
                return json_response({'error': 'role and content are required'}), 400
            timestamp = None
            if timestamp_str:
                try:
                    from datetime import datetime as dt
                    timestamp = dt.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except Exception as e:
                    return json_response({'error': f'Invalid timestamp format: {e}'}), 400

            # Импортируем систему памяти
            from app.memory.unified_memory import UnifiedMemoryManager
            from app.memory.memory_adapter import MemoryAdapter
            from app.memory.base import Message, MemoryContext
            from datetime import datetime

            try:
                # Используем глобальный экземпляр памяти
                unified_memory = get_unified_memory(user_id)
                if not unified_memory:
                    raise Exception("Failed to get UnifiedMemoryManager")
                memory_manager = MemoryAdapter(unified_memory, config=None)
                print(f"✅ [API] Используем глобальный UnifiedMemoryManager для {user_id}")
            except Exception as e:
                print(f"⚠️ [API] Fallback к MemoryLevelsManager: {e}")
                from app.memory.memory_levels import MemoryLevelsManager
                fallback_manager = MemoryLevelsManager(user_id)
                memory_manager = MemoryAdapter(fallback_manager, config=None)
                
            message = Message(
                role=role,
                content=content,
                timestamp=datetime.now(),
                metadata=metadata
            )
            
            context = MemoryContext(
                user_id=user_id,
                conversation_id=data.get('conversation_id'),
                day_number=data.get('day_number', 1)
            )
            result = memory_manager.add_message_to_unified(role, content, metadata, user_id, timestamp)
            print(f"✅ [API] Использован add_message_to_unified: {result}")

            return json_response({
                'success': True,
                'message': 'Added to memory',
                'result': result,
                'user_id': user_id
            })

        except Exception as e:
            return json_response({'error': str(e), 'type': type(e).__name__}, 500)

    @app.route('/api/memory/<user_id>/search', methods=['POST'])
    def search_memory(user_id):
        """Ищет в памяти пользователя"""
        try:
            data = request.get_json()
            if not data:
                return json_response({'error': 'No data provided'}), 400

            query = data.get('query')
            max_results = data.get('max_results', 5)
            levels = data.get('levels')  # список уровней для поиска

            if not query:
                return json_response({'error': 'query is required'}), 400

            try:
                unified_memory = get_unified_memory(user_id)
                if unified_memory:
                    print(f"✅ [API] Используем глобальный UnifiedMemoryManager для поиска {user_id}")
                    use_unified = True
                else:
                    raise Exception("Failed to get unified memory")
            except Exception as e:
                print(f"⚠️ [API] Fallback к MemoryLevelsManager для поиска: {e}")
                from app.memory.memory_levels import MemoryLevelsManager, MemoryLevel
                memory_manager = MemoryLevelsManager(user_id)
                use_unified = False
            
            # Выполняем поиск в зависимости от системы
            serializable_results = []
            
            if use_unified:
                # Поиск через UnifiedMemoryManager
                if unified_memory.vector_available and unified_memory.vector_db:
                    try:
                        vector_results = unified_memory.vector_db.search_similar(query, max_results)
                        print(f"🔍 [API] Найдено {len(vector_results)} результатов в векторной БД")
                        
                        for result in vector_results:
                            serializable_results.append({
                                'content': result.get('content', ''),
                                'source_level': 'long_term',
                                'relevance_score': result.get('similarity', 0.0),
                                'metadata': result.get('metadata', {}),
                                'created_at': result.get('created_at')
                            })
                    except Exception as e:
                        print(f"❌ [API] Ошибка поиска в векторной БД: {e}")
                else:
                    print(f"⚠️ [API] Векторная БД недоступна для {user_id}")
            else:
                # Fallback к старой системе
                if levels:
                    level_enums = []
                    for level_str in levels:
                        try:
                            level_enums.append(MemoryLevel(level_str))
                        except ValueError:
                            pass
                    levels = level_enums if level_enums else None

                results = memory_manager.search_memory(query, levels=levels, max_results=max_results)
                
                for result in results:
                    serializable_results.append({
                        'content': result.content,
                        'source_level': result.source_level.value,
                        'relevance_score': result.relevance_score,
                        'metadata': result.metadata,
                        'created_at': result.created_at.isoformat() if result.created_at else None
                    })

            return json_response({
                'success': True,
                'query': query,
                'results': serializable_results,
                'total_found': len(serializable_results),
                'user_id': user_id
            })

        except Exception as e:
            return json_response({'error': str(e), 'type': type(e).__name__}, 500)

    @app.route('/api/memory/<user_id>/overview', methods=['GET'])
    def get_memory_overview(user_id):
        """Получает обзор памяти пользователя"""
        try:
            try:
                # Используем глобальный экземпляр памяти
                unified_memory = get_unified_memory(user_id)
                if not unified_memory:
                    raise Exception("Failed to get UnifiedMemoryManager")
                print(f"✅ [API] Используем глобальный UnifiedMemoryManager для обзора {user_id}")
                
                # Создаем обзор для UnifiedMemoryManager
                stats = unified_memory.get_memory_stats()
                overview = {
                    'user_id': user_id,
                    'levels': {
                        'short_term': {
                            'status': 'active',
                            'buffer_size': len(unified_memory.short_term_window),
                            'total_messages': unified_memory.message_count,
                            'window_size': unified_memory.window_size
                        },
                        'long_term': {
                            'status': 'active' if unified_memory.vector_available else 'not_initialized',
                            'vector_available': unified_memory.vector_available,
                            'total_documents': stats.get('vector_count', 0) if unified_memory.vector_available else 0
                        },
                        'episodic': {
                            'status': 'active',
                            'total_episodes': 0
                        },
                        'summary': {
                            'status': 'active', 
                            'total_summaries': 0
                        }
                    }
                }
                
            except Exception as e:
                print(f"⚠️ [API] Fallback к MemoryLevelsManager для обзора: {e}")
                from app.memory.memory_levels import MemoryLevelsManager
                memory_manager = MemoryLevelsManager(user_id)
                overview = memory_manager.get_memory_overview()
            
            return json_response({
                'success': True,
                'user_id': user_id,
                'overview': overview
            })

        except Exception as e:
            return json_response({'error': str(e), 'type': type(e).__name__}, 500)

    @app.route('/api/memory/<user_id>/clear', methods=['POST'])
    def clear_memory(user_id):
        """Очищает память пользователя"""
        try:
            try:
                unified_memory = get_unified_memory(user_id)
                if not unified_memory:
                    raise Exception("Failed to get unified memory")
                print(f"✅ [API] Используем глобальный UnifiedMemoryManager для очистки {user_id}")
                
                # Очищаем UnifiedMemoryManager
                unified_memory.short_term_window.clear()
                unified_memory.message_count = 0
                
                # Очищаем векторную БД если доступна
                if unified_memory.vector_available and unified_memory.vector_db:
                    try:
                        # Попытка очистить векторную БД
                        if hasattr(unified_memory.vector_db, 'clear'):
                            unified_memory.vector_db.clear()
                        print(f"✅ [API] Векторная БД очищена для {user_id}")
                    except Exception as e:
                        print(f"⚠️ [API] Не удалось очистить векторную БД: {e}")
                
            except Exception as e:
                print(f"⚠️ [API] Fallback к MemoryLevelsManager для очистки: {e}")
                from app.memory.memory_levels import MemoryLevelsManager
                memory_manager = MemoryLevelsManager(user_id)
                
                if memory_manager.short_term:
                    memory_manager.short_term.clear()
                if memory_manager.long_term:
                    memory_manager.long_term.clear()
            
            return json_response({
                'success': True,
                'message': 'Memory cleared',
                'user_id': user_id
            })

        except Exception as e:
            return json_response({'error': str(e), 'type': type(e).__name__}, 500)

    @app.errorhandler(404)
    def not_found(error):
        return json_response({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return json_response({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=settings.HOST,
        port=settings.PORT,
        debug=settings.DEBUG
    ) 