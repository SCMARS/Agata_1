-- Миграция: Полностью динамическая конфигурация памяти без хардкода
-- Версия: 2.0
-- Автор: System
-- Параметры: ${VECTOR_DIM:=1536}, ${DEFAULT_LANG:=ru}, ${ENABLE_VECTOR:=false}

-- Таблица версий конфигурации (ядро системы)
CREATE TABLE config_versions (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    created_by VARCHAR(100) DEFAULT 'system',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    active BOOLEAN DEFAULT FALSE,
    description TEXT,
    environment VARCHAR(20) DEFAULT 'production', -- production, staging, dev
    feature_flags JSONB DEFAULT '{}',
    UNIQUE(config_key, version, environment)
);

-- Индексы для быстрого поиска активных конфигов
CREATE INDEX idx_config_versions_active ON config_versions(config_key, active, environment) WHERE active = TRUE;
CREATE INDEX idx_config_versions_created ON config_versions(created_at DESC);
CREATE INDEX idx_config_versions_env ON config_versions(environment, active);

-- Таблица флагов функций и зависимостей
CREATE TABLE feature_flags (
    id SERIAL PRIMARY KEY,
    feature_name VARCHAR(100) NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT FALSE,
    environment VARCHAR(20) DEFAULT 'production',
    dependencies TEXT[], -- массив зависимых расширений/сервисов
    config JSONB DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы для feature flags
CREATE INDEX idx_feature_flags_enabled ON feature_flags(feature_name, enabled, environment);

-- Таблица справочника тем/топиков (без хардкода языка)
CREATE TABLE memory_topics (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(50) NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    weight FLOAT DEFAULT 1.0,
    language VARCHAR(10) NOT NULL, -- убираем DEFAULT, берем из конфига
    source VARCHAR(20) DEFAULT 'default', -- default, user, admin, imported
    active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}', -- для расширения без миграций
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(topic, keyword, language)
);

-- Индексы для топиков
CREATE INDEX idx_memory_topics_topic ON memory_topics(topic, language) WHERE active = TRUE;
CREATE INDEX idx_memory_topics_keyword ON memory_topics(keyword, language) WHERE active = TRUE;
CREATE INDEX idx_memory_topics_lang ON memory_topics(language, active);
CREATE INDEX idx_memory_topics_weight ON memory_topics(weight DESC) WHERE active = TRUE;

-- Таблица справочника профессий
CREATE TABLE memory_professions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    normalized_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    language VARCHAR(10) NOT NULL,
    confidence_boost FLOAT DEFAULT 0.0, -- бонус к уверенности при извлечении
    active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(normalized_name, language)
);

-- Индексы для профессий
CREATE INDEX idx_memory_professions_name ON memory_professions(normalized_name, language) WHERE active = TRUE;
CREATE INDEX idx_memory_professions_cat ON memory_professions(category, language) WHERE active = TRUE;

-- Таблица справочника мест/городов
CREATE TABLE memory_places (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    normalized_name VARCHAR(100) NOT NULL,
    place_type VARCHAR(20), -- city, country, region
    language VARCHAR(10) NOT NULL,
    confidence_boost FLOAT DEFAULT 0.0,
    active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}', -- может содержать координаты, часовой пояс и т.д.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(normalized_name, language)
);

-- Индексы для мест
CREATE INDEX idx_memory_places_name ON memory_places(normalized_name, language) WHERE active = TRUE;
CREATE INDEX idx_memory_places_type ON memory_places(place_type, language) WHERE active = TRUE;

-- Таблица паттернов для извлечения фактов (полностью конфигурируемая)
CREATE TABLE extraction_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL, -- intent, fact_extraction, validation
    category VARCHAR(50) NOT NULL, -- name, age, profession, etc.
    pattern TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.8,
    canonical_keys JSONB, -- массив ключей для intent patterns (гибче чем TEXT[])
    language VARCHAR(10) NOT NULL,
    source VARCHAR(20) DEFAULT 'default',
    priority INT DEFAULT 100, -- порядок применения паттернов
    active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}', -- для дополнительных параметров
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы для паттернов
CREATE INDEX idx_extraction_patterns_type ON extraction_patterns(pattern_type, language, active) WHERE active = TRUE;
CREATE INDEX idx_extraction_patterns_cat ON extraction_patterns(category, language, active) WHERE active = TRUE;
CREATE INDEX idx_extraction_patterns_priority ON extraction_patterns(priority ASC, confidence DESC) WHERE active = TRUE;

-- Таблица пользовательских настроек/переопределений
CREATE TABLE user_configs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    config_key VARCHAR(100) NOT NULL,
    config_value JSONB NOT NULL,
    priority INT DEFAULT 100, -- приоритет применения (меньше = выше приоритет)
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, config_key)
);

-- Индексы для пользовательских конфигов
CREATE INDEX idx_user_configs_user ON user_configs(user_id, priority);
CREATE INDEX idx_user_configs_key ON user_configs(config_key);
CREATE INDEX idx_user_configs_expires ON user_configs(expires_at) WHERE expires_at IS NOT NULL;

-- Таблица фактов пользователей (улучшенная версия без хардкода)
CREATE TABLE user_facts (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    fact_key VARCHAR(100) NOT NULL,
    fact_value TEXT NOT NULL,
    normalized_value TEXT NOT NULL, -- для поиска
    confidence FLOAT DEFAULT 0.9,
    occurrences INT DEFAULT 1,
    importance_score FLOAT DEFAULT 0.5,
    extracted_by VARCHAR(20) DEFAULT 'unknown', -- llm, regex, manual, imported
    source_context TEXT, -- отрывок исходного сообщения
    language VARCHAR(10) NOT NULL, -- язык факта
    metadata JSONB DEFAULT '{}',
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    is_canonical BOOLEAN DEFAULT FALSE, -- основной факт для этого ключа
    is_active BOOLEAN DEFAULT TRUE,
    version INT DEFAULT 1 -- для отслеживания изменений
);

-- Индексы для фактов
CREATE INDEX idx_user_facts_user_key ON user_facts(user_id, fact_key, language) WHERE is_active = TRUE;
CREATE INDEX idx_user_facts_canonical ON user_facts(user_id, fact_key, is_canonical) WHERE is_canonical = TRUE AND is_active = TRUE;
CREATE INDEX idx_user_facts_confidence ON user_facts(confidence DESC, occurrences DESC, importance_score DESC);
CREATE INDEX idx_user_facts_last_seen ON user_facts(last_seen DESC);
CREATE INDEX idx_user_facts_language ON user_facts(language, is_active);

-- Полнотекстовый поиск для фактов (адаптируемый под язык)
CREATE INDEX idx_user_facts_value_gin_ru ON user_facts USING gin(to_tsvector('russian', fact_value)) WHERE is_active = TRUE AND language = 'ru';
CREATE INDEX idx_user_facts_value_gin_en ON user_facts USING gin(to_tsvector('english', fact_value)) WHERE is_active = TRUE AND language = 'en';

