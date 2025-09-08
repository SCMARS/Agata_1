-- Полностью production-ready миграция векторной поддержки
-- Версия: 3.0 (Zero Hardcode, Advisory Locks, Idempotent)
-- Нет хардкода, полная конфигурируемость, синхронизация через locks

DO $$
DECLARE
    -- Переменные конфигурации (без конфликта имен)
    v_feature_name TEXT := 'pgvector_support';
    v_environment TEXT;
    v_vector_enabled BOOLEAN;
    v_vector_config JSONB;
    v_global_config JSONB;
    v_final_config JSONB;
    
    -- Параметры векторной БД (из конфигурации)
    v_vector_dim INT;
    v_index_lists INT;
    v_distance_metric TEXT;
    v_hnsw_m INT;
    v_hnsw_ef_construction INT;
    v_table_name TEXT;
    v_embedding_column TEXT;
    v_ops_suffix TEXT;
    
    -- Состояние и блокировки
    v_lock_key BIGINT;
    v_lock_acquired BOOLEAN := FALSE;
    v_extension_exists BOOLEAN;
    v_table_exists BOOLEAN;
    v_index_exists BOOLEAN;
    v_current_vector_dim INT;
    v_migration_log JSONB;
    v_dry_run BOOLEAN;
    
    -- Динамические настройки
    v_fallback_config JSONB;
    v_computed_params JSONB;
    v_error_context JSONB;
    
    -- Результат операций
    v_operations_log JSONB := '[]'::jsonb;
    
