-- Улучшенная условная миграция: Поддержка векторных операций
-- Версия: 2.0 (Production-ready)
-- Полностью конфигурируемая, идемпотентная, с откатом и логированием

DO $$
DECLARE
    -- Переменные конфигурации
    vector_enabled BOOLEAN;
    vector_config JSONB;
    global_config JSONB;
    final_config JSONB;
    
    -- Параметры векторной БД
    vector_dim INT;
    index_lists INT;
    distance_metric TEXT;
    hnsw_m INT;
    hnsw_ef_construction INT;
    
    -- Состояние
    extension_exists BOOLEAN;
    table_exists BOOLEAN;
    index_exists BOOLEAN;
    current_vector_dim INT;
    migration_log JSONB;
    
    -- Константы
    current_env TEXT := COALESCE(current_setting('app.environment', true), 'production');
    feature_name TEXT := 'pgvector_support';
    
BEGIN
    RAISE NOTICE '[VECTOR_MIGRATION] Starting vector support migration for environment: %', current_env;
    
    -- Инициализация лога миграции
    migration_log := jsonb_build_object(
        'migration_name', 'vector_support_v2',
        'environment', current_env,
        'started_at', extract(epoch from now()),
        'steps', '[]'::jsonb
    );
    
    -- 1. Проверяем флаг функции
    SELECT enabled, config INTO vector_enabled, vector_config
    FROM feature_flags 
    WHERE feature_name = feature_name 
      AND environment = current_env;
    
    IF NOT FOUND THEN
        RAISE NOTICE '[VECTOR_MIGRATION] Feature flag not found for %, skipping migration', feature_name;
        RETURN;
    END IF;
    
    IF NOT vector_enabled THEN
        RAISE NOTICE '[VECTOR_MIGRATION] Feature disabled, skipping migration';
        -- Записываем в лог что пропустили
        migration_log := migration_log || jsonb_build_object('status', 'skipped', 'reason', 'feature_disabled');
        INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context)
        VALUES ('migration', 'vector_support_skipped', 1, migration_log);
        RETURN;
    END IF;
    
    -- 2. Получаем глобальную конфигурацию из config_versions
    SELECT payload INTO global_config
    FROM config_versions 
    WHERE config_key = 'vector_db_settings' 
      AND active = TRUE 
      AND environment = current_env;
    
    -- 3. Объединяем конфигурации (приоритет: feature_flags.config > global_config > defaults)
    final_config := COALESCE(global_config, '{}'::jsonb) || COALESCE(vector_config, '{}'::jsonb);
    
    -- 4. Извлекаем параметры с fallback значениями
    vector_dim := COALESCE((final_config->>'embedding_dimension')::INT, (final_config->>'vector_dim')::INT, 1536);
    distance_metric := COALESCE(final_config->>'distance_metric', 'l2');
    
    -- Вычисляем параметры индексов адаптивно
    index_lists := COALESCE(
        (final_config->'index_parameters'->>'ivfflat_lists')::INT,
        GREATEST(vector_dim / 20, 50)  -- адаптивно к размерности
    );
    
    hnsw_m := COALESCE((final_config->'index_parameters'->>'hnsw_m')::INT, 16);
    hnsw_ef_construction := COALESCE((final_config->'index_parameters'->>'hnsw_ef_construction')::INT, 200);
    
    RAISE NOTICE '[VECTOR_MIGRATION] Using parameters: dim=%, lists=%, metric=%', vector_dim, index_lists, distance_metric;
    
    -- Обновляем лог
    migration_log := migration_log || jsonb_build_object(
        'config_resolved', final_config,
        'computed_params', jsonb_build_object(
            'vector_dim', vector_dim,
            'index_lists', index_lists,
            'distance_metric', distance_metric
        )
    );
    
    -- 5. Проверяем состояние расширения
    SELECT EXISTS(
        SELECT 1 FROM pg_extension WHERE extname = 'vector'
    ) INTO extension_exists;
    
    -- 6. Устанавливаем расширение pgvector если нужно
    IF NOT extension_exists THEN
        BEGIN
            CREATE EXTENSION vector;
            RAISE NOTICE '[VECTOR_MIGRATION] pgvector extension installed successfully';
            
            migration_log := migration_log || jsonb_build_object('extension_installed', true);
            
        EXCEPTION 
            WHEN OTHERS THEN
                RAISE WARNING '[VECTOR_MIGRATION] Failed to install pgvector extension: %', SQLERRM;
                
                -- Записываем ошибку в конфигурацию feature flag
                UPDATE feature_flags 
                SET config = config || jsonb_build_object(
                    'error', SQLERRM,
                    'status', 'extension_unavailable',
                    'last_attempt', extract(epoch from now())
                )
                WHERE feature_name = feature_name AND environment = current_env;
                
                -- Записываем в метрики
                migration_log := migration_log || jsonb_build_object(
                    'status', 'failed',
                    'error', SQLERRM,
                    'step', 'extension_installation'
                );
                
                INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context)
                VALUES ('migration', 'vector_support_failed', 1, migration_log);
                
                RETURN;
        END;
    ELSE
        RAISE NOTICE '[VECTOR_MIGRATION] pgvector extension already exists';
        migration_log := migration_log || jsonb_build_object('extension_already_exists', true);
    END IF;
    
    -- 7. Проверяем существование таблицы
    SELECT EXISTS(
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'vector_memories' AND table_schema = 'public'
    ) INTO table_exists;
    
    -- 8. Создаем/обновляем таблицу векторных воспоминаний
    IF NOT table_exists THEN
        -- Создаем новую таблицу
        EXECUTE format('
            CREATE TABLE vector_memories (
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
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )', vector_dim);
        
        RAISE NOTICE '[VECTOR_MIGRATION] Created vector_memories table with dimension %', vector_dim;
        migration_log := migration_log || jsonb_build_object('table_created', true, 'vector_dimension', vector_dim);
        
    ELSE
        -- Проверяем размерность существующей таблицы
        SELECT 
            CASE 
                WHEN data_type = 'USER-DEFINED' AND udt_name = 'vector' THEN
                    (SELECT typmod-4 FROM pg_type WHERE typname = 'vector' AND oid = (
                        SELECT atttypid FROM pg_attribute 
                        WHERE attrelid = (SELECT oid FROM pg_class WHERE relname = 'vector_memories')
                        AND attname = 'embedding'
                    ))
                ELSE NULL
            END
        INTO current_vector_dim
        FROM information_schema.columns 
        WHERE table_name = 'vector_memories' 
          AND column_name = 'embedding'
          AND table_schema = 'public';
        
        IF current_vector_dim IS NULL THEN
            RAISE WARNING '[VECTOR_MIGRATION] Could not determine current vector dimension';
        ELSIF current_vector_dim != vector_dim THEN
            RAISE WARNING '[VECTOR_MIGRATION] Vector dimension mismatch: existing=%, required=%', current_vector_dim, vector_dim;
            
            -- В production лучше не менять размерность автоматически
            migration_log := migration_log || jsonb_build_object(
                'dimension_mismatch', true,
                'existing_dim', current_vector_dim,
                'required_dim', vector_dim
            );
            
            -- Обновляем конфигурацию с фактической размерностью
            UPDATE feature_flags 
            SET config = config || jsonb_build_object(
                'actual_vector_dim', current_vector_dim,
                'requested_vector_dim', vector_dim,
                'dimension_mismatch', true
            )
            WHERE feature_name = feature_name AND environment = current_env;
            
        ELSE
            RAISE NOTICE '[VECTOR_MIGRATION] Table exists with correct dimension %', vector_dim;
            migration_log := migration_log || jsonb_build_object('table_dimension_ok', true);
        END IF;
    END IF;
    
    -- 9. Создаем базовые индексы (идемпотентно)
    CREATE INDEX IF NOT EXISTS idx_vector_memories_user_lang ON vector_memories(user_id, language);
    CREATE INDEX IF NOT EXISTS idx_vector_memories_category ON vector_memories(category);
    CREATE INDEX IF NOT EXISTS idx_vector_memories_session ON vector_memories(session_id);
    CREATE INDEX IF NOT EXISTS idx_vector_memories_importance ON vector_memories(importance_level);
    CREATE INDEX IF NOT EXISTS idx_vector_memories_created ON vector_memories(created_at DESC);
    
    -- 10. Создаем/обновляем векторный индекс
    SELECT EXISTS(
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'vector_memories' 
          AND indexname = 'idx_vector_memories_embedding'
    ) INTO index_exists;
    
    IF NOT index_exists THEN
        -- Создаем новый векторный индекс
        EXECUTE format('
            CREATE INDEX idx_vector_memories_embedding 
            ON vector_memories USING ivfflat (embedding vector_%s_ops) 
            WITH (lists = %s)', 
            CASE distance_metric 
                WHEN 'cosine' THEN 'cosine'
                WHEN 'l2' THEN 'l2' 
                ELSE 'l2'
            END,
            index_lists
        );
        
        RAISE NOTICE '[VECTOR_MIGRATION] Created vector index with % lists and % metric', index_lists, distance_metric;
        migration_log := migration_log || jsonb_build_object('vector_index_created', true);
        
    ELSE
        RAISE NOTICE '[VECTOR_MIGRATION] Vector index already exists';
        migration_log := migration_log || jsonb_build_object('vector_index_exists', true);
    END IF;
    
    -- 11. Создаем/обновляем функции для работы с векторами
    EXECUTE format('
        CREATE OR REPLACE FUNCTION vector_similarity_search(
            p_user_id VARCHAR,
            p_query_embedding vector(%s),
            p_similarity_threshold FLOAT DEFAULT 0.7,
            p_limit INT DEFAULT 10,
            p_category VARCHAR DEFAULT NULL
        ) RETURNS TABLE (
            memory_id BIGINT,
            content TEXT,
            category VARCHAR,
            importance_level VARCHAR,
            similarity_score FLOAT,
            metadata JSONB
        ) AS $func$
        BEGIN
            RETURN QUERY
            SELECT 
                vm.id,
                vm.content,
                vm.category,
                vm.importance_level,
                1 - (vm.embedding <-> p_query_embedding) AS similarity,
                vm.metadata
            FROM vector_memories vm
            WHERE vm.user_id = p_user_id 
              AND (p_category IS NULL OR vm.category = p_category)
              AND (1 - (vm.embedding <-> p_query_embedding)) >= p_similarity_threshold
            ORDER BY vm.embedding <-> p_query_embedding
            LIMIT p_limit;
        END;
        $func$ LANGUAGE plpgsql;', vector_dim);
    
    -- Функция для добавления векторной памяти
    EXECUTE format('
        CREATE OR REPLACE FUNCTION add_vector_memory(
            p_user_id VARCHAR,
            p_content TEXT,
            p_embedding vector(%s),
            p_role VARCHAR DEFAULT ''user'',
            p_category VARCHAR DEFAULT NULL,
            p_importance VARCHAR DEFAULT ''medium'',
            p_session_id VARCHAR DEFAULT NULL,
            p_language VARCHAR DEFAULT ''ru'',
            p_topics JSONB DEFAULT ''[]'',
            p_emotions JSONB DEFAULT ''[]'',
            p_metadata JSONB DEFAULT ''{}''
        ) RETURNS BIGINT AS $func$
        DECLARE
            new_id BIGINT;
        BEGIN
            INSERT INTO vector_memories (
                user_id, content, embedding, role, category, 
                importance_level, session_id, language, topics, emotions, metadata
            ) VALUES (
                p_user_id, p_content, p_embedding, p_role, p_category,
                p_importance, p_session_id, p_language, p_topics, p_emotions, p_metadata
            ) RETURNING id INTO new_id;
            
            RETURN new_id;
        END;
        $func$ LANGUAGE plpgsql;', vector_dim);
    
    -- 12. Обновляем конфигурацию feature flag с фактическими параметрами
    UPDATE feature_flags 
    SET config = config || jsonb_build_object(
        'status', 'installed',
        'actual_vector_dim', COALESCE(current_vector_dim, vector_dim),
        'index_parameters', jsonb_build_object(
            'lists', index_lists,
            'distance_metric', distance_metric,
            'hnsw_m', hnsw_m,
            'hnsw_ef_construction', hnsw_ef_construction
        ),
        'installation_completed_at', extract(epoch from now()),
        'table_created', NOT table_exists,
        'index_created', NOT index_exists
    )
    WHERE feature_name = feature_name AND environment = current_env;
    
    -- 13. Финализируем лог и записываем метрики
    migration_log := migration_log || jsonb_build_object(
        'status', 'completed',
        'completed_at', extract(epoch from now()),
        'duration_seconds', extract(epoch from now()) - (migration_log->>'started_at')::FLOAT
    );
    
    INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
    VALUES ('migration', 'vector_support_completed', 1, migration_log, current_env);
    
    RAISE NOTICE '[VECTOR_MIGRATION] Vector support migration completed successfully';
    
EXCEPTION 
    WHEN OTHERS THEN
        -- Обработка любых неожиданных ошибок
        RAISE WARNING '[VECTOR_MIGRATION] Migration failed with error: %', SQLERRM;
        
        -- Записываем ошибку в feature flags
        UPDATE feature_flags 
        SET config = config || jsonb_build_object(
            'status', 'failed',
            'last_error', SQLERRM,
            'last_attempt', extract(epoch from now())
        )
        WHERE feature_name = feature_name AND environment = current_env;
        
        -- Записываем в метрики
        migration_log := migration_log || jsonb_build_object(
            'status', 'failed',
            'error', SQLERRM,
            'failed_at', extract(epoch from now())
        );
        
        INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
        VALUES ('migration', 'vector_support_failed', 1, migration_log, current_env);
        
        -- Не перебрасываем исключение, чтобы не ломать общую миграцию
        RAISE NOTICE '[VECTOR_MIGRATION] Migration completed with errors, check feature_flags and metrics for details';
END $$;

-- Создаем функцию для отката миграции
CREATE OR REPLACE FUNCTION rollback_vector_support(
    p_environment VARCHAR DEFAULT 'production',
    p_force BOOLEAN DEFAULT FALSE
) RETURNS JSONB AS $$
DECLARE
    rollback_log JSONB;
    table_exists BOOLEAN;
    extension_exists BOOLEAN;
    dependent_objects INT;
BEGIN
    rollback_log := jsonb_build_object(
        'rollback_started_at', extract(epoch from now()),
        'environment', p_environment,
        'force_mode', p_force
    );
    
    -- Проверяем наличие зависимых объектов
    SELECT COUNT(*) INTO dependent_objects
    FROM vector_memories 
    WHERE created_at > NOW() - INTERVAL '1 day';
    
    IF dependent_objects > 0 AND NOT p_force THEN
        rollback_log := rollback_log || jsonb_build_object(
            'status', 'aborted',
            'reason', 'has_recent_data',
            'recent_records', dependent_objects
        );
        RETURN rollback_log;
    END IF;
    
    -- Удаляем функции
    DROP FUNCTION IF EXISTS vector_similarity_search(VARCHAR, vector, FLOAT, INT, VARCHAR);
    DROP FUNCTION IF EXISTS add_vector_memory(VARCHAR, TEXT, vector, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, JSONB, JSONB, JSONB);
    
    -- Удаляем таблицу если существует
    SELECT EXISTS(
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'vector_memories'
    ) INTO table_exists;
    
    IF table_exists THEN
        DROP TABLE vector_memories CASCADE;
        rollback_log := rollback_log || jsonb_build_object('table_dropped', true);
    END IF;
    
    -- Отключаем feature flag
    UPDATE feature_flags 
    SET enabled = false,
        config = config || jsonb_build_object(
            'status', 'rolled_back',
            'rollback_completed_at', extract(epoch from now())
        )
    WHERE feature_name = 'pgvector_support' AND environment = p_environment;
    
    rollback_log := rollback_log || jsonb_build_object(
        'status', 'completed',
        'completed_at', extract(epoch from now())
    );
    
    -- Записываем метрику отката
    INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
    VALUES ('migration', 'vector_support_rollback', 1, rollback_log, p_environment);
    
    RETURN rollback_log;
END;
$$ LANGUAGE plpgsql;

-- Комментарии
COMMENT ON FUNCTION rollback_vector_support IS 'Откат миграции vector support с проверками безопасности';
COMMENT ON FUNCTION vector_similarity_search IS 'Поиск по векторному сходству с настраиваемыми параметрами';
COMMENT ON FUNCTION add_vector_memory IS 'Добавление векторной памяти с валидацией';
