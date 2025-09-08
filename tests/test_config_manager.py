
import os
import json
import yaml
import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Импорт тестируемого модуля
import sys
sys.path.append(str(Path(__file__).parent.parent))

from app.config.production_config_manager import (
    ProductionConfigManager, 
    ConfigManagerConfig,
    ConfigCache,
    CacheEntry
)


class TestConfigCache:
    """Тесты для ConfigCache"""
    
    def test_cache_basic_operations(self):
        """Тест базовых операций кеша"""
        cache = ConfigCache(max_size=3)
        
        # Добавление и получение
        cache.set('key1', {'value': 1}, ttl_seconds=60)
        result = cache.get('key1')
        assert result == {'value': 1}
        
        # Несуществующий ключ
        result = cache.get('nonexistent')
        assert result is None
    
    def test_cache_ttl_expiration(self):
        """Тест истечения TTL"""
        cache = ConfigCache()
        
        # Добавляем с коротким TTL
        cache.set('short_ttl', {'temp': True}, ttl_seconds=1)
        
        # Сразу должно быть доступно
        result = cache.get('short_ttl')
        assert result == {'temp': True}
        
        # Ждем истечения TTL
        time.sleep(1.1)
        
        # Должно быть недоступно
        result = cache.get('short_ttl')
        assert result is None
    
    def test_cache_namespace_isolation(self):
        """Тест изоляции namespace"""
        cache = ConfigCache()
        
        # Добавляем в разные namespace
        cache.set('key1', {'ns1': True}, ttl_seconds=60, namespace='ns1')
        cache.set('key1', {'ns2': True}, ttl_seconds=60, namespace='ns2')
        
        # Проверяем изоляцию
        result1 = cache.get('key1', namespace='ns1')
        result2 = cache.get('key1', namespace='ns2')
        
        assert result1 == {'ns1': True}
        assert result2 == {'ns2': True}
    
    def test_cache_invalidation(self):
        """Тест инвалидации кеша"""
        cache = ConfigCache()
        
        # Добавляем данные в разные namespace
        cache.set('key1', {'value': 1}, ttl_seconds=60, namespace='ns1')
        cache.set('key2', {'value': 2}, ttl_seconds=60, namespace='ns1')
        cache.set('key1', {'value': 3}, ttl_seconds=60, namespace='ns2')
        
        # Инвалидируем namespace
        removed_count = cache.invalidate(namespace='ns1')
        assert removed_count == 2
        
        # Проверяем что ns1 очищен, а ns2 остался
        assert cache.get('key1', namespace='ns1') is None
        assert cache.get('key2', namespace='ns1') is None
        assert cache.get('key1', namespace='ns2') == {'value': 3}
    
    def test_cache_lru_eviction(self):
        """Тест LRU вытеснения"""
        cache = ConfigCache(max_size=3)
        
        # Заполняем кеш до максимума
        cache.set('key1', {'value': 1}, ttl_seconds=60)
        cache.set('key2', {'value': 2}, ttl_seconds=60)
        cache.set('key3', {'value': 3}, ttl_seconds=60)
        
        # Обращаемся к key1 чтобы сделать его "свежим"
        cache.get('key1')
        
        # Добавляем еще один элемент, должен вытеснить key2 (самый старый)
        cache.set('key4', {'value': 4}, ttl_seconds=60)
        
        assert cache.get('key1') == {'value': 1}  # Должен остаться
        assert cache.get('key2') is None  # Должен быть вытеснен
        assert cache.get('key3') == {'value': 3}  # Должен остаться
        assert cache.get('key4') == {'value': 4}  # Новый элемент


class TestConfigManagerConfig:
    """Тесты для ConfigManagerConfig"""
    
    def test_default_config_from_env(self):
        """Тест создания конфигурации из переменных окружения"""
        # Сохраняем оригинальные значения
        original_env = os.environ.copy()
        
        try:
            # Устанавливаем тестовые переменные
            os.environ.update({
                'CONFIG_DIR': '/test/config',
                'DB_POOL_MIN': '5',
                'DB_POOL_MAX': '20',
                'CONFIG_CACHE_TTL': '600',
                'APP_ENVIRONMENT': 'testing'
            })
            
            config = ConfigManagerConfig()
            
            assert config.config_dir == '/test/config'
            assert config.db_pool_min_connections == 5
            assert config.db_pool_max_connections == 20
            assert config.cache_ttl_seconds == 600
            assert config.environment == 'testing'
            
        finally:
            # Восстанавливаем оригинальные переменные
            os.environ.clear()
            os.environ.update(original_env)


class TestProductionConfigManager:
    """Тесты для ProductionConfigManager"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Создает временную директорию с тестовыми конфигами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Создаем тестовые файлы конфигурации
            test_configs = {
                'memory_thresholds.yml': {
                    'semantic_similarity': 0.5,
                    'fact_confidence_min': 0.7,
                    'importance_threshold': 0.6
                },
                'search_weights.json': {
                    'deterministic_facts': 1.0,
                    'fuzzy_text': 0.7,
                    'semantic_vector': 0.6
                },
                'test_config.yaml': {
                    'nested': {
                        'param1': 'value1',
                        'param2': 42
                    },
                    'simple_param': True
                }
            }
            
            for filename, content in test_configs.items():
                file_path = config_dir / filename
                with open(file_path, 'w') as f:
                    if filename.endswith('.json'):
                        json.dump(content, f)
                    else:
                        yaml.dump(content, f)
            
            yield str(config_dir)
    
    @pytest.fixture
    def config_manager_no_db(self, temp_config_dir):
        """Создает ConfigManager без БД для тестов"""
        config = ConfigManagerConfig(
            config_dir=temp_config_dir,
            db_connection_string=None,  # Отключаем БД
            auto_reload=False,  # Отключаем auto-reload для тестов
            cache_ttl_seconds=60
        )
        
        manager = ProductionConfigManager(config)
        yield manager
        
        # Очистка
        manager.shutdown()
    
    def test_fallback_config_loading(self, config_manager_no_db):
        """Тест загрузки fallback конфигураций из файлов"""
        manager = config_manager_no_db
        
        # Проверяем что файлы загружены
        assert len(manager._fallback_configs) == 3
        assert 'memory_thresholds' in manager._fallback_configs
        assert 'search_weights' in manager._fallback_configs
        assert 'test_config' in manager._fallback_configs
        
        # Проверяем содержимое
        thresholds = manager._fallback_configs['memory_thresholds']
        assert thresholds['semantic_similarity'] == 0.5
        assert thresholds['fact_confidence_min'] == 0.7
    
    def test_config_retrieval_fallback_only(self, config_manager_no_db):
        """Тест получения конфигурации только из fallback файлов"""
        manager = config_manager_no_db
        
        # Получаем конфигурацию
        config = manager.get_config('memory_thresholds')
        
        assert config['semantic_similarity'] == 0.5
        assert config['fact_confidence_min'] == 0.7
        assert config['importance_threshold'] == 0.6
    
    def test_env_overrides(self, config_manager_no_db):
        """Тест переопределений через переменные окружения"""
        manager = config_manager_no_db
        
        # Сохраняем оригинальные значения
        original_env = os.environ.copy()
        
        try:
            # Устанавливаем переопределения
            os.environ.update({
                'MEMORY__TEST_CONFIG__NESTED__PARAM1': 'overridden_value',
                'MEMORY__TEST_CONFIG__NESTED__NEW_PARAM': 'new_value',
                'MEMORY__TEST_CONFIG__SIMPLE_PARAM': 'false',
                'MEMORY__TEST_CONFIG__NUMBER_PARAM': '123',
                'MEMORY__TEST_CONFIG__FLOAT_PARAM': '3.14',
                'MEMORY__TEST_CONFIG__JSON_PARAM': '{"key": "value"}'
            })
            
            # Получаем конфигурацию с переопределениями
            config = manager.get_config('test_config', force_reload=True)
            
            # Проверяем что переопределения применились
            assert config['nested']['param1'] == 'overridden_value'
            assert config['nested']['new_param'] == 'new_value'
            assert config['nested']['param2'] == 42  # Оригинальное значение
            assert config['simple_param'] is False  # Парсинг boolean
            assert config['number_param'] == 123  # Парсинг int
            assert config['float_param'] == 3.14  # Парсинг float
            assert config['json_param'] == {"key": "value"}  # Парсинг JSON
            
        finally:
            # Восстанавливаем переменные окружения
            os.environ.clear()
            os.environ.update(original_env)
    
    def test_cache_functionality(self, config_manager_no_db):
        """Тест функциональности кеша"""
        manager = config_manager_no_db
        
        # Первый запрос - должен попасть в кеш
        config1 = manager.get_config('memory_thresholds')
        
        # Проверяем метрики
        assert manager._metrics['config_requests'] > 0
        assert manager._metrics['cache_misses'] > 0
        
        # Второй запрос - должен быть из кеша
        cache_misses_before = manager._metrics['cache_misses']
        config2 = manager.get_config('memory_thresholds')
        
        assert config1 == config2
        assert manager._metrics['cache_hits'] > 0
        assert manager._metrics['cache_misses'] == cache_misses_before  # Не должно увеличиться
    
    def test_force_reload(self, config_manager_no_db):
        """Тест принудительной перезагрузки"""
        manager = config_manager_no_db
        
        # Получаем конфигурацию и кешируем
        config1 = manager.get_config('memory_thresholds')
        
        # Принудительная перезагрузка
        cache_misses_before = manager._metrics['cache_misses']
        config2 = manager.get_config('memory_thresholds', force_reload=True)
        
        assert config1 == config2
        assert manager._metrics['cache_misses'] > cache_misses_before  # Должно увеличиться
    
    def test_default_values(self, config_manager_no_db):
        """Тест возврата значений по умолчанию"""
        manager = config_manager_no_db
        
        # Запрос несуществующей конфигурации с default
        config = manager.get_config('nonexistent_config', default={'default_value': True})
        
        assert config == {'default_value': True}
        
        # Запрос без default
        config = manager.get_config('another_nonexistent')
        assert config == {}
    
    @patch('app.config.production_config_manager.psycopg2')
    def test_db_unavailable_fallback(self, mock_psycopg2, temp_config_dir):
        """Тест fallback при недоступности БД"""
        # Настраиваем мок для симуляции ошибки БД
        mock_psycopg2.pool.ThreadedConnectionPool.side_effect = Exception("DB connection failed")
        
        config = ConfigManagerConfig(
            config_dir=temp_config_dir,
            db_connection_string="postgresql://fake_url",
            auto_reload=False
        )
        
        manager = ProductionConfigManager(config)
        
        try:
            # Проверяем что БД недоступна
            assert manager._db_pool is None
            
            # Но fallback конфигурации работают
            config = manager.get_config('memory_thresholds')
            assert config['semantic_similarity'] == 0.5
            
            # Проверяем метрику fallback
            assert manager._metrics['db_fallbacks'] > 0
            
        finally:
            manager.shutdown()
    
    def test_file_watching_simulation(self, config_manager_no_db, temp_config_dir):
        """Тест имитации file watching (без реального watcher)"""
        manager = config_manager_no_db
        
        # Проверяем что файлы отслеживаются
        assert len(manager._file_watchers) > 0
        
        # Получаем путь к файлу конфигурации
        config_file = Path(temp_config_dir) / 'memory_thresholds.yml'
        file_path_str = str(config_file)
        
        # Проверяем что файл в списке отслеживаемых
        assert file_path_str in manager._file_watchers
        
        # Симулируем изменение файла
        old_mtime = manager._file_watchers[file_path_str]
        
        # Изменяем файл
        new_content = {
            'semantic_similarity': 0.8,  # Изменено значение
            'fact_confidence_min': 0.7,
            'importance_threshold': 0.6
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(new_content, f)
        
        # Обновляем mtime вручную (имитация file watcher)
        manager._file_watchers[file_path_str] = config_file.stat().st_mtime
        manager._reload_file_config(config_file)
        
        # Проверяем что конфигурация обновилась
        config = manager.get_config('memory_thresholds', force_reload=True)
        assert config['semantic_similarity'] == 0.8
    
    def test_metrics_recording(self, config_manager_no_db):
        """Тест записи метрик"""
        manager = config_manager_no_db
        
        # Выполняем несколько операций
        manager.get_config('memory_thresholds')
        manager.get_config('search_weights')
        manager.get_config('nonexistent_config')
        
        # Проверяем метрики
        stats = manager.get_stats()
        
        assert stats['metrics']['config_requests'] >= 3
        assert stats['metrics']['cache_misses'] >= 3
        assert 'cache_stats' in stats
        assert 'fallback_configs_count' in stats
    
    def test_secret_masking(self, config_manager_no_db):
        """Тест маскирования секретов"""
        manager = config_manager_no_db
        
        # Создаем конфигурацию с секретами
        test_config = {
            'api_key': 'secret123',
            'password': 'password123',
            'public_setting': 'public_value',
            'nested': {
                'token': 'token123',
                'normal_param': 'normal_value'
            }
        }
        
        # Тестируем маскирование
        masked = manager._mask_secrets(test_config)
        
        assert masked['api_key'] == '***MASKED***'
        assert masked['password'] == '***MASKED***'
        assert masked['public_setting'] == 'public_value'
        assert masked['nested']['token'] == '***MASKED***'
        assert masked['nested']['normal_param'] == 'normal_value'
    
    def test_deep_merge(self, config_manager_no_db):
        """Тест глубокого слияния конфигураций"""
        manager = config_manager_no_db
        
        base = {
            'level1': {
                'level2': {
                    'param1': 'base_value1',
                    'param2': 'base_value2'
                },
                'simple_param': 'base_simple'
            },
            'top_level': 'base_top'
        }
        
        override = {
            'level1': {
                'level2': {
                    'param1': 'override_value1',  # Переопределяется
                    'param3': 'new_value3'        # Добавляется
                },
                'new_simple_param': 'override_simple'  # Добавляется
            },
            'new_top_level': 'override_top'  # Добавляется
        }
        
        result = manager._deep_merge(base, override)
        
        # Проверяем результат
        assert result['level1']['level2']['param1'] == 'override_value1'  # Переопределено
        assert result['level1']['level2']['param2'] == 'base_value2'      # Сохранено
        assert result['level1']['level2']['param3'] == 'new_value3'       # Добавлено
        assert result['level1']['simple_param'] == 'base_simple'          # Сохранено
        assert result['level1']['new_simple_param'] == 'override_simple'  # Добавлено
        assert result['top_level'] == 'base_top'                          # Сохранено
        assert result['new_top_level'] == 'override_top'                  # Добавлено
    
    @patch('app.config.production_config_manager.psycopg2')
    def test_notify_simulation(self, mock_psycopg2, temp_config_dir):
        """Тест имитации NOTIFY уведомлений"""
        # Настраиваем мок для БД
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool = MagicMock()
        
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_psycopg2.pool.ThreadedConnectionPool.return_value = mock_pool
        
        config = ConfigManagerConfig(
            config_dir=temp_config_dir,
            db_connection_string="postgresql://test",
            auto_reload=True  # Включаем auto-reload
        )
        
        manager = ProductionConfigManager(config)
        
        try:
            # Проверяем что БД инициализирована
            assert manager._db_pool is not None
            
            # Симулируем получение уведомления
            config_key = 'memory_thresholds'
            manager._invalidate_config_cache(config_key)
            
            # Проверяем что кеш был очищен
            # (более детальная проверка потребовала бы полной имитации LISTEN/NOTIFY)
            
        finally:
            manager.shutdown()


def test_env_parsing():
    """Тест парсинга переменных окружения"""
    config = ConfigManagerConfig()
    manager = ProductionConfigManager(config)
    
    # Тест различных типов значений
    test_cases = [
        ('true', True),
        ('false', False),
        ('null', None),
        ('42', 42),
        ('3.14', 3.14),
        ('{"key": "value"}', {"key": "value"}),
        ('[1, 2, 3]', [1, 2, 3]),
        ('simple_string', 'simple_string'),
        ('', None)
    ]
    
    for input_value, expected in test_cases:
        result = manager._parse_env_value(input_value)
        assert result == expected, f"Failed for input: {input_value}"
    
    manager.shutdown()


def test_concurrent_access():
    """Тест параллельного доступа к конфигурации"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Создаем тестовый конфиг
        config_file = Path(temp_dir) / 'test.yml'
        with open(config_file, 'w') as f:
            yaml.dump({'test_param': 'test_value'}, f)
        
        config = ConfigManagerConfig(
            config_dir=temp_dir,
            db_connection_string=None,
            auto_reload=False,
            cache_ttl_seconds=60
        )
        
        manager = ProductionConfigManager(config)
        
        try:
            results = []
            errors = []
            
            def worker():
                try:
                    for i in range(100):
                        config = manager.get_config('test')
                        results.append(config.get('test_param'))
                except Exception as e:
                    errors.append(e)
            
            # Запускаем несколько потоков
            threads = []
            for _ in range(10):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()
            
            # Ждем завершения
            for thread in threads:
                thread.join()
            
            # Проверяем результаты
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(results) == 1000  # 10 потоков * 100 запросов
            assert all(r == 'test_value' for r in results)
            
        finally:
            manager.shutdown()


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])
