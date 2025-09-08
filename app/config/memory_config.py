
import os
import json
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path

class MemoryConfig:
    """Конфигурация системы памяти"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация конфигурации
        
        Args:
            config_path: Путь к файлу конфигурации (YAML/JSON)
        """
        self.config_path = config_path or os.getenv('MEMORY_CONFIG_PATH')
        self._config_data = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Загрузить конфигурацию из файла или переменных окружения"""
        config = {}
        
        # Загружаем из файла если есть
        if self.config_path and Path(self.config_path).exists():
            config.update(self._load_from_file())
        
        # Переопределяем переменными окружения
        config.update(self._load_from_env())
        
        return config
    
    def _load_from_file(self) -> Dict[str, Any]:
        """Загрузить конфигурацию из файла"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    return yaml.safe_load(f) or {}
                else:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load config from {self.config_path}: {e}")
            return {}
    
    def _load_from_env(self) -> Dict[str, Any]:
        """Загрузить конфигурацию из переменных окружения"""
        return {
            # Общие настройки
            'memory_type': os.getenv('MEMORY_TYPE', 'advanced'),
            'debug_mode': os.getenv('MEMORY_DEBUG', 'false').lower() == 'true',
            
            # Short-Term Memory
            'short_term': {
                'enabled': os.getenv('SHORT_TERM_ENABLED', 'true').lower() == 'true',
                'max_messages': int(os.getenv('SHORT_TERM_MAX_MESSAGES', '10')),
                'provider': os.getenv('SHORT_TERM_PROVIDER', 'langchain_buffer'),
                'ttl_seconds': int(os.getenv('SHORT_TERM_TTL', '3600')),
            },
            
            # Episodic Memory
            'episodic': {
                'enabled': os.getenv('EPISODIC_ENABLED', 'true').lower() == 'true',
                'auto_save_episodes': os.getenv('EPISODIC_AUTO_SAVE', 'true').lower() == 'true',
                'episode_min_messages': int(os.getenv('EPISODIC_MIN_MESSAGES', '5')),
                'episode_timeout_minutes': int(os.getenv('EPISODIC_TIMEOUT', '30')),
            },
            
            # Long-Term Memory
            'long_term': {
                'enabled': os.getenv('LONG_TERM_ENABLED', 'true').lower() == 'true',
                'provider': os.getenv('LONG_TERM_PROVIDER', 'chroma'),  # chroma, pinecone, weaviate, faiss
                'importance_threshold': float(os.getenv('LONG_TERM_IMPORTANCE_THRESHOLD', '0.6')),
                'max_storage_items': int(os.getenv('LONG_TERM_MAX_ITEMS', '10000')),
            },
            
            # Summary Memory
            'summary': {
                'enabled': os.getenv('SUMMARY_ENABLED', 'true').lower() == 'true',
                'auto_summarize': os.getenv('SUMMARY_AUTO', 'true').lower() == 'true',
                'trigger_message_count': int(os.getenv('SUMMARY_TRIGGER_COUNT', '50')),
                'max_summary_length': int(os.getenv('SUMMARY_MAX_LENGTH', '500')),
                'summarizer_model': os.getenv('SUMMARY_MODEL', 'gpt-4o-mini'),
            },
            
            # Vector Database
            'vector_db': {
                'provider': os.getenv('VECTOR_DB_PROVIDER', 'chroma'),
                'connection_string': os.getenv('VECTOR_DB_CONNECTION'),
                'collection_prefix': os.getenv('VECTOR_DB_COLLECTION_PREFIX', 'agatha_memory'),
                'persist_directory': os.getenv('VECTOR_DB_PERSIST_DIR', './vector_db'),
                'distance_metric': os.getenv('VECTOR_DB_DISTANCE', 'cosine'),
            },
            
            # Embeddings
            'embeddings': {
                'provider': os.getenv('EMBEDDINGS_PROVIDER', 'openai'),  # openai, huggingface, cohere
                'model': os.getenv('EMBEDDINGS_MODEL', 'text-embedding-3-small'),
                'api_key': os.getenv('EMBEDDINGS_API_KEY') or os.getenv('OPENAI_API_KEY'),
                'chunk_size': int(os.getenv('EMBEDDINGS_CHUNK_SIZE', '1000')),
                'chunk_overlap': int(os.getenv('EMBEDDINGS_CHUNK_OVERLAP', '200')),
            },
            
            # Search
            'search': {
                'hybrid_enabled': os.getenv('SEARCH_HYBRID_ENABLED', 'true').lower() == 'true',
                'semantic_weight': float(os.getenv('SEARCH_SEMANTIC_WEIGHT', '0.7')),
                'keyword_weight': float(os.getenv('SEARCH_KEYWORD_WEIGHT', '0.3')),
                'max_results': int(os.getenv('SEARCH_MAX_RESULTS', '5')),
                'similarity_threshold': float(os.getenv('SEARCH_SIMILARITY_THRESHOLD', '0.6')),
            },
            
            # Information Extraction
            'extraction': {
                'enabled': os.getenv('INFO_EXTRACTION_ENABLED', 'true').lower() == 'true',
                'extractors_config_path': os.getenv('EXTRACTORS_CONFIG_PATH'),
                'auto_extract_entities': os.getenv('AUTO_EXTRACT_ENTITIES', 'true').lower() == 'true',
                'extract_importance_threshold': float(os.getenv('EXTRACT_IMPORTANCE_THRESHOLD', '0.5')),
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Получить значение конфигурации по пути (через точку)
        
        Args:
            key_path: Путь к ключу, например 'short_term.max_messages'
            default: Значение по умолчанию
            
        Returns:
            Значение конфигурации
        """
        keys = key_path.split('.')
        value = self._config_data
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def update(self, key_path: str, value: Any) -> None:
        """
        Обновить значение конфигурации
        
        Args:
            key_path: Путь к ключу
            value: Новое значение
        """
        keys = key_path.split('.')
        config_dict = self._config_data
        
        # Навигация до предпоследнего ключа
        for key in keys[:-1]:
            if key not in config_dict:
                config_dict[key] = {}
            config_dict = config_dict[key]
        
        # Установка значения
        config_dict[keys[-1]] = value
    
    def is_enabled(self, component: str) -> bool:
        """Проверить, включен ли компонент"""
        return self.get(f'{component}.enabled', False)
    
    def get_provider_config(self, component: str) -> Dict[str, Any]:
        """Получить конфигурацию провайдера для компонента"""
        provider = self.get(f'{component}.provider')
        if not provider:
            return {}
        
        # Базовая конфигурация
        config = dict(self._config_data.get(component, {}))
        
        # Добавляем специфичные настройки провайдера
        provider_config = self._config_data.get(f'{component}_providers', {}).get(provider, {})
        config.update(provider_config)
        
        return config
    
    def validate(self) -> List[str]:
        """
        Валидация конфигурации
        
        Returns:
            Список ошибок валидации
        """
        errors = []
        
        # Проверяем обязательные поля
        required_fields = [
            'vector_db.provider',
            'embeddings.provider',
        ]
        
        for field in required_fields:
            if not self.get(field):
                errors.append(f"Required field '{field}' is missing")
        
        # Проверяем API ключи
        if self.get('embeddings.provider') == 'openai' and not self.get('embeddings.api_key'):
            errors.append("OpenAI API key is required for OpenAI embeddings")
        
        # Проверяем векторную БД
        vector_provider = self.get('vector_db.provider')
        if vector_provider == 'pinecone' and not self.get('vector_db.connection_string'):
            errors.append("Pinecone connection string is required")
        
        # Проверяем числовые значения
        numeric_checks = [
            ('short_term.max_messages', 1, 1000),
            ('search.max_results', 1, 100),
            ('summary.trigger_message_count', 1, 10000),
        ]
        
        for field, min_val, max_val in numeric_checks:
            value = self.get(field)
            if value is not None and not (min_val <= value <= max_val):
                errors.append(f"Field '{field}' value {value} is out of range [{min_val}, {max_val}]")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Получить полную конфигурацию как словарь"""
        return self._config_data.copy()
    
    def save_to_file(self, file_path: str) -> None:
        """Сохранить конфигурацию в файл"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    yaml.dump(self._config_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(self._config_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Configuration saved to {file_path}")
        except Exception as e:
            print(f"❌ Failed to save configuration to {file_path}: {e}")


# Глобальный экземпляр конфигурации
memory_config = MemoryConfig()

# Валидация при загрузке
validation_errors = memory_config.validate()
if validation_errors:
    print("⚠️ Memory configuration validation errors:")
    for error in validation_errors:
        print(f"   - {error}")
else:
    print("✅ Memory configuration loaded successfully")


# Пример файла конфигурации (может быть создан автоматически)
EXAMPLE_CONFIG = """
# Конфигурация системы памяти Agatha AI
memory_type: advanced
debug_mode: false

short_term:
  enabled: true
  max_messages: 10
  provider: langchain_buffer
  ttl_seconds: 3600

episodic:
  enabled: true
  auto_save_episodes: true
  episode_min_messages: 5
  episode_timeout_minutes: 30

long_term:
  enabled: true
  provider: chroma  # chroma, pinecone, weaviate, faiss
  importance_threshold: 0.6
  max_storage_items: 10000

summary:
  enabled: true
  auto_summarize: true
  trigger_message_count: 50
  max_summary_length: 500
  summarizer_model: gpt-4o-mini

vector_db:
  provider: chroma
  collection_prefix: agatha_memory
  persist_directory: ./vector_db
  distance_metric: cosine

embeddings:
  provider: openai  # openai, huggingface, cohere
  model: text-embedding-3-small
  chunk_size: 1000
  chunk_overlap: 200

search:
  hybrid_enabled: true
  semantic_weight: 0.7
  keyword_weight: 0.3
  max_results: 5
  similarity_threshold: 0.6

extraction:
  enabled: true
  auto_extract_entities: true
  extract_importance_threshold: 0.5
  
  # Конфигурируемые экстракторы
  extractors:
    personal_info:
      patterns:
        name: 
          - "зовут\\s+(\\w+)"
          - "меня\\s+зовут\\s+(\\w+)"
          - "имя\\s+(\\w+)"
        age:
          - "мне\\s+(\\d+)\\s*(?:лет|года|год)"
          - "возраст\\s+(\\d+)"
        profession:
          - "работаю\\s+(\\w+)"
          - "профессия\\s+(\\w+)"
      importance_weight: 1.0
    
    interests:
      keywords:
        - "люблю"
        - "нравится" 
        - "увлекаюсь"
        - "хобби"
      importance_weight: 0.8
    
    locations:
      patterns:
        city:
          - "живу\\s+в\\s+(\\w+)"
          - "из\\s+(\\w+)"
          - "город\\s+(\\w+)"
      importance_weight: 0.7
"""

def create_example_config(file_path: str = './memory_config.yaml') -> None:
    """Создать пример файла конфигурации"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(EXAMPLE_CONFIG)
        print(f"✅ Example configuration created at {file_path}")
    except Exception as e:
        print(f"❌ Failed to create example config: {e}")


if __name__ == "__main__":
    # Тест конфигурации
    config = MemoryConfig()
    
    print("📋 Current Memory Configuration:")
    print(f"  Memory Type: {config.get('memory_type')}")
    print(f"  Short-Term Max Messages: {config.get('short_term.max_messages')}")
    print(f"  Vector DB Provider: {config.get('vector_db.provider')}")
    print(f"  Embeddings Provider: {config.get('embeddings.provider')}")
    print(f"  Hybrid Search: {config.get('search.hybrid_enabled')}")
    
    # Создаем пример конфигурации
    create_example_config()
