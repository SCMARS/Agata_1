-- Agatha AI Companion Database Initialization
-- Створення бази даних для PostgreSQL з pgvector

-- Створюємо розширення pgvector для векторних операцій
CREATE EXTENSION IF NOT EXISTS vector;

-- Створюємо таблиці для системи пам'яті

-- Таблиця для коротко-строкової пам'яті
CREATE TABLE IF NOT EXISTS short_term_memory (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    role VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    INDEX(user_id, timestamp)
);

-- Таблиця для довго-строкової пам'яті
CREATE TABLE IF NOT EXISTS long_term_memory (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    memory_type VARCHAR(100) NOT NULL,
    importance_score FLOAT DEFAULT 0.0,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    INDEX(user_id, memory_type),
    INDEX(user_id, importance_score DESC),
    INDEX(user_id, last_accessed DESC)
);

-- Таблиця для семантичного контексту
CREATE TABLE IF NOT EXISTS semantic_context (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    context_text TEXT NOT NULL,
    context_type VARCHAR(100) NOT NULL,
    relevance_score FLOAT DEFAULT 0.0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    INDEX(user_id, context_type),
    INDEX(user_id, relevance_score DESC)
);

-- Таблиця для поведінкового аналізу
CREATE TABLE IF NOT EXISTS behavioral_analysis (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    behavior_data JSONB NOT NULL,
    analysis_type VARCHAR(100) NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX(user_id, analysis_type),
    INDEX(user_id, timestamp DESC)
);

-- Таблиця для стадій розмов
CREATE TABLE IF NOT EXISTS conversation_stages (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    stage_number INTEGER NOT NULL,
    stage_name VARCHAR(100) NOT NULL,
    stage_data JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX(user_id, stage_number),
    INDEX(user_id, is_active)
);

-- Таблиця для налаштувань користувачів
CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Створюємо індекси для векторного пошуку
CREATE INDEX IF NOT EXISTS long_term_memory_embedding_idx ON long_term_memory USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS semantic_context_embedding_idx ON semantic_context USING ivfflat (embedding vector_cosine_ops);

-- Додаємо тригер для автоматичного оновлення updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON user_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Створюємо таблицю для системних налаштувань
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Вставляємо початкові налаштування
INSERT INTO system_config (config_key, config_value, description) VALUES
('system_version', '"1.0.0"', 'Версія системи Agatha AI'),
('memory_retention_days', '30', 'Кількість днів для зберігання короткострокової пам''яті'),
('max_long_term_memories', '1000', 'Максимальна кількість записів у довгостроковій пам''яті на користувача'),
('embedding_model', '"text-embedding-ada-002"', 'Модель для створення embeddings')
ON CONFLICT (config_key) DO NOTHING;

-- Готово! База даних ініціалізована