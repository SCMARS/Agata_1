"""
Production-ready динамический загрузчик конфигурации без хардкода
Поддерживает connection pool, hot-reload, потокобезопасность
"""
import os
import json
import yaml
import time
import logging
import threading
import select
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict
from threading import Lock, Thread
import weakref

# Импорты для БД с fallback
try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    psycopg2 = None

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Элемент кеша с TTL"""
    value: Any
    created_at: datetime
    ttl_seconds: int
    namespace: str = 'default'
    
    @property
    def is_expired(self) -> bool:
        """Проверяет истек ли TTL"""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)


@dataclass
class ConfigManagerConfig:
    """Конфигурация самого менеджера конфигурации"""
    # Источники конфигурации
    config_dir: str = field(default_factory=lambda: os.getenv('CONFIG_DIR', './app/config'))
    file_patterns: List[str] = field(default_factory=lambda: ['*.yml', '*.yaml', '*.json'])
    
    # База данных
    db_connection_string: Optional[str] = field(default_factory=lambda: os.getenv('DATABASE_URL'))
    db_pool_min_connections: int = field(default_factory=lambda: int(os.getenv('DB_POOL_MIN', '2')))
    db_pool_max_connections: int = field(default_factory=lambda: int(os.getenv('DB_POOL_MAX', '10')))
    db_connect_timeout: int = field(default_factory=lambda: int(os.getenv('DB_CONNECT_TIMEOUT', '10')))
    
    # Кеширование
    cache_ttl_seconds: int = field(default_factory=lambda: int(os.getenv('CONFIG_CACHE_TTL', '300')))
    cache_max_size: int = field(default_factory=lambda: int(os.getenv('CONFIG_CACHE_MAX_SIZE', '1000')))
    
    # Hot-reload
    auto_reload: bool = field(default_factory=lambda: os.getenv('CONFIG_AUTO_RELOAD', 'true').lower() == 'true')
    file_watch_enabled: bool = field(default_factory=lambda: os.getenv('CONFIG_FILE_WATCH', 'true').lower() == 'true')
    db_listen_channel: str = field(default_factory=lambda: os.getenv('CONFIG_LISTEN_CHANNEL', 'memory_config_updates'))
    
    # Окружение
    environment: str = field(default_factory=lambda: os.getenv('APP_ENVIRONMENT', 'production'))
    env_prefix: str = field(default_factory=lambda: os.getenv('CONFIG_ENV_PREFIX', 'MEMORY'))
    env_separator: str = '__'
    
    # Логирование
    log_level: str = field(default_factory=lambda: os.getenv('CONFIG_LOG_LEVEL', 'INFO'))
    log_config_access: bool = field(default_factory=lambda: os.getenv('CONFIG_LOG_ACCESS', 'false').lower() == 'true')
    mask_secrets: bool = field(default_factory=lambda: os.getenv('CONFIG_MASK_SECRETS', 'true').lower() == 'true')
    
    # Метрики
    metrics_enabled: bool = field(default_factory=lambda: os.getenv('CONFIG_METRICS_ENABLED', 'true').lower() == 'true')


class ConfigCache:
    """Потокобезопасный кеш с TTL и namespace support"""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._access_times: Dict[str, datetime] = {}
        self._lock = Lock()
        self._max_size = max_size
    
    def get(self, key: str, namespace: str = 'default') -> Optional[Any]:
        """Получает значение из кеша"""
        cache_key = f"{namespace}:{key}"
        
        with self._lock:
            entry = self._cache.get(cache_key)
            if not entry:
                return None
            
            if entry.is_expired:
                del self._cache[cache_key]
                if cache_key in self._access_times:
                    del self._access_times[cache_key]
                return None
            
            self._access_times[cache_key] = datetime.now()
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: int, namespace: str = 'default') -> None:
        """Сохраняет значение в кеше"""
        cache_key = f"{namespace}:{key}"
        
        with self._lock:
            # Очистка переполненного кеша
            if len(self._cache) >= self._max_size:
                self._evict_lru()
            
            self._cache[cache_key] = CacheEntry(
                value=value,
                created_at=datetime.now(),
                ttl_seconds=ttl_seconds,
                namespace=namespace
            )
            self._access_times[cache_key] = datetime.now()
    
    def invalidate(self, key: Optional[str] = None, namespace: Optional[str] = None) -> int:
        """Инвалидирует кеш по ключу или namespace"""
        removed_count = 0
        
        with self._lock:
            if key and namespace:
                # Инвалидация конкретного ключа
                cache_key = f"{namespace}:{key}"
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    if cache_key in self._access_times:
                        del self._access_times[cache_key]
                    removed_count = 1
                    
            elif namespace:
                # Инвалидация всего namespace
                keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{namespace}:")]
                for cache_key in keys_to_remove:
                    del self._cache[cache_key]
                    if cache_key in self._access_times:
                        del self._access_times[cache_key]
                    removed_count += 1
                    
            else:
                # Полная очистка кеша
                removed_count = len(self._cache)
                self._cache.clear()
                self._access_times.clear()
        
        return removed_count
    
    def _evict_lru(self) -> None:
        """Удаляет наименее недавно используемые элементы"""
        if not self._access_times:
            return
        
        # Удаляем 10% самых старых элементов
        sorted_by_access = sorted(self._access_times.items(), key=lambda x: x[1])
        to_remove = max(1, len(sorted_by_access) // 10)
        
        for cache_key, _ in sorted_by_access[:to_remove]:
            if cache_key in self._cache:
                del self._cache[cache_key]
            del self._access_times[cache_key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кеша"""
        with self._lock:
            expired_count = sum(1 for entry in self._cache.values() if entry.is_expired)
            namespaces = defaultdict(int)
            for key in self._cache.keys():
                namespace = key.split(':', 1)[0]
                namespaces[namespace] += 1
            
            return {
                'total_entries': len(self._cache),
                'expired_entries': expired_count,
                'max_size': self._max_size,
                'namespaces': dict(namespaces)
            }


class ProductionConfigManager:
    """Production-ready менеджер конфигурации"""
    
    def __init__(self, config: Optional[ConfigManagerConfig] = None):
        self.config = config or ConfigManagerConfig()
        
        # Настройка логирования
        logging.basicConfig(level=getattr(logging, self.config.log_level.upper()))
        
        # Инициализация компонентов
        self._cache = ConfigCache(self.config.cache_max_size)
        self._db_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        self._fallback_configs: Dict[str, Dict[str, Any]] = {}
        self._file_watchers: Dict[str, float] = {}  # file_path -> last_modified
        
        # Управление потоками
        self._shutdown_event = threading.Event()
        self._reload_thread: Optional[Thread] = None
        self._listener_thread: Optional[Thread] = None
        
        # Callback для уведомлений об изменениях
        self._change_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # Метрики
        self._metrics = {
            'config_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'db_fallbacks': 0,
            'file_fallbacks': 0,
            'hot_reloads': 0,
            'errors': 0
        }
        self._metrics_lock = Lock()
        
        logger.info(f"Initializing ProductionConfigManager for environment: {self.config.environment}")
        
        # Инициализация
        self._initialize()
    
    def _initialize(self):
        """Инициализация менеджера"""
        try:
            # 1. Загружаем fallback конфигурации из файлов
            self._load_fallback_configs()
            
            # 2. Инициализируем подключение к БД
            if DB_AVAILABLE and self.config.db_connection_string:
                self._init_db_pool()
            else:
                logger.warning("Database not available or not configured, using file-only mode")
            
            # 3. Запускаем hot-reload если нужно
            if self.config.auto_reload:
                self._start_auto_reload()
            
            logger.info("ProductionConfigManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ConfigManager: {e}")
            self._record_error("initialization_failed", str(e))
            # Не падаем, работаем в режиме fallback
    
    def _load_fallback_configs(self):
        """Загружает fallback конфигурации из файлов"""
        config_dir = Path(self.config.config_dir)
        
        if not config_dir.exists():
            logger.warning(f"Config directory not found: {config_dir}")
            return
        
        loaded_count = 0
        
        for pattern in self.config.file_patterns:
            for config_file in config_dir.glob(pattern):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        if config_file.suffix.lower() in ['.yml', '.yaml']:
                            data = yaml.safe_load(f)
                        else:
                            data = json.load(f)
                    
                    if data:
                        config_key = config_file.stem
                        self._fallback_configs[config_key] = data
                        self._file_watchers[str(config_file)] = config_file.stat().st_mtime
                        loaded_count += 1
                        
                        logger.debug(f"Loaded fallback config: {config_key}")
                        
                except Exception as e:
                    logger.error(f"Failed to load config file {config_file}: {e}")
                    self._record_error("file_load_failed", str(e))
        
        logger.info(f"Loaded {loaded_count} fallback configuration files")
    
    def _init_db_pool(self):
        """Инициализирует пул подключений к БД"""
        try:
            self._db_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.config.db_pool_min_connections,
                maxconn=self.config.db_pool_max_connections,
                dsn=self.config.db_connection_string,
                connect_timeout=self.config.db_connect_timeout
            )
            
            # Тестируем подключение
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            
            logger.info(f"Database pool initialized: {self.config.db_pool_min_connections}-{self.config.db_pool_max_connections} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            self._record_error("db_pool_init_failed", str(e))
            self._db_pool = None
    
    def _get_db_connection(self):
        """Получает подключение из пула"""
        if not self._db_pool:
            raise RuntimeError("Database pool not available")
        
        return self._db_pool.getconn()
    
    def _return_db_connection(self, conn, close=False):
        """Возвращает подключение в пул"""
        if self._db_pool and conn:
            self._db_pool.putconn(conn, close=close)
    
    def _start_auto_reload(self):
        """Запускает auto-reload потоки"""
        if self.config.file_watch_enabled:
            self._reload_thread = Thread(
                target=self._file_watch_loop,
                name="ConfigFileWatcher",
                daemon=True
            )
            self._reload_thread.start()
            logger.info("File watcher thread started")
        
        if self._db_pool and self.config.db_listen_channel:
            self._listener_thread = Thread(
                target=self._db_listen_loop,
                name="ConfigDBListener", 
                daemon=True
            )
            self._listener_thread.start()
            logger.info(f"Database listener thread started for channel: {self.config.db_listen_channel}")
    
    def _file_watch_loop(self):
        """Цикл отслеживания изменений файлов"""
        logger.debug("File watch loop started")
        
        while not self._shutdown_event.is_set():
            try:
                for file_path, last_mtime in list(self._file_watchers.items()):
                    path = Path(file_path)
                    if path.exists():
                        current_mtime = path.stat().st_mtime
                        if current_mtime > last_mtime:
                            logger.info(f"Config file changed: {file_path}")
                            self._reload_file_config(path)
                            self._file_watchers[file_path] = current_mtime
                            self._record_metric('hot_reloads')
                
                time.sleep(5)  # Проверяем каждые 5 секунд
                
            except Exception as e:
                logger.error(f"File watch error: {e}")
                self._record_error("file_watch_error", str(e))
                time.sleep(10)  # Увеличиваем интервал при ошибке
    
    def _db_listen_loop(self):
        """Цикл прослушивания изменений в БД"""
        logger.debug("Database listen loop started")
        
        conn = None
        try:
            conn = self._get_db_connection()
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cur:
                cur.execute(f"LISTEN {self.config.db_listen_channel}")
                logger.info(f"Listening for notifications on channel: {self.config.db_listen_channel}")
                
                while not self._shutdown_event.is_set():
                    if select.select([conn], [], [], 5) == ([], [], []):
                        continue  # Timeout, проверяем shutdown_event
                    
                    conn.poll()
                    while conn.notifies:
                        notify = conn.notifies.pop(0)
                        logger.info(f"Received config change notification: {notify.payload}")
                        
                        try:
                            # Парсим payload (ожидаем JSON с config_key)
                            if notify.payload:
                                payload = json.loads(notify.payload)
                                config_key = payload.get('config_key')
                                if config_key:
                                    self._invalidate_config_cache(config_key)
                                    self._record_metric('hot_reloads')
                        except json.JSONDecodeError:
                            # Если не JSON, считаем что это config_key
                            self._invalidate_config_cache(notify.payload)
                            self._record_metric('hot_reloads')
                        except Exception as e:
                            logger.error(f"Error processing notification: {e}")
                            self._record_error("notification_processing_error", str(e))
                            
        except Exception as e:
            logger.error(f"Database listen error: {e}")
            self._record_error("db_listen_error", str(e))
        finally:
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(f"UNLISTEN {self.config.db_listen_channel}")
                except:
                    pass
                self._return_db_connection(conn, close=True)
    
    def _reload_file_config(self, file_path: Path):
        """Перезагружает конфигурацию из файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yml', '.yaml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            if data:
                config_key = file_path.stem
                old_config = self._fallback_configs.get(config_key, {})
                self._fallback_configs[config_key] = data
                
                # Инвалидируем кеш для этой конфигурации
                self._invalidate_config_cache(config_key)
                
                # Уведомляем подписчиков
                self._notify_config_change(config_key, data)
                
                logger.info(f"Reloaded config: {config_key}")
                
        except Exception as e:
            logger.error(f"Failed to reload config from {file_path}: {e}")
            self._record_error("config_reload_failed", str(e))
    
    def _invalidate_config_cache(self, config_key: str):
        """Инвалидирует кеш для конфигурации"""
        removed_count = self._cache.invalidate(namespace=config_key)
        logger.debug(f"Invalidated {removed_count} cache entries for config: {config_key}")
    
    def _notify_config_change(self, config_key: str, new_config: Dict[str, Any]):
        """Уведомляет подписчиков об изменении конфигурации"""
        for callback in self._change_callbacks:
            try:
                callback(config_key, new_config)
            except Exception as e:
                logger.error(f"Config change callback error: {e}")
    
    def get_config(self, 
                   config_key: str, 
                   user_id: Optional[str] = None,
                   default: Any = None,
                   force_reload: bool = False) -> Dict[str, Any]:
        """
        Получает конфигурацию с учетом приоритетов:
        1. Переопределения переменных окружения
        2. Пользовательские настройки из БД
        3. Глобальная конфигурация из БД
        4. Fallback конфигурация из файлов
        """
        self._record_metric('config_requests')
        
        if self.config.log_config_access:
            logger.debug(f"Getting config: {config_key} for user: {user_id}")
        
        # Проверяем кеш
        cache_key = f"{config_key}:{user_id or 'global'}"
        if not force_reload:
            cached_value = self._cache.get(cache_key, namespace=config_key)
            if cached_value is not None:
                self._record_metric('cache_hits')
                return cached_value
        
        self._record_metric('cache_misses')
        
        # Собираем конфигурацию из всех источников
        final_config = {}
        
        # 1. Базовая конфигурация из файлов
        file_config = self._fallback_configs.get(config_key, {})
        if file_config:
            final_config.update(file_config)
        
        # 2. Конфигурация из БД
        db_config = self._load_config_from_db(config_key, user_id)
        if db_config:
            final_config = self._deep_merge(final_config, db_config)
        elif self._db_pool:
            # База доступна, но конфигурации нет
            pass
        else:
            # База недоступна, используем fallback
            self._record_metric('db_fallbacks')
        
        # 3. Переопределения из переменных окружения
        env_overrides = self._get_env_overrides(config_key)
        if env_overrides:
            final_config = self._deep_merge(final_config, env_overrides)
        
        # Если ничего не найдено, используем default
        if not final_config and default is not None:
            final_config = default if isinstance(default, dict) else {'default': default}
        
        # Кешируем результат
        if final_config:
            self._cache.set(cache_key, final_config, self.config.cache_ttl_seconds, namespace=config_key)
        
        # Маскируем секреты в логах
        if self.config.log_config_access:
            safe_config = self._mask_secrets(final_config) if self.config.mask_secrets else final_config
            logger.debug(f"Resolved config for {config_key}: {safe_config}")
        
        return final_config
    
    def _load_config_from_db(self, config_key: str, user_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Загружает конфигурацию из БД"""
        if not self._db_pool:
            return None
        
        conn = None
        try:
            conn = self._get_db_connection()
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Используем функцию get_effective_config из БД
                cur.execute("""
                    SELECT get_effective_config(%s, %s, %s) as config
                """, (config_key, user_id, self.config.environment))
                
                result = cur.fetchone()
                if result and result['config']:
                    return dict(result['config'])
                    
        except Exception as e:
            logger.error(f"Database config load error for {config_key}: {e}")
            self._record_error("db_config_load_error", str(e))
        finally:
            if conn:
                self._return_db_connection(conn)
        
        return None
    
    def _get_env_overrides(self, config_key: str) -> Dict[str, Any]:
        """Получает переопределения из переменных окружения"""
        overrides = {}
        
        # Ищем переменные вида PREFIX__CONFIG_KEY__PARAM__SUBPARAM=value
        env_prefix = f"{self.config.env_prefix}{self.config.env_separator}{config_key.upper()}{self.config.env_separator}"
        
        for env_var, value in os.environ.items():
            if env_var.startswith(env_prefix):
                # Получаем путь параметра
                param_path = env_var[len(env_prefix):].lower()
                
                # Заменяем __ на . для создания вложенной структуры
                param_path = param_path.replace(self.config.env_separator.lower(), '.')
                
                # Парсим значение
                typed_value = self._parse_env_value(value)
                
                # Устанавливаем значение по пути
                self._set_nested_value(overrides, param_path, typed_value)
        
        return overrides
    
    def _parse_env_value(self, value: str) -> Union[str, int, float, bool, dict, list, None]:
        """Парсит значение переменной окружения в правильный тип"""
        # Пустое значение
        if not value:
            return None
        
        # Boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # None/null
        if value.lower() in ('null', 'none', 'nil'):
            return None
        
        # JSON (массивы и объекты)
        if (value.startswith('[') and value.endswith(']')) or (value.startswith('{') and value.endswith('}')):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass  # Возвращаем как строку
        
        # Числа
        try:
            if '.' in value or 'e' in value.lower():
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Строка (по умолчанию)
        return value
    
    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any):
        """Устанавливает значение по вложенному пути"""
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                # Конфликт типов, перезаписываем
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Глубоко объединяет два словаря"""
        result = base.copy()
        
        for key, value in override.items():
            if (key in result and 
                isinstance(result[key], dict) and 
                isinstance(value, dict)):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _mask_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Маскирует секретные значения в конфигурации"""
        secret_keys = {
            'password', 'passwd', 'secret', 'key', 'token', 
            'api_key', 'private_key', 'access_token', 'auth_token'
        }
        
        def mask_dict(d):
            if not isinstance(d, dict):
                return d
            
            result = {}
            for k, v in d.items():
                key_lower = k.lower()
                if any(secret_word in key_lower for secret_word in secret_keys):
                    result[k] = '***MASKED***'
                elif isinstance(v, dict):
                    result[k] = mask_dict(v)
                elif isinstance(v, list):
                    result[k] = [mask_dict(item) if isinstance(item, dict) else item for item in v]
                else:
                    result[k] = v
            return result
        
        return mask_dict(config)
    
    def _record_metric(self, metric_name: str, value: float = 1.0):
        """Записывает метрику"""
        with self._metrics_lock:
            self._metrics[metric_name] = self._metrics.get(metric_name, 0) + value
        
        # Опционально записываем в БД
        if self.config.metrics_enabled and self._db_pool:
            self._record_db_metric('config_manager', metric_name, value)
    
    def _record_error(self, error_type: str, error_message: str):
        """Записывает ошибку"""
        self._record_metric('errors')
        
        if self.config.metrics_enabled and self._db_pool:
            self._record_db_metric('config_manager_error', error_type, 1.0, {
                'error_message': error_message,
                'environment': self.config.environment
            })
    
    def _record_db_metric(self, metric_type: str, metric_name: str, value: float, context: Optional[Dict] = None):
        """Записывает метрику в БД"""
        conn = None
        try:
            conn = self._get_db_connection()
            
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
                    VALUES (%s, %s, %s, %s, %s)
                """, (metric_type, metric_name, value, json.dumps(context) if context else None, self.config.environment))
                
                conn.commit()
                
        except Exception as e:
            # Не логируем ошибки записи метрик чтобы избежать циклов
            pass
        finally:
            if conn:
                self._return_db_connection(conn)
    
    def set_user_config(self, user_id: str, config_key: str, config_value: Dict[str, Any], 
                       expires_hours: Optional[int] = None) -> bool:
        """Устанавливает пользовательскую конфигурацию"""
        if not self._db_pool:
            logger.warning("Cannot set user config: database not available")
            return False
        
        conn = None
        try:
            expires_at = None
            if expires_hours:
                expires_at = datetime.now() + timedelta(hours=expires_hours)
            
            conn = self._get_db_connection()
            
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_configs (user_id, config_key, config_value, expires_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, config_key) 
                    DO UPDATE SET 
                        config_value = EXCLUDED.config_value,
                        expires_at = EXCLUDED.expires_at,
                        updated_at = NOW()
                """, (user_id, config_key, json.dumps(config_value), expires_at))
                
                conn.commit()
                
                # Инвалидируем кеш
                self._invalidate_config_cache(config_key)
                
                # Уведомляем через NOTIFY
                cur.execute(f"""
                    NOTIFY {self.config.db_listen_channel}, %s
                """, (json.dumps({'config_key': config_key, 'user_id': user_id}),))
                
                conn.commit()
                
                logger.info(f"User config set: {user_id}:{config_key}")
                self._record_metric('user_config_updates')
                return True
                
        except Exception as e:
            logger.error(f"Set user config error: {e}")
            self._record_error("set_user_config_error", str(e))
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self._return_db_connection(conn)
    
    def reload_config(self, config_key: str, version: str) -> bool:
        """Hot-reload конфигурации"""
        if not self._db_pool:
            logger.warning("Cannot reload config: database not available")
            return False
        
        conn = None
        try:
            conn = self._get_db_connection()
            
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT reload_config(%s, %s, %s)
                """, (config_key, version, self.config.environment))
                
                success = cur.fetchone()[0]
                
                if success:
                    # Инвалидируем кеш
                    self._invalidate_config_cache(config_key)
                    
                    # Уведомляем через NOTIFY
                    cur.execute(f"""
                        NOTIFY {self.config.db_listen_channel}, %s
                    """, (json.dumps({'config_key': config_key, 'version': version}),))
                    
                    conn.commit()
                    
                    logger.info(f"Config reloaded: {config_key} v{version}")
                    self._record_metric('config_reloads')
                
                return success
                
        except Exception as e:
            logger.error(f"Config reload error: {e}")
            self._record_error("config_reload_error", str(e))
            return False
        finally:
            if conn:
                self._return_db_connection(conn)
    
    def add_change_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Добавляет callback для уведомлений об изменениях"""
        self._change_callbacks.append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику менеджера"""
        with self._metrics_lock:
            metrics = self._metrics.copy()
        
        cache_stats = self._cache.get_stats()
        
        return {
            'environment': self.config.environment,
            'database_available': self._db_pool is not None,
            'auto_reload_enabled': self.config.auto_reload,
            'cache_stats': cache_stats,
            'metrics': metrics,
            'fallback_configs_count': len(self._fallback_configs),
            'file_watchers_count': len(self._file_watchers),
            'change_callbacks_count': len(self._change_callbacks)
        }
    
    def shutdown(self):
        """Корректное завершение работы"""
        logger.info("Shutting down ProductionConfigManager")
        
        # Останавливаем потоки
        self._shutdown_event.set()
        
        if self._reload_thread and self._reload_thread.is_alive():
            self._reload_thread.join(timeout=5)
        
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=5)
        
        # Закрываем пул соединений
        if self._db_pool:
            self._db_pool.closeall()
        
        logger.info("ProductionConfigManager shutdown completed")


# Глобальный экземпляр менеджера
config_manager = ProductionConfigManager()

# Регистрация корректного завершения
import atexit
atexit.register(config_manager.shutdown)


# Удобные функции для быстрого доступа
def get_config(config_key: str, user_id: Optional[str] = None, default: Any = None) -> Dict[str, Any]:
    """Быстрый доступ к конфигурации"""
    return config_manager.get_config(config_key, user_id, default)


def get_memory_thresholds(user_id: Optional[str] = None) -> Dict[str, float]:
    """Быстрый доступ к порогам памяти"""
    return config_manager.get_config('memory_thresholds', user_id, {})


def get_search_weights(user_id: Optional[str] = None) -> Dict[str, float]:
    """Быстрый доступ к весам поиска"""
    return config_manager.get_config('search_weights', user_id, {})


def reload_config(config_key: str, version: str) -> bool:
    """Быстрый hot-reload конфигурации"""
    return config_manager.reload_config(config_key, version)


if __name__ == "__main__":
    # Тест менеджера конфигурации
    print("🧪 Testing ProductionConfigManager")
    
    # Создаем тестовую конфигурацию
    test_config = ConfigManagerConfig(
        config_dir="./test_configs",
        cache_ttl_seconds=60,
        auto_reload=False  # Отключаем для тестов
    )
    
    manager = ProductionConfigManager(test_config)
    
    # Тестируем статистику
    stats = manager.get_stats()
    print(f"Manager stats: {stats}")
    
    # Тестируем загрузку конфигурации
    thresholds = manager.get_config('memory_thresholds', default={'test': 0.5})
    print(f"Memory thresholds: {thresholds}")
    
    # Тестируем переменные окружения
    os.environ['MEMORY__TEST_CONFIG__PARAM1'] = '42'
    os.environ['MEMORY__TEST_CONFIG__NESTED__PARAM2'] = 'true'
    
    test_config = manager.get_config('test_config')
    print(f"Test config with env overrides: {test_config}")
    
    print("✅ ProductionConfigManager test completed")
