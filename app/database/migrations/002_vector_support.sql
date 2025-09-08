-- Условная миграция: Поддержка векторных операций
-- Версия: 1.0
-- Выполняется только если включен feature_flag 'pgvector_support'
-- Параметры: ${VECTOR_DIM:=1536}

-- Проверяем включен ли флаг векторной поддержки
DO $$
DECLARE
    vector_enabled BOOLEAN;
    vector_config JSONB;
    vector_dim INT;
BEGIN
    -- Проверяем флаг функции
    SELECT enabled, config INTO vector_enabled, vector_config
    FROM feature_flags 
    WHERE feature_name = 'pgvector_support' 
      AND environment = COALESCE(current_setting('app.environment', true), 'production');
    
    IF NOT FOUND OR NOT vector_enabled THEN
        RAISE NOTICE 'Skipping vector support migration - feature disabled';
        RETURN;
    END IF;
    
    -- Получаем размерность векторов из конфигурации
    vector_dim := COALESCE((vector_config->>'vector_dim')::INT, 1536);
    
    RAISE NOTICE 'Installing vector support with dimension: %', vector_dim;
    
    -- Создаем расширение pgvector если доступно
    BEGIN
        CREATE EXTENSION IF NOT EXISTS vector;
        RAISE NOTICE 'pgvector extension installed successfully';
    EXCEPTION 
        WHEN OTHERS THEN
            RAISE WARNING 'Failed to install pgvector extension: %', SQLERRM;
            -- Обновляем флаг как неактивный
            UPDATE feature_flags 
            SET enabled = false, 
                config = config || '{"error": "extension_unavailable"}'::jsonb
            WHERE feature_name = 'pgvector_support';
            RETURN;
    END;
    
    -- Создаем таблицу векторных воспоминаний с динамической размерностью
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS vector_memories (
            id BIGSERIAL PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            content TEXT NOT NULL,
            role VARCHAR(20), -- user, assistant, system
            category VARCHAR(50),
            importance_level VARCHAR(10), -- high, medium, low
            topics JSONB DEFAULT ''[]'',
            emotions JSONB DEFAULT ''[]'',
            embedding vector(%s),
            session_id VARCHAR(100),
            language VARCHAR(10) NOT NULL,
            metadata JSONB DEFAULT ''{}'',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )', vector_dim);
    
    -- Создаем индексы для векторной памяти
    CREATE INDEX IF NOT EXISTS idx_vector_memories_user ON vector_memories(user_id, language);
    CREATE INDEX IF NOT EXISTS idx_vector_memories_category ON vector_memories(category);
    CREATE INDEX IF NOT EXISTS idx_vector_memories_session ON vector_memories(session_id);
    CREATE INDEX IF NOT EXISTS idx_vector_memories_importance ON vector_memories(importance_level);
    
    -- Создаем векторный индекс с динамическими параметрами
    EXECUTE format('
        CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
        ON vector_memories USING ivfflat (embedding vector_l2_ops) 
        WITH (lists = %s)', GREATEST(vector_dim / 10, 50)); -- адаптируем количество списков к размерности
    
    -- Обновляем конфигурацию с фактической размерностью
    UPDATE feature_flags 
    SET config = config || jsonb_build_object('actual_vector_dim', vector_dim, 'status', 'installed')
    WHERE feature_name = 'pgvector_support';
    
    RAISE NOTICE 'Vector support migration completed successfully';
END $$;