-- Таблица эпизодов
CREATE TABLE memory_episodes (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    message_count INT DEFAULT 0,
    summary TEXT,
    topics JSONB DEFAULT '[]', -- массив топиков с весами
    sentiment VARCHAR(20), -- positive, negative, neutral
    importance_score FLOAT DEFAULT 0.5,
    session_id VARCHAR(100),
    language VARCHAR(10) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы для эпизодов
CREATE INDEX idx_memory_episodes_user ON memory_episodes(user_id, language);
CREATE INDEX idx_memory_episodes_time ON memory_episodes(start_time DESC);
CREATE INDEX idx_memory_episodes_importance ON memory_episodes(importance_score DESC);
CREATE INDEX idx_memory_episodes_session ON memory_episodes(session_id);

-- Таблица метрик и статистики
CREATE TABLE memory_metrics (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    metric_type VARCHAR(50) NOT NULL, -- fact_extraction, search_precision, etc.
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    context JSONB,
    environment VARCHAR(20) DEFAULT 'production',
    measured_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы для метрик
CREATE INDEX idx_memory_metrics_type ON memory_metrics(metric_type, environment, measured_at DESC);
CREATE INDEX idx_memory_metrics_user ON memory_metrics(user_id, measured_at DESC);

-- Функция для автоматического обновления timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для автоматического обновления timestamp
CREATE TRIGGER update_user_configs_updated_at 
    BEFORE UPDATE ON user_configs 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feature_flags_updated_at 
    BEFORE UPDATE ON feature_flags 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memory_topics_updated_at 
    BEFORE UPDATE ON memory_topics 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_extraction_patterns_updated_at 
    BEFORE UPDATE ON extraction_patterns 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Функция для получения конфигурации с приоритетами
CREATE OR REPLACE FUNCTION get_effective_config(
    p_config_key VARCHAR,
    p_user_id VARCHAR DEFAULT NULL,
    p_environment VARCHAR DEFAULT 'production'
) RETURNS JSONB AS $$
DECLARE
    global_config JSONB;
    user_config JSONB;
    final_config JSONB;
BEGIN
    -- Получаем глобальную конфигурацию
    SELECT payload INTO global_config
    FROM config_versions 
    WHERE config_key = p_config_key 
      AND active = TRUE 
      AND environment = p_environment
    LIMIT 1;
    
    -- Если есть пользователь, получаем его переопределения
    IF p_user_id IS NOT NULL THEN
        SELECT config_value INTO user_config
        FROM user_configs 
        WHERE user_id = p_user_id 
          AND config_key = p_config_key
          AND (expires_at IS NULL OR expires_at > NOW())
        ORDER BY priority ASC
        LIMIT 1;
        
        -- Объединяем конфиги (user override global)
        IF user_config IS NOT NULL THEN
            final_config := global_config || user_config;
        ELSE
            final_config := global_config;
        END IF;
    ELSE
        final_config := global_config;
    END IF;
    
    RETURN COALESCE(final_config, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql;

-- Функция для вычисления важности факта (конфигурируемая)
CREATE OR REPLACE FUNCTION calculate_fact_importance(
    p_confidence FLOAT,
    p_occurrences INT,
    p_fact_key VARCHAR,
    p_days_since_first_seen INT DEFAULT 0,
    p_user_id VARCHAR DEFAULT NULL
) RETURNS FLOAT AS $$
DECLARE
    config JSONB;
    key_weights JSONB;
    thresholds JSONB;
    base_score FLOAT;
    key_weight FLOAT;
    recency_bonus FLOAT;
    occurrence_bonus FLOAT;
    max_occurrence_bonus FLOAT;
    recency_thresholds JSONB;
BEGIN
    -- Получаем конфигурацию для расчета важности
    config := get_effective_config('importance_calculation', p_user_id);
    
    -- Извлекаем веса ключей из конфигурации
    key_weights := COALESCE(config->'key_weights', '{
        "name": 1.0, "age": 0.9, "profession": 0.9, "location": 0.8,
        "friends": 0.8, "family": 0.85, "company": 0.7, "hobbies": 0.6
    }'::jsonb);
    
    thresholds := COALESCE(config->'thresholds', '{
        "max_occurrence_bonus": 0.3, "occurrence_multiplier": 0.1
    }'::jsonb);
    
    recency_thresholds := COALESCE(config->'recency_bonuses', '{
        "week": 0.2, "month": 0.1, "default": 0.0
    }'::jsonb);
    
    -- Получаем вес для конкретного ключа
    key_weight := COALESCE((key_weights->>p_fact_key)::FLOAT, 0.5);
    
    -- Вычисляем бонус за частоту упоминания
    max_occurrence_bonus := COALESCE((thresholds->>'max_occurrence_bonus')::FLOAT, 0.3);
    occurrence_bonus := LEAST(
        LOG(p_occurrences + 1) * COALESCE((thresholds->>'occurrence_multiplier')::FLOAT, 0.1), 
        max_occurrence_bonus
    );
    
    -- Вычисляем бонус за свежесть
    recency_bonus := CASE 
        WHEN p_days_since_first_seen <= 7 THEN COALESCE((recency_thresholds->>'week')::FLOAT, 0.2)
        WHEN p_days_since_first_seen <= 30 THEN COALESCE((recency_thresholds->>'month')::FLOAT, 0.1)
        ELSE COALESCE((recency_thresholds->>'default')::FLOAT, 0.0)
    END;
    
    base_score := p_confidence * key_weight + occurrence_bonus + recency_bonus;
    
    RETURN LEAST(base_score, 1.0);
END;
$$ LANGUAGE plpgsql;

-- Функция для проверки доступности функций
CREATE OR REPLACE FUNCTION check_feature_availability(
    feature_name VARCHAR,
    environment VARCHAR DEFAULT 'production'
) RETURNS BOOLEAN AS $$
DECLARE
    is_enabled BOOLEAN;
    dependencies TEXT[];
    dep VARCHAR;
BEGIN
    -- Проверяем включен ли feature
    SELECT enabled, feature_flags.dependencies INTO is_enabled, dependencies
    FROM feature_flags 
    WHERE feature_flags.feature_name = check_feature_availability.feature_name 
      AND feature_flags.environment = check_feature_availability.environment;
    
    IF NOT FOUND OR NOT is_enabled THEN
        RETURN FALSE;
    END IF;
    
    -- Проверяем зависимости (упрощенная версия)
    IF dependencies IS NOT NULL THEN
        FOREACH dep IN ARRAY dependencies LOOP
            -- Здесь можно добавить проверки расширений, внешних сервисов и т.д.
            -- Пока просто логируем
            RAISE NOTICE 'Checking dependency: %', dep;
        END LOOP;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Представления для удобства использования
CREATE VIEW active_configs AS
SELECT config_key, payload, version, environment, created_at, feature_flags
FROM config_versions 
WHERE active = TRUE;

CREATE VIEW user_canonical_facts AS
SELECT DISTINCT ON (user_id, fact_key, language) 
    user_id, fact_key, fact_value, normalized_value, 
    confidence, occurrences, importance_score, last_seen, language
FROM user_facts 
WHERE is_active = TRUE 
ORDER BY user_id, fact_key, language, is_canonical DESC, confidence DESC, occurrences DESC;

CREATE VIEW enabled_features AS
SELECT feature_name, config, environment, description
FROM feature_flags 
WHERE enabled = TRUE;

-- Функция для hot-reload конфигурации
CREATE OR REPLACE FUNCTION reload_config(
    p_config_key VARCHAR,
    p_version VARCHAR,
    p_environment VARCHAR DEFAULT 'production'
) RETURNS BOOLEAN AS $$
BEGIN
    -- Деактивируем текущую конфигурацию
    UPDATE config_versions 
    SET active = FALSE 
    WHERE config_key = p_config_key 
      AND environment = p_environment;
    
    -- Активируем новую версию
    UPDATE config_versions 
    SET active = TRUE 
    WHERE config_key = p_config_key 
      AND version = p_version 
      AND environment = p_environment;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Config version not found: % v% in %', p_config_key, p_version, p_environment;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Комментарии к таблицам
COMMENT ON TABLE config_versions IS 'Версионированные конфигурации системы памяти с поддержкой окружений и hot-reload';
COMMENT ON TABLE feature_flags IS 'Флаги функций для условного включения возможностей';
COMMENT ON TABLE user_facts IS 'Извлеченные факты о пользователях с поддержкой языков, merge и ranking';
COMMENT ON TABLE extraction_patterns IS 'Динамические паттерны для извлечения фактов и определения намерений с приоритетами';
COMMENT ON TABLE user_configs IS 'Пользовательские переопределения конфигурации с поддержкой приоритетов';
COMMENT ON TABLE memory_topics IS 'Справочник тем/топиков для категоризации с поддержкой весов';
COMMENT ON TABLE memory_professions IS 'Справочник профессий с бонусами уверенности';
COMMENT ON TABLE memory_places IS 'Справочник мест и локаций с метаданными';

-- Первичная конфигурация флагов функций
INSERT INTO feature_flags (feature_name, enabled, environment, dependencies, description, config) VALUES
('pgvector_support', false, 'production', ARRAY['vector'], 'Поддержка векторных операций через pgvector', '{"vector_dim": 1536}'),
('pg_trgm_support', false, 'production', ARRAY['pg_trgm'], 'Поддержка fuzzy text search через pg_trgm', '{}'),
('llm_extraction', true, 'production', ARRAY[], 'Извлечение фактов через LLM', '{"model": "gpt-4o-mini", "temperature": 0.1}'),
('multilingual_support', true, 'production', ARRAY[], 'Поддержка множественных языков', '{"default_language": "ru", "supported": ["ru", "en"]}'),
('auto_summarization', true, 'production', ARRAY[], 'Автоматическая суммаризация эпизодов', '{"trigger_count": 50}');

-- Нотификация о завершении
SELECT 'Migration 001_dynamic_config_v2.sql completed successfully' AS status;
