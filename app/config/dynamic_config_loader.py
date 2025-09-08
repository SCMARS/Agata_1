"""
Динамический загрузчик конфигурации без хардкода
Поддерживает hot-reload, пользовательские переопределения и feature flags
"""
import os
import json
import yaml
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from threading import Lock

try:
    import psycopg2
    import psycopg2.extras
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    psycopg2 = None

logger = logging.getLogger(__name__)


@dataclass
class ConfigVersion:
    """Версия конфигурации"""
    config_key: str
    version: str
    payload: Dict[str, Any]
    environment: str
    active: bool
    created_at: datetime
    feature_flags: Optional[Dict[str, Any]] = None


@dataclass
class FeatureFlag:
    """Флаг функции"""
    feature_name: str
    enabled: bool
    environment: str
    dependencies: List[str]
    config: Dict[str, Any]
    description: str


class ConfigManager:
    """Менеджер динамической конфигурации"""
    
    def __init__(self, 
                 db_connection_string: Optional[str] = None,
                 environment: str = 'production',
                 cache_ttl: int = 300,  # 5 минут кеш
                 auto_reload: bool = True):
        self.db_connection_string = db_connection_string or os.getenv('DATABASE_URL')
        self.environment = environment
        self.cache_ttl = cache_ttl
        self.auto_reload = auto_reload
        
        # Кеш конфигураций
        self._config_cache: Dict[str, ConfigVersion] = {}
        self._feature_cache: Dict[str, FeatureFlag] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_lock = Lock()
        
        # Fallback конфигурации (из файлов)
        self._fallback_configs: Dict[str, Dict[str, Any]] = {}
        
        # Загружаем начальную конфигурацию
        self._load_fallback_configs()
        
        if DB_AVAILABLE and self.db_connection_string:
            self._db_available = True
            self._init_db_connection()
        else:
            self._db_available = False
            logger.warning("Database not available, using fallback configs only")
    
    def _load_fallback_configs(self):
        """Загружает fallback конфигурации из файлов"""
        config_dir = Path(__file__).parent
        
        # Список конфигурационных файлов для загрузки
        config_files = [
            'memory.yml',
            'thresholds.yml', 
            'patterns.yml',
            'features.yml'
        ]
        
        for config_file in config_files:
            config_path = config_dir / config_file
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        if config_file.endswith('.yml') or config_file.endswith('.yaml'):
                            data = yaml.safe_load(f)
                        else:
                            data = json.load(f)
                    
                    config_key = config_file.split('.')[0]
                    self._fallback_configs[config_key] = data
                    logger.info(f"Loaded fallback config: {config_key}")
                    
                except Exception as e:
                    logger.error(f"Failed to load fallback config {config_file}: {e}")
    
    def _init_db_connection(self):
        """Инициализация подключения к БД"""
        try:
            self._test_db_connection()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            self._db_available = False
    
    def _test_db_connection(self):
        """Тестовое подключение к БД"""
        if not self._db_available:
            return False
            
        try:
            with psycopg2.connect(self.db_connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"DB connection test failed: {e}")
            return False
    
    def get_config(self, 
                   config_key: str, 
                   user_id: Optional[str] = None,
                   default: Any = None,
                   force_reload: bool = False) -> Dict[str, Any]:
        """
        Получает конфигурацию с учетом приоритетов:
        1. Пользовательские переопределения
        2. Глобальная активная конфигурация из БД
        3. Fallback конфигурация из файлов
        """
        
        # Проверяем кеш
        cache_key = f"{config_key}:{user_id or 'global'}:{self.environment}"
        
        if not force_reload and self._is_cache_valid(cache_key):
            with self._cache_lock:
                if cache_key in self._config_cache:
                    return self._config_cache[cache_key].payload
        
        # Загружаем конфигурацию
        config = self._load_config_from_sources(config_key, user_id)
        
        # Кешируем результат
        if config:
            with self._cache_lock:
                self._config_cache[cache_key] = ConfigVersion(
                    config_key=config_key,
                    version='runtime',
                    payload=config,
                    environment=self.environment,
                    active=True,
                    created_at=datetime.now()
                )
                self._cache_timestamps[cache_key] = datetime.now()
        
        return config or default or {}
    
    def _load_config_from_sources(self, config_key: str, user_id: Optional[str]) -> Dict[str, Any]:
        """Загружает конфигурацию из всех доступных источников"""
        
        # 1. Пытаемся загрузить из БД
        if self._db_available:
            try:
                db_config = self._load_config_from_db(config_key, user_id)
                if db_config:
                    return db_config
            except Exception as e:
                logger.error(f"Failed to load config from DB: {e}")
        
        # 2. Fallback к файловой конфигурации
        fallback_config = self._fallback_configs.get(config_key, {})
        
        # 3. Применяем пользовательские переопределения из переменных окружения
        env_overrides = self._get_env_overrides(config_key)
        if env_overrides:
            fallback_config = self._merge_configs(fallback_config, env_overrides)
        
        return fallback_config
    
    def _load_config_from_db(self, config_key: str, user_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Загружает конфигурацию из БД"""
        try:
            with psycopg2.connect(self.db_connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Используем функцию из БД для получения эффективной конфигурации
                    cur.execute("""
                        SELECT get_effective_config(%s, %s, %s) as config
                    """, (config_key, user_id, self.environment))
                    
                    result = cur.fetchone()
                    if result and result['config']:
                        return dict(result['config'])
                    
        except Exception as e:
            logger.error(f"Database config load error: {e}")
            
        return None
    
    def _get_env_overrides(self, config_key: str) -> Dict[str, Any]:
        """Получает переопределения из переменных окружения"""
        overrides = {}
        
        # Ищем переменные вида CONFIG_KEY_PARAM=value
        prefix = f"{config_key.upper()}_"
        
        for env_var, value in os.environ.items():
            if env_var.startswith(prefix):
                param_path = env_var[len(prefix):].lower()
                
                # Преобразуем PARAM_SUB_VALUE в param.sub.value
                param_path = param_path.replace('_', '.')
                
                # Пытаемся преобразовать значение в правильный тип
                typed_value = self._parse_env_value(value)
                
                # Устанавливаем значение по пути
                self._set_nested_value(overrides, param_path, typed_value)
        
        return overrides
    
    def _parse_env_value(self, value: str) -> Union[str, int, float, bool, None]:
        """Парсит значение переменной окружения в правильный тип"""
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        elif value.lower() in ('null', 'none', ''):
            return None
        
        try:
            # Пытаемся преобразовать в число
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            return value
    
    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any):
        """Устанавливает значение по вложенному пути"""
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Рекурсивно объединяет конфигурации"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Проверяет валидность кеша"""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_age = datetime.now() - self._cache_timestamps[cache_key]
        return cache_age.total_seconds() < self.cache_ttl
    
    def get_feature_flag(self, feature_name: str, default: bool = False) -> bool:
        """Проверяет включен ли флаг функции"""
        if not self._db_available:
            # Fallback к переменным окружения
            env_var = f"FEATURE_{feature_name.upper()}"
            return os.getenv(env_var, str(default)).lower() == 'true'
        
        try:
            with psycopg2.connect(self.db_connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT enabled FROM feature_flags 
                        WHERE feature_name = %s AND environment = %s
                    """, (feature_name, self.environment))
                    
                    result = cur.fetchone()
                    return result[0] if result else default
                    
        except Exception as e:
            logger.error(f"Feature flag check error: {e}")
            return default
    
    def get_feature_config(self, feature_name: str) -> Dict[str, Any]:
        """Получает конфигурацию флага функции"""
        if not self._db_available:
            return {}
        
        try:
            with psycopg2.connect(self.db_connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT config FROM feature_flags 
                        WHERE feature_name = %s AND environment = %s AND enabled = true
                    """, (feature_name, self.environment))
                    
                    result = cur.fetchone()
                    return dict(result['config']) if result and result['config'] else {}
                    
        except Exception as e:
            logger.error(f"Feature config error: {e}")
            return {}
    
    def reload_config(self, config_key: str, version: str) -> bool:
        """Hot-reload конфигурации"""
        if not self._db_available:
            logger.warning("Hot-reload not available without database")
            return False
        
        try:
            with psycopg2.connect(self.db_connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT reload_config(%s, %s, %s)
                    """, (config_key, version, self.environment))
                    
                    success = cur.fetchone()[0]
                    
                    if success:
                        # Очищаем кеш для этой конфигурации
                        self._invalidate_cache(config_key)
                        logger.info(f"Config reloaded: {config_key} v{version}")
                    
                    return success
                    
        except Exception as e:
            logger.error(f"Config reload error: {e}")
            return False
    
    def _invalidate_cache(self, config_key: str):
        """Инвалидирует кеш для конфигурации"""
        with self._cache_lock:
            keys_to_remove = [k for k in self._config_cache.keys() if k.startswith(f"{config_key}:")]
            for key in keys_to_remove:
                del self._config_cache[key]
                if key in self._cache_timestamps:
                    del self._cache_timestamps[key]
    
    def set_user_config(self, user_id: str, config_key: str, config_value: Dict[str, Any], 
                       expires_hours: Optional[int] = None) -> bool:
        """Устанавливает пользовательскую конфигурацию"""
        if not self._db_available:
            return False
        
        try:
            expires_at = None
            if expires_hours:
                expires_at = datetime.now() + timedelta(hours=expires_hours)
            
            with psycopg2.connect(self.db_connection_string) as conn:
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
                    
                    # Инвалидируем кеш для этого пользователя
                    self._invalidate_cache(config_key)
                    
                    logger.info(f"User config set: {user_id}:{config_key}")
                    return True
                    
        except Exception as e:
            logger.error(f"Set user config error: {e}")
            return False
    
    def get_memory_thresholds(self, user_id: Optional[str] = None) -> Dict[str, float]:
        """Получает пороги для системы памяти"""
        config = self.get_config('memory_thresholds', user_id, {})
        
        # Дефолтные пороги если конфигурация недоступна
        defaults = {
            'semantic_similarity': 0.5,
            'text_fuzzy_min': 0.25,
            'fact_accept_immediate': 0.95,
            'low_confidence': 0.3,
            'fact_confidence_min': 0.7,
            'importance_threshold': 0.6
        }
        
        return {**defaults, **config}
    
    def get_search_weights(self, user_id: Optional[str] = None) -> Dict[str, float]:
        """Получает веса для поиска"""
        config = self.get_config('search_weights', user_id, {})
        
        defaults = {
            'deterministic_facts': 1.0,
            'fuzzy_text': 0.7,
            'semantic_vector': 0.6,
            'episodic': 0.4
        }
        
        return {**defaults, **config}
    
    def check_dependencies(self, feature_name: str) -> List[str]:
        """Проверяет зависимости флага функции"""
        if not self._db_available:
            return []
        
        try:
            with psycopg2.connect(self.db_connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT dependencies FROM feature_flags 
                        WHERE feature_name = %s AND environment = %s
                    """, (feature_name, self.environment))
                    
                    result = cur.fetchone()
                    return result[0] if result and result[0] else []
                    
        except Exception as e:
            logger.error(f"Dependencies check error: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Получает статус менеджера конфигурации"""
        return {
            'database_available': self._db_available,
            'environment': self.environment,
            'cache_size': len(self._config_cache),
            'fallback_configs': list(self._fallback_configs.keys()),
            'auto_reload': self.auto_reload,
            'cache_ttl': self.cache_ttl
        }


# Глобальный экземпляр менеджера конфигурации
config_manager = ConfigManager(
    environment=os.getenv('APP_ENVIRONMENT', 'production'),
    cache_ttl=int(os.getenv('CONFIG_CACHE_TTL', '300')),
    auto_reload=os.getenv('CONFIG_AUTO_RELOAD', 'true').lower() == 'true'
)


# Удобные функции для быстрого доступа
def get_config(config_key: str, user_id: Optional[str] = None, default: Any = None) -> Dict[str, Any]:
    """Быстрый доступ к конфигурации"""
    return config_manager.get_config(config_key, user_id, default)


def get_feature_flag(feature_name: str, default: bool = False) -> bool:
    """Быстрая проверка флага функции"""
    return config_manager.get_feature_flag(feature_name, default)


def get_memory_thresholds(user_id: Optional[str] = None) -> Dict[str, float]:
    """Быстрый доступ к порогам памяти"""
    return config_manager.get_memory_thresholds(user_id)


def get_search_weights(user_id: Optional[str] = None) -> Dict[str, float]:
    """Быстрый доступ к весам поиска"""
    return config_manager.get_search_weights(user_id)


if __name__ == "__main__":
    # Тест менеджера конфигурации
    print("🧪 Testing ConfigManager")
    
    manager = ConfigManager()
    status = manager.get_status()
    print(f"Manager status: {status}")
    
    # Тест загрузки конфигурации
    thresholds = manager.get_memory_thresholds()
    print(f"Memory thresholds: {thresholds}")
    
    # Тест флагов функций
    vector_enabled = manager.get_feature_flag('pgvector_support')
    print(f"Vector support enabled: {vector_enabled}")
    
    print("✅ ConfigManager test completed")