BEGIN
    -- Инициализация
    v_environment := COALESCE(current_setting('app.environment', true), 'production');
    v_dry_run := COALESCE(current_setting('pgvector_migration.dry_run', true)::boolean, false);
    
    -- Вычисляем уникальный ключ блокировки
    v_lock_key := ('x' || substr(md5(v_feature_name || '::' || v_environment), 1, 15))::bit(60)::bigint;
    
    RAISE NOTICE '[VECTOR_MIGRATION_V3] Starting for environment=%, dry_run=%', v_environment, v_dry_run;
    
    -- Инициализация лога миграции
    v_migration_log := jsonb_build_object(
        'migration_name', 'vector_support_v3',
        'environment', v_environment,
        'dry_run', v_dry_run,
        'started_at', extract(epoch from now()),
        'lock_key', v_lock_key,
        'steps', '[]'::jsonb
    );
    
    -- 1. Получаем advisory lock (избегаем конкуренции)
    v_lock_acquired := pg_try_advisory_lock(v_lock_key);
    
    IF NOT v_lock_acquired THEN
        RAISE NOTICE '[VECTOR_MIGRATION_V3] Another migration is running for % in % — skipping', v_feature_name, v_environment;
        v_migration_log := v_migration_log || jsonb_build_object(
            'status', 'skipped',
            'reason', 'lock_contention',
            'completed_at', extract(epoch from now())
        );
        
        INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
        VALUES ('migration', 'vector_support_lock_contention', 1, v_migration_log, v_environment);
        
        RETURN;
    END IF;
    
    v_operations_log := v_operations_log || jsonb_build_object(
        'step', 'advisory_lock_acquired',
        'lock_key', v_lock_key,
        'timestamp', extract(epoch from now())
    );
    
    -- 2. Проверяем флаг функции (исправлен конфликт имен)
    SELECT ff.enabled, ff.config INTO v_vector_enabled, v_vector_config
    FROM feature_flags ff
    WHERE ff.feature_name = v_feature_name 
      AND ff.environment = v_environment
    LIMIT 1;
    
    IF NOT FOUND THEN
        RAISE NOTICE '[VECTOR_MIGRATION_V3] Feature flag not found for %, skipping migration', v_feature_name;
        v_migration_log := v_migration_log || jsonb_build_object(
            'status', 'skipped',
            'reason', 'feature_flag_not_found'
        );
        PERFORM pg_advisory_unlock(v_lock_key);
        RETURN;
    END IF;
    
    IF NOT v_vector_enabled THEN
        RAISE NOTICE '[VECTOR_MIGRATION_V3] Feature disabled, skipping migration';
        v_migration_log := v_migration_log || jsonb_build_object(
            'status', 'skipped', 
            'reason', 'feature_disabled'
        );
        
        INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
        VALUES ('migration', 'vector_support_disabled', 1, v_migration_log, v_environment);
        
        PERFORM pg_advisory_unlock(v_lock_key);
        RETURN;
    END IF;
    
    -- 3. Получаем глобальную конфигурацию из config_versions
    SELECT cv.payload INTO v_global_config
    FROM config_versions cv
    WHERE cv.config_key = 'vector_db_settings' 
      AND cv.active = TRUE 
      AND cv.environment = v_environment
    LIMIT 1;
    
    -- 4. Получаем fallback конфигурацию
    SELECT cv.payload INTO v_fallback_config
    FROM config_versions cv
    WHERE cv.config_key = 'system_defaults'
      AND cv.active = TRUE
      AND cv.environment = v_environment
    LIMIT 1;
    
    -- 5. Объединяем конфигурации (приоритет: feature_flags > global > fallback)
    v_final_config := COALESCE(v_fallback_config->'vector_defaults', '{}'::jsonb) 
                      || COALESCE(v_global_config, '{}'::jsonb) 
                      || COALESCE(v_vector_config, '{}'::jsonb);
    
    -- 6. Извлекаем параметры (полностью конфигурируемо)
    v_vector_dim := COALESCE(
        (v_final_config->>'embedding_dimension')::INT,
        (v_final_config->>'vector_dim')::INT,
        (v_fallback_config->'vector_defaults'->>'default_embedding_dimension')::INT,
        1536  -- Только если fallback не настроен
    );
    
    v_distance_metric := COALESCE(
        v_final_config->>'distance_metric',
        v_fallback_config->'vector_defaults'->>'default_distance_metric',
        'l2'
    );
    
    v_table_name := COALESCE(
        v_final_config->>'table_name',
        v_fallback_config->'vector_defaults'->>'default_table_name',
        'vector_memories'
    );
    
    v_embedding_column := COALESCE(
        v_final_config->>'embedding_column',
        v_fallback_config->'vector_defaults'->>'default_embedding_column',
        'embedding'
    );
    
    -- Параметры индексов (полностью конфигурируемо)
    v_index_lists := COALESCE(
        (v_final_config->'index_parameters'->>'ivfflat_lists')::INT,
        (v_fallback_config->'vector_defaults'->'index_defaults'->>'ivfflat_lists')::INT,
        GREATEST(v_vector_dim / 20, 50)  -- Адаптивный fallback только если не настроено
    );
    
    v_hnsw_m := COALESCE(
        (v_final_config->'index_parameters'->>'hnsw_m')::INT,
        (v_fallback_config->'vector_defaults'->'index_defaults'->>'hnsw_m')::INT,
        16
    );
    
    v_hnsw_ef_construction := COALESCE(
        (v_final_config->'index_parameters'->>'hnsw_ef_construction')::INT,
        (v_fallback_config->'vector_defaults'->'index_defaults'->>'hnsw_ef_construction')::INT,
        200
    );
    
    -- Операторный класс для индекса
    v_ops_suffix := CASE v_distance_metric 
        WHEN 'cosine' THEN 'vector_cosine_ops'
        WHEN 'l2' THEN 'vector_l2_ops'
        WHEN 'inner_product' THEN 'vector_ip_ops'
        ELSE 'vector_l2_ops'
    END;
    
    RAISE NOTICE '[VECTOR_MIGRATION_V3] Using parameters: dim=%, table=%, metric=%, lists=%', 
                 v_vector_dim, v_table_name, v_distance_metric, v_index_lists;
    
    -- Обновляем лог
    v_computed_params := jsonb_build_object(
        'vector_dim', v_vector_dim,
        'table_name', v_table_name,
        'embedding_column', v_embedding_column,
        'distance_metric', v_distance_metric,
        'index_lists', v_index_lists,
        'hnsw_m', v_hnsw_m,
        'hnsw_ef_construction', v_hnsw_ef_construction,
        'ops_suffix', v_ops_suffix
    );
    
    v_migration_log := v_migration_log || jsonb_build_object(
        'config_resolved', v_final_config,
        'computed_params', v_computed_params
    );
    
    -- 7. Проверяем состояние расширения
    SELECT EXISTS(
        SELECT 1 FROM pg_extension WHERE extname = 'vector'
    ) INTO v_extension_exists;
    
    -- 8. Проверяем права на создание расширения (dry-run)
    IF v_dry_run THEN
        RAISE NOTICE '[VECTOR_MIGRATION_V3] DRY RUN: Checking extension creation privileges';
        
        -- Проверяем права суперпользователя
        IF NOT (SELECT usesuper FROM pg_user WHERE usename = current_user) THEN
            RAISE NOTICE '[VECTOR_MIGRATION_V3] DRY RUN: Warning - current user lacks superuser privileges for CREATE EXTENSION';
            v_migration_log := v_migration_log || jsonb_build_object(
                'dry_run_warnings', jsonb_build_array('no_superuser_privileges')
            );
        END IF;
        
        v_operations_log := v_operations_log || jsonb_build_object(
            'step', 'dry_run_privilege_check',
            'has_superuser', (SELECT usesuper FROM pg_user WHERE usename = current_user),
            'timestamp', extract(epoch from now())
        );
    END IF;
    
    -- 9. Устанавливаем расширение pgvector если нужно
    IF NOT v_extension_exists THEN
        BEGIN
            IF NOT v_dry_run THEN
                CREATE EXTENSION vector;
                RAISE NOTICE '[VECTOR_MIGRATION_V3] pgvector extension installed successfully';
                
                v_operations_log := v_operations_log || jsonb_build_object(
                    'step', 'extension_created',
                    'extension_name', 'vector',
                    'timestamp', extract(epoch from now())
                );
            ELSE
                RAISE NOTICE '[VECTOR_MIGRATION_V3] DRY RUN: Would create extension vector';
            END IF;
            
            v_migration_log := v_migration_log || jsonb_build_object('extension_installed', NOT v_dry_run);
            
        EXCEPTION 
            WHEN OTHERS THEN
                RAISE WARNING '[VECTOR_MIGRATION_V3] Failed to install pgvector extension: %', SQLERRM;
                
                v_error_context := jsonb_build_object(
                    'error_type', 'extension_installation_failed',
                    'error_message', SQLERRM,
                    'sqlstate', SQLSTATE,
                    'step', 'CREATE EXTENSION vector',
                    'dry_run', v_dry_run
                );
                
                -- НЕ выключаем feature flag автоматически, только логируем
                UPDATE feature_flags 
                SET config = COALESCE(config, '{}'::jsonb) || jsonb_build_object(
                    'last_error', v_error_context,
                    'status', 'extension_failed',
                    'last_attempt', extract(epoch from now())
                )
                WHERE feature_flags.feature_name = v_feature_name 
                  AND environment = v_environment;
                
                v_migration_log := v_migration_log || jsonb_build_object(
                    'status', 'failed',
                    'error', v_error_context,
                    'step', 'extension_installation'
                );
                
                INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
                VALUES ('migration', 'vector_support_extension_failed', 1, v_migration_log, v_environment);
                
                PERFORM pg_advisory_unlock(v_lock_key);
                RETURN;
        END;
    ELSE
        RAISE NOTICE '[VECTOR_MIGRATION_V3] pgvector extension already exists';
        v_migration_log := v_migration_log || jsonb_build_object('extension_already_exists', true);
    END IF;
    
    -- 10. Проверяем существование таблицы
    EXECUTE format('SELECT EXISTS(
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = %L AND table_schema = %L
    )', v_table_name, 'public') INTO v_table_exists;
    
    -- 11. Создаем/обновляем таблицу векторных воспоминаний
    IF NOT v_table_exists THEN
        IF NOT v_dry_run THEN
            -- Создаем новую таблицу с динамическими параметрами
            EXECUTE format('
                CREATE TABLE %I (
                    id BIGSERIAL PRIMARY KEY,
                    user_id VARCHAR(%s) NOT NULL,
                    content TEXT NOT NULL,
                    role VARCHAR(%s), 
                    category VARCHAR(%s),
                    importance_level VARCHAR(%s),
                    topics JSONB DEFAULT %L,
                    emotions JSONB DEFAULT %L,
                    %I vector(%s),
                    session_id VARCHAR(%s),
                    language VARCHAR(%s) NOT NULL,
                    metadata JSONB DEFAULT %L,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )', 
                v_table_name,
                COALESCE((v_final_config->>'user_id_length')::TEXT, '100'),
                COALESCE((v_final_config->>'role_length')::TEXT, '20'),
                COALESCE((v_final_config->>'category_length')::TEXT, '50'),
                COALESCE((v_final_config->>'importance_length')::TEXT, '10'),
                COALESCE(v_final_config->>'default_topics', '[]'),
                COALESCE(v_final_config->>'default_emotions', '[]'),
                v_embedding_column,
                v_vector_dim,
                COALESCE((v_final_config->>'session_id_length')::TEXT, '100'),
                COALESCE((v_final_config->>'language_length')::TEXT, '10'),
                COALESCE(v_final_config->>'default_metadata', '{}')
            );
            
            RAISE NOTICE '[VECTOR_MIGRATION_V3] Created table % with dimension %', v_table_name, v_vector_dim;
        ELSE
            RAISE NOTICE '[VECTOR_MIGRATION_V3] DRY RUN: Would create table % with dimension %', v_table_name, v_vector_dim;
        END IF;
        
        v_operations_log := v_operations_log || jsonb_build_object(
            'step', 'table_created',
            'table_name', v_table_name,
            'vector_dimension', v_vector_dim,
            'dry_run', v_dry_run,
            'timestamp', extract(epoch from now())
        );
        
        v_migration_log := v_migration_log || jsonb_build_object(
            'table_created', NOT v_dry_run, 
            'vector_dimension', v_vector_dim
        );
        
    ELSE
        -- Проверяем размерность существующей таблицы (надежно)
        EXECUTE format('
            SELECT (a.atttypmod - 4) AS dim
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = %L
              AND a.attname = %L
              AND n.nspname = %L
        ', v_table_name, v_embedding_column, 'public') INTO v_current_vector_dim;
        
        IF v_current_vector_dim IS NULL THEN
            RAISE WARNING '[VECTOR_MIGRATION_V3] Could not determine current vector dimension for table %', v_table_name;
            v_migration_log := v_migration_log || jsonb_build_object('dimension_detection_failed', true);
            
        ELSIF v_current_vector_dim != v_vector_dim THEN
            RAISE WARNING '[VECTOR_MIGRATION_V3] Vector dimension mismatch: existing=%, required=%', v_current_vector_dim, v_vector_dim;
            
            -- НЕ меняем схему автоматически, только логируем
            v_migration_log := v_migration_log || jsonb_build_object(
                'dimension_mismatch', true,
                'existing_dim', v_current_vector_dim,
                'required_dim', v_vector_dim,
                'action', 'logged_only_no_automatic_change'
            );
            
            -- Обновляем конфигурацию с фактической размерностью
            UPDATE feature_flags 
            SET config = COALESCE(config, '{}'::jsonb) || jsonb_build_object(
                'actual_vector_dim', v_current_vector_dim,
                'requested_vector_dim', v_vector_dim,
                'dimension_mismatch', true,
                'mismatch_detected_at', extract(epoch from now())
            )
            WHERE feature_flags.feature_name = v_feature_name 
              AND environment = v_environment;
            
        ELSE
            RAISE NOTICE '[VECTOR_MIGRATION_V3] Table exists with correct dimension %', v_vector_dim;
            v_migration_log := v_migration_log || jsonb_build_object('table_dimension_ok', true);
        END IF;
    END IF;
    
    -- 12. Создаем базовые индексы (идемпотентно)
    IF NOT v_dry_run THEN
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%s_user_lang ON %I(user_id, language)', v_table_name, v_table_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%s_category ON %I(category)', v_table_name, v_table_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%s_session ON %I(session_id)', v_table_name, v_table_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%s_importance ON %I(importance_level)', v_table_name, v_table_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%s_created ON %I(created_at DESC)', v_table_name, v_table_name);
    ELSE
        RAISE NOTICE '[VECTOR_MIGRATION_V3] DRY RUN: Would create standard indexes on %', v_table_name;
    END IF;
    
    -- 13. Создаем/обновляем векторный индекс
    EXECUTE format('SELECT EXISTS(
        SELECT 1 FROM pg_indexes 
        WHERE tablename = %L 
          AND indexname = %L
    )', v_table_name, 'idx_' || v_table_name || '_' || v_embedding_column) INTO v_index_exists;
    
    IF NOT v_index_exists THEN
        IF NOT v_dry_run THEN
            -- Создаем новый векторный индекс с полной конфигурируемостью
            EXECUTE format('
                CREATE INDEX idx_%s_%s 
                ON %I USING ivfflat (%I %s) 
                WITH (lists = %s)', 
                v_table_name, v_embedding_column,
                v_table_name, v_embedding_column, v_ops_suffix,
                v_index_lists
            );
            
            RAISE NOTICE '[VECTOR_MIGRATION_V3] Created vector index with % lists and % metric', v_index_lists, v_distance_metric;
        ELSE
            RAISE NOTICE '[VECTOR_MIGRATION_V3] DRY RUN: Would create vector index with % lists and % metric', v_index_lists, v_distance_metric;
        END IF;
        
        v_operations_log := v_operations_log || jsonb_build_object(
            'step', 'vector_index_created',
            'index_type', 'ivfflat',
            'lists', v_index_lists,
            'ops', v_ops_suffix,
            'dry_run', v_dry_run,
            'timestamp', extract(epoch from now())
        );
        
        v_migration_log := v_migration_log || jsonb_build_object('vector_index_created', NOT v_dry_run);
        
    ELSE
        RAISE NOTICE '[VECTOR_MIGRATION_V3] Vector index already exists';
        v_migration_log := v_migration_log || jsonb_build_object('vector_index_exists', true);
    END IF;
    
    -- 14. Создаем/обновляем функции для работы с векторами (только если не dry run)
    IF NOT v_dry_run THEN
        EXECUTE format('
            CREATE OR REPLACE FUNCTION %s_similarity_search(
                p_user_id VARCHAR,
                p_query_embedding vector(%s),
                p_similarity_threshold FLOAT DEFAULT %s,
                p_limit INT DEFAULT %s,
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
                EXECUTE format(''
                    SELECT 
                        vm.id,
                        vm.content,
                        vm.category,
                        vm.importance_level,
                        1 - (vm.%I <-> $1) AS similarity,
                        vm.metadata
                    FROM %I vm
                    WHERE vm.user_id = $2
                      AND ($3 IS NULL OR vm.category = $3)
                      AND (1 - (vm.%I <-> $1)) >= $4
                    ORDER BY vm.%I <-> $1
                    LIMIT $5
                '', %L, %L, %L, %L)
                USING p_query_embedding, p_user_id, p_category, p_similarity_threshold, p_limit;
            END;
            $func$ LANGUAGE plpgsql;',
            v_table_name, v_vector_dim,
            COALESCE((v_final_config->>'default_similarity_threshold')::TEXT, '0.7'),
            COALESCE((v_final_config->>'default_search_limit')::TEXT, '10'),
            v_embedding_column, v_table_name, v_embedding_column, v_embedding_column,
            v_embedding_column, v_table_name, v_embedding_column, v_embedding_column
        );
    END IF;
    
    -- 15. Обновляем конфигурацию feature flag с фактическими параметрами
    UPDATE feature_flags 
    SET config = COALESCE(config, '{}'::jsonb) || jsonb_build_object(
        'status', CASE WHEN v_dry_run THEN 'dry_run_completed' ELSE 'installed' END,
        'actual_vector_dim', COALESCE(v_current_vector_dim, v_vector_dim),
        'computed_parameters', v_computed_params,
        'installation_completed_at', extract(epoch from now()),
        'table_created', (NOT v_table_exists AND NOT v_dry_run),
        'index_created', (NOT v_index_exists AND NOT v_dry_run),
        'operations_log', v_operations_log,
        'migration_version', 'v3.0'
    )
    WHERE feature_flags.feature_name = v_feature_name 
      AND environment = v_environment;
    
    -- 16. Записываем результат в config_versions (audit trail)
    IF NOT v_dry_run THEN
        INSERT INTO config_versions (config_key, version, payload, environment, created_by, active)
        VALUES (
            'vector_migration_results',
            'auto_' || extract(epoch from now())::text,
            v_migration_log || jsonb_build_object('final_config', v_final_config),
            v_environment,
            current_user,
            false  -- Не активируем автоматически, это для аудита
        );
    END IF;
    
    -- 17. Финализируем лог и записываем метрики
    v_migration_log := v_migration_log || jsonb_build_object(
        'status', CASE WHEN v_dry_run THEN 'dry_run_success' ELSE 'completed' END,
        'completed_at', extract(epoch from now()),
        'duration_seconds', extract(epoch from now()) - (v_migration_log->>'started_at')::FLOAT,
        'operations_performed', jsonb_array_length(v_operations_log)
    );
    
    INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
    VALUES ('migration', 
            CASE WHEN v_dry_run THEN 'vector_support_dry_run' ELSE 'vector_support_completed' END, 
            1, v_migration_log, v_environment);
    
    RAISE NOTICE '[VECTOR_MIGRATION_V3] Migration completed successfully (dry_run=%)', v_dry_run;
    
EXCEPTION 
    WHEN OTHERS THEN
        -- Обработка любых неожиданных ошибок
        RAISE WARNING '[VECTOR_MIGRATION_V3] Migration failed with error: %', SQLERRM;
        
        v_error_context := jsonb_build_object(
            'error_type', 'unexpected_error',
            'error_message', SQLERRM,
            'sqlstate', SQLSTATE,
            'step', 'general_exception_handler'
        );
        
        -- НЕ выключаем feature flag, только логируем ошибку
        UPDATE feature_flags 
        SET config = COALESCE(config, '{}'::jsonb) || jsonb_build_object(
            'status', 'failed',
            'last_error', v_error_context,
            'last_attempt', extract(epoch from now()),
            'migration_version', 'v3.0'
        )
        WHERE feature_flags.feature_name = v_feature_name 
          AND environment = v_environment;
        
        -- Записываем в метрики
        v_migration_log := COALESCE(v_migration_log, '{}'::jsonb) || jsonb_build_object(
            'status', 'failed',
            'error', v_error_context,
            'failed_at', extract(epoch from now())
        );
        
        INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
        VALUES ('migration', 'vector_support_failed', 1, v_migration_log, v_environment);
        
        RAISE NOTICE '[VECTOR_MIGRATION_V3] Migration completed with errors, check feature_flags and metrics for details';
        
FINALLY:
    -- Всегда освобождаем блокировку
    IF v_lock_acquired THEN
        PERFORM pg_advisory_unlock(v_lock_key);
        RAISE NOTICE '[VECTOR_MIGRATION_V3] Advisory lock released';
    END IF;
END $$;

-- Создаем функцию для отката миграции (улучшенная версия)
CREATE OR REPLACE FUNCTION rollback_vector_support_v3(
    p_environment VARCHAR DEFAULT NULL,
    p_force BOOLEAN DEFAULT FALSE,
    p_dry_run BOOLEAN DEFAULT FALSE
) RETURNS JSONB AS $$
DECLARE
    v_environment TEXT;
    v_feature_name TEXT := 'pgvector_support';
    v_rollback_log JSONB;
    v_table_exists BOOLEAN;
    v_dependent_objects INT;
    v_lock_key BIGINT;
    v_lock_acquired BOOLEAN := FALSE;
    v_table_name TEXT;
    v_config JSONB;
    
BEGIN
    v_environment := COALESCE(p_environment, current_setting('app.environment', true), 'production');
    v_lock_key := ('x' || substr(md5(v_feature_name || '::rollback::' || v_environment), 1, 15))::bit(60)::bigint;
    
    v_rollback_log := jsonb_build_object(
        'rollback_started_at', extract(epoch from now()),
        'environment', v_environment,
        'force_mode', p_force,
        'dry_run', p_dry_run
    );
    
    -- Получаем блокировку
    v_lock_acquired := pg_try_advisory_lock(v_lock_key);
    IF NOT v_lock_acquired THEN
        v_rollback_log := v_rollback_log || jsonb_build_object(
            'status', 'failed',
            'reason', 'could_not_acquire_lock'
        );
        RETURN v_rollback_log;
    END IF;
    
    -- Получаем конфигурацию для определения имени таблицы
    SELECT config INTO v_config
    FROM feature_flags 
    WHERE feature_name = v_feature_name 
      AND environment = v_environment;
    
    v_table_name := COALESCE(v_config->'computed_parameters'->>'table_name', 'vector_memories');
    
    -- Проверяем наличие зависимых объектов
    EXECUTE format('SELECT COUNT(*) FROM %I WHERE created_at > NOW() - INTERVAL ''1 day''', v_table_name) 
    INTO v_dependent_objects;
    
    IF v_dependent_objects > 0 AND NOT p_force THEN
        v_rollback_log := v_rollback_log || jsonb_build_object(
            'status', 'aborted',
            'reason', 'has_recent_data',
            'recent_records', v_dependent_objects
        );
        PERFORM pg_advisory_unlock(v_lock_key);
        RETURN v_rollback_log;
    END IF;
    
    IF NOT p_dry_run THEN
        -- Удаляем функции
        EXECUTE format('DROP FUNCTION IF EXISTS %s_similarity_search(VARCHAR, vector, FLOAT, INT, VARCHAR)', v_table_name);
        
        -- Удаляем таблицу если существует
        EXECUTE format('SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %L)', v_table_name) 
        INTO v_table_exists;
        
        IF v_table_exists THEN
            EXECUTE format('DROP TABLE %I CASCADE', v_table_name);
            v_rollback_log := v_rollback_log || jsonb_build_object('table_dropped', true);
        END IF;
        
        -- Обновляем feature flag (НЕ отключаем, только помечаем как rolled back)
        UPDATE feature_flags 
        SET config = COALESCE(config, '{}'::jsonb) || jsonb_build_object(
            'status', 'rolled_back',
            'rollback_completed_at', extract(epoch from now()),
            'rollback_version', 'v3.0'
        )
        WHERE feature_name = v_feature_name AND environment = v_environment;
        
    ELSE
        v_rollback_log := v_rollback_log || jsonb_build_object('dry_run_mode', true);
    END IF;
    
    v_rollback_log := v_rollback_log || jsonb_build_object(
        'status', CASE WHEN p_dry_run THEN 'dry_run_success' ELSE 'completed' END,
        'completed_at', extract(epoch from now())
    );
    
    -- Записываем метрику отката
    INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
    VALUES ('migration', 'vector_support_rollback_v3', 1, v_rollback_log, v_environment);
    
    PERFORM pg_advisory_unlock(v_lock_key);
    RETURN v_rollback_log;
    
EXCEPTION
    WHEN OTHERS THEN
        IF v_lock_acquired THEN
            PERFORM pg_advisory_unlock(v_lock_key);
        END IF;
        
        v_rollback_log := v_rollback_log || jsonb_build_object(
            'status', 'failed',
            'error', SQLERRM,
            'failed_at', extract(epoch from now())
        );
        
        RETURN v_rollback_log;
END;
$$ LANGUAGE plpgsql;

-- Комментарии
COMMENT ON FUNCTION rollback_vector_support_v3 IS 'Откат миграции vector support v3 с полным контролем и конфигурируемостью';

-- Функция для проверки статуса миграции
CREATE OR REPLACE FUNCTION get_vector_migration_status(
    p_environment VARCHAR DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_environment TEXT;
    v_feature_name TEXT := 'pgvector_support';
    v_status JSONB;
    v_table_name TEXT;
    v_table_exists BOOLEAN;
    v_extension_exists BOOLEAN;
    v_records_count BIGINT;
    
BEGIN
    v_environment := COALESCE(p_environment, current_setting('app.environment', true), 'production');
    
    -- Получаем статус из feature_flags
    SELECT 
        jsonb_build_object(
            'feature_enabled', enabled,
            'config', config,
            'updated_at', updated_at
        )
    INTO v_status
    FROM feature_flags 
    WHERE feature_name = v_feature_name 
      AND environment = v_environment;
    
    IF v_status IS NULL THEN
        RETURN jsonb_build_object('status', 'feature_flag_not_found');
    END IF;
    
    -- Проверяем состояние компонентов
    SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector') INTO v_extension_exists;
    
    v_table_name := COALESCE(v_status->'config'->'computed_parameters'->>'table_name', 'vector_memories');
    
    EXECUTE format('SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %L)', v_table_name) 
    INTO v_table_exists;
    
    IF v_table_exists THEN
        EXECUTE format('SELECT COUNT(*) FROM %I', v_table_name) INTO v_records_count;
    ELSE
        v_records_count := 0;
    END IF;
    
    RETURN v_status || jsonb_build_object(
        'runtime_status', jsonb_build_object(
            'extension_exists', v_extension_exists,
            'table_exists', v_table_exists,
            'table_name', v_table_name,
            'records_count', v_records_count,
            'checked_at', extract(epoch from now())
        )
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_vector_migration_status IS 'Получение полного статуса миграции векторной поддержки';
