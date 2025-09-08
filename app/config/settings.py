import os
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv('config.env')

class Settings:
    """Application settings configuration"""

    # Base directory
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Flask
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'development')
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '5000'))
    
    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql://agatha:agatha@postgres:5432/agatha')
    
    # Database connection parameters for pgvector
    DATABASE_HOST: str = os.getenv('DATABASE_HOST', 'localhost')
    DATABASE_PORT: int = int(os.getenv('DATABASE_PORT', '5432'))
    DATABASE_USER: str = os.getenv('DATABASE_USER', 'postgres')
    DATABASE_PASSWORD: str = os.getenv('DATABASE_PASSWORD', 'postgres')
    DATABASE_NAME: str = os.getenv('DATABASE_NAME', 'agatha')
    
    # Redis
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/1')
    CELERY_RESULT_BACKEND: str = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/2')
    
    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    LLM_MODEL: str = os.getenv('LLM_MODEL', 'gpt-4')
    MAX_MESSAGE_LENGTH: int = int(os.getenv('MAX_MESSAGE_LENGTH', '500'))
    
    # LangSmith (optional)
    LANGSMITH_API_KEY: Optional[str] = os.getenv('LANGSMITH_API_KEY')
    LANGSMITH_PROJECT: str = os.getenv('LANGSMITH_PROJECT', 'agatha')
    
    # Agatha Configuration
    BASE_PROMPT_PATH: str = os.getenv('BASE_PROMPT_PATH', 'app/config/prompts')
    DAYS_SCENARIO_COUNT: int = int(os.getenv('DAYS_SCENARIO_COUNT', '30'))
    QUESTION_FREQUENCY: int = int(os.getenv('QUESTION_FREQUENCY', '3'))
    
    # Memory
    MEMORY_TYPE: str = os.getenv('MEMORY_TYPE', 'hybrid')
    VECTOR_STORE_TYPE: str = os.getenv('VECTOR_STORE_TYPE', 'pgvector')

settings = Settings() 