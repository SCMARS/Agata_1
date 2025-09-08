-- Улучшенная условная миграция: Поддержка полнотекстового поиска
-- Версия: 2.0 (Production-ready)
-- Полностью конфигурируемая, идемпотентная, с откатом и логированием

DO $$
DECLARE
    -- Переменные конфигурации
    trgm_enabled BOOLEAN;
    trgm_config JSONB;
    global_config JSONB;
    final_config JSONB;
    
    -- Параметры поиска
    supported_languages TEXT[];
    similarity_thresholds JSONB;
    default_similarity FLOAT;
    max_results_default INT;
    
    -- Состояние
    extension_exists BOOLEAN;
    indexes_exist RECORD;
    functions_exist RECORD;
    migration_log JSONB;
    
    -- Константы
    current_env TEXT := COALESCE(current_setting('app.environment', true), 'production');
    feature_name TEXT := 'pg_trgm_support';
    
BEGIN
    RAISE NOTICE '[FULLTEXT_MIGRATION] Starting fulltext support migration for environment: %', current_env;
    
    -- Инициализация лога миграции
    migration_log := jsonb_build_object(
        'migration_name', 'fulltext_support_v2',
        'environment', current_env,
        'started_at', extract(epoch from now()),
        'steps', '[]'::jsonb
    );
    
    -- 1. Проверяем флаг функции
    SELECT enabled, config INTO trgm_enabled, trgm_config
    FROM feature_flags 
    WHERE feature_name = feature_name 
      AND environment = current_env;
    
    IF NOT FOUND THEN
        RAISE NOTICE '[FULLTEXT_MIGRATION] Feature flag not found for %, skipping migration', feature_name;
        RETURN;
    END IF;
    
    IF NOT trgm_enabled THEN
        RAISE NOTICE '[FULLTEXT_MIGRATION] Feature disabled, skipping migration';
        migration_log := migration_log || jsonb_build_object('status', 'skipped', 'reason', 'feature_disabled');
        INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context)
        VALUES ('migration', 'fulltext_support_skipped', 1, migration_log);
        RETURN;
    END IF;
    
    -- 2. Получаем глобальную конфигурацию из config_versions
    SELECT payload INTO global_config
    FROM config_versions 
    WHERE config_key = 'search_settings' 
      AND active = TRUE 
      AND environment = current_env;
    
    -- 3. Объединяем конфигурации
    final_config := COALESCE(global_config, '{}'::jsonb) || COALESCE(trgm_config, '{}'::jsonb);
    
    -- 4. Извлекаем параметры с fallback значениями
    -- Получаем поддерживаемые языки
    SELECT ARRAY(
        SELECT jsonb_array_elements_text(
            COALESCE(
                final_config->'supported_languages',
                (SELECT config->'supported' FROM feature_flags 
                 WHERE feature_name = 'multilingual_support' AND enabled = true),
                '["ru", "en"]'::jsonb
            )
        )
    ) INTO supported_languages;
    
    -- Пороги похожести для разных типов поиска
    similarity_thresholds := COALESCE(final_config->'similarity_thresholds', '{
        "fact_similarity_threshold": 0.3,
        "episode_similarity_threshold": 0.4,
        "default_similarity": 0.3
    }'::jsonb);
    
    default_similarity := COALESCE((similarity_thresholds->>'default_similarity')::FLOAT, 0.3);
    max_results_default := COALESCE((final_config->>'max_results_default')::INT, 10);
    
    RAISE NOTICE '[FULLTEXT_MIGRATION] Using parameters: languages=%, default_similarity=%, max_results=%', 
                 supported_languages, default_similarity, max_results_default;
    
    -- Обновляем лог
    migration_log := migration_log || jsonb_build_object(
        'config_resolved', final_config,
        'computed_params', jsonb_build_object(
            'supported_languages', supported_languages,
            'similarity_thresholds', similarity_thresholds,
            'max_results_default', max_results_default
        )
    );
    
    -- 5. Проверяем состояние расширения
    SELECT EXISTS(
        SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
    ) INTO extension_exists;
    
    -- 6. Устанавливаем расширение pg_trgm если нужно
    IF NOT extension_exists THEN
        BEGIN
            CREATE EXTENSION pg_trgm;
            RAISE NOTICE '[FULLTEXT_MIGRATION] pg_trgm extension installed successfully';
            migration_log := migration_log || jsonb_build_object('extension_installed', true);
            
        EXCEPTION 
            WHEN OTHERS THEN
                RAISE WARNING '[FULLTEXT_MIGRATION] Failed to install pg_trgm extension: %', SQLERRM;
                
                -- Записываем ошибку в конфигурацию feature flag
                UPDATE feature_flags 
                SET config = config || jsonb_build_object(
                    'error', SQLERRM,
                    'status', 'extension_unavailable',
                    'last_attempt', extract(epoch from now())
                )
                WHERE feature_name = feature_name AND environment = current_env;
                
                migration_log := migration_log || jsonb_build_object(
                    'status', 'failed',
                    'error', SQLERRM,
                    'step', 'extension_installation'
                );
                
                INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context)
                VALUES ('migration', 'fulltext_support_failed', 1, migration_log);
                
                RETURN;
        END;
    ELSE
        RAISE NOTICE '[FULLTEXT_MIGRATION] pg_trgm extension already exists';
        migration_log := migration_log || jsonb_build_object('extension_already_exists', true);
    END IF;
    
    -- 7. Проверяем состояние индексов (идемпотентно)
    SELECT 
        EXISTS(SELECT 1 FROM pg_indexes WHERE tablename = 'vector_memories' AND indexname = 'idx_vector_memories_content_trgm') as vector_memories_trgm,
        EXISTS(SELECT 1 FROM pg_indexes WHERE tablename = 'user_facts' AND indexname = 'idx_user_facts_normalized_trgm') as user_facts_trgm,
        EXISTS(SELECT 1 FROM pg_indexes WHERE tablename = 'memory_episodes' AND indexname = 'idx_memory_episodes_summary_trgm') as episodes_trgm
    INTO indexes_exist;
    
    -- 8. Создаем триграммные индексы (идемпотентно)
    
    -- Индекс для vector_memories (если таблица существует)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vector_memories' AND table_schema = 'public') THEN
        IF NOT indexes_exist.vector_memories_trgm THEN
            CREATE INDEX idx_vector_memories_content_trgm 
            ON vector_memories USING gin (content gin_trgm_ops);
            RAISE NOTICE '[FULLTEXT_MIGRATION] Created trigram index for vector_memories.content';
        ELSE
            RAISE NOTICE '[FULLTEXT_MIGRATION] Trigram index for vector_memories already exists';
        END IF;
    END IF;
    
    -- Индекс для user_facts
    IF NOT indexes_exist.user_facts_trgm THEN
        CREATE INDEX idx_user_facts_normalized_trgm 
        ON user_facts USING gin (normalized_value gin_trgm_ops) 
        WHERE is_active = TRUE;
        RAISE NOTICE '[FULLTEXT_MIGRATION] Created trigram index for user_facts.normalized_value';
    ELSE
        RAISE NOTICE '[FULLTEXT_MIGRATION] Trigram index for user_facts already exists';
    END IF;
    
    -- Индекс для memory_episodes
    IF NOT indexes_exist.episodes_trgm THEN
        CREATE INDEX idx_memory_episodes_summary_trgm 
        ON memory_episodes USING gin (summary gin_trgm_ops) 
        WHERE summary IS NOT NULL;
        RAISE NOTICE '[FULLTEXT_MIGRATION] Created trigram index for memory_episodes.summary';
    ELSE
        RAISE NOTICE '[FULLTEXT_MIGRATION] Trigram index for memory_episodes already exists';
    END IF;
    
    -- Дополнительные полнотекстовые индексы для разных языков
    -- Создаем только если не существуют
    DECLARE
        lang TEXT;
        index_name TEXT;
    BEGIN
        FOREACH lang IN ARRAY supported_languages LOOP
            -- Полнотекстовый индекс для фактов по языкам
            index_name := format('idx_user_facts_fulltext_%s', lang);
            
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = index_name) THEN
                CASE lang
                    WHEN 'ru' THEN
                        EXECUTE format('CREATE INDEX %I ON user_facts USING gin(to_tsvector(''russian'', fact_value)) WHERE language = ''ru'' AND is_active = TRUE', index_name);
                    WHEN 'en' THEN
                        EXECUTE format('CREATE INDEX %I ON user_facts USING gin(to_tsvector(''english'', fact_value)) WHERE language = ''en'' AND is_active = TRUE', index_name);
                    ELSE
                        EXECUTE format('CREATE INDEX %I ON user_facts USING gin(to_tsvector(''simple'', fact_value)) WHERE language = %L AND is_active = TRUE', index_name, lang);
                END CASE;
                
                RAISE NOTICE '[FULLTEXT_MIGRATION] Created fulltext index for language: %', lang;
            END IF;
        END LOOP;
    END;
    
    -- 9. Проверяем существование функций
    SELECT 
        EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'fuzzy_search_facts') as fuzzy_search_facts,
        EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'fuzzy_search_episodes') as fuzzy_search_episodes,
        EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'combined_text_search') as combined_text_search,
        EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'fulltext_search_facts') as fulltext_search_facts
    INTO functions_exist;
    
    -- 10. Создаем/обновляем функции поиска
    
    -- Улучшенная функция нечеткого поиска фактов
    CREATE OR REPLACE FUNCTION fuzzy_search_facts(
        p_user_id VARCHAR,
        p_query TEXT,
        p_similarity_threshold FLOAT DEFAULT NULL,
        p_limit INT DEFAULT NULL,
        p_language VARCHAR DEFAULT NULL
    ) RETURNS TABLE (
        fact_id BIGINT,
        fact_key VARCHAR,
        fact_value TEXT,
        normalized_value TEXT,
        confidence FLOAT,
        similarity_score FLOAT,
        language VARCHAR
    ) AS $func$
    DECLARE
        effective_threshold FLOAT;
        effective_limit INT;
        search_config JSONB;
    BEGIN
        -- Получаем эффективную конфигурацию
        search_config := get_effective_config('search_settings', p_user_id);
        
        effective_threshold := COALESCE(p_similarity_threshold, 
                                       (search_config->>'fact_similarity_threshold')::FLOAT, 
                                       0.3);
        effective_limit := COALESCE(p_limit, 
                                   (search_config->>'max_fact_results')::INT, 
                                   10);
        
        RETURN QUERY
        SELECT 
            uf.id,
            uf.fact_key,
            uf.fact_value,
            uf.normalized_value,
            uf.confidence,
            COALESCE(similarity(uf.normalized_value, p_query), 0.0) AS sim_score,
            uf.language
        FROM user_facts uf
        WHERE uf.user_id = p_user_id 
          AND uf.is_active = TRUE
          AND (p_language IS NULL OR uf.language = p_language)
          AND uf.normalized_value IS NOT NULL
          AND COALESCE(similarity(uf.normalized_value, p_query), 0.0) >= effective_threshold
        ORDER BY sim_score DESC, uf.confidence DESC, uf.importance_score DESC
        LIMIT effective_limit;
    END;
    $func$ LANGUAGE plpgsql;
    
    -- Улучшенная функция поиска по эпизодам
    CREATE OR REPLACE FUNCTION fuzzy_search_episodes(
        p_user_id VARCHAR,
        p_query TEXT,
        p_similarity_threshold FLOAT DEFAULT NULL,
        p_limit INT DEFAULT NULL,
        p_language VARCHAR DEFAULT NULL
    ) RETURNS TABLE (
        episode_id VARCHAR,
        summary TEXT,
        topics JSONB,
        importance_score FLOAT,
        similarity_score FLOAT,
        start_time TIMESTAMPTZ,
        language VARCHAR
    ) AS $func$
    DECLARE
        effective_threshold FLOAT;
        effective_limit INT;
        search_config JSONB;
    BEGIN
        search_config := get_effective_config('search_settings', p_user_id);
        
        effective_threshold := COALESCE(p_similarity_threshold, 
                                       (search_config->>'episode_similarity_threshold')::FLOAT, 
                                       0.4);
        effective_limit := COALESCE(p_limit, 
                                   (search_config->>'max_episode_results')::INT, 
                                   5);
        
        RETURN QUERY
        SELECT 
            me.id,
            me.summary,
            me.topics,
            me.importance_score,
            COALESCE(similarity(me.summary, p_query), 0.0) AS sim_score,
            me.start_time,
            me.language
        FROM memory_episodes me
        WHERE me.user_id = p_user_id 
          AND me.summary IS NOT NULL
          AND (p_language IS NULL OR me.language = p_language)
          AND COALESCE(similarity(me.summary, p_query), 0.0) >= effective_threshold
        ORDER BY sim_score DESC, me.importance_score DESC, me.start_time DESC
        LIMIT effective_limit;
    END;
    $func$ LANGUAGE plpgsql;
    
    -- Новая функция полнотекстового поиска
    CREATE OR REPLACE FUNCTION fulltext_search_facts(
        p_user_id VARCHAR,
        p_query TEXT,
        p_language VARCHAR DEFAULT 'ru',
        p_limit INT DEFAULT 10
    ) RETURNS TABLE (
        fact_id BIGINT,
        fact_key VARCHAR,
        fact_value TEXT,
        confidence FLOAT,
        rank_score FLOAT,
        language VARCHAR
    ) AS $func$
    DECLARE
        ts_config TEXT;
    BEGIN
        -- Определяем конфигурацию полнотекстового поиска по языку
        ts_config := CASE p_language
            WHEN 'ru' THEN 'russian'
            WHEN 'en' THEN 'english'
            ELSE 'simple'
        END;
        
        RETURN QUERY
        EXECUTE format('
            SELECT 
                uf.id,
                uf.fact_key,
                uf.fact_value,
                uf.confidence,
                ts_rank(to_tsvector(%L, uf.fact_value), plainto_tsquery(%L, %L)) AS rank_score,
                uf.language
            FROM user_facts uf
            WHERE uf.user_id = %L
              AND uf.language = %L
              AND uf.is_active = TRUE
              AND to_tsvector(%L, uf.fact_value) @@ plainto_tsquery(%L, %L)
            ORDER BY rank_score DESC, uf.confidence DESC
            LIMIT %s',
            ts_config, ts_config, p_query, p_user_id, p_language, ts_config, ts_config, p_query, p_limit
        );
    END;
    $func$ LANGUAGE plpgsql;
    
    -- Улучшенная функция комбинированного поиска
    CREATE OR REPLACE FUNCTION combined_text_search(
        p_user_id VARCHAR,
        p_query TEXT,
        p_config JSONB DEFAULT NULL,
        p_language VARCHAR DEFAULT NULL
    ) RETURNS JSONB AS $func$
    DECLARE
        search_config JSONB;
        fact_results JSONB;
        episode_results JSONB;
        fulltext_results JSONB;
        final_results JSONB;
        effective_language VARCHAR;
        
        fact_threshold FLOAT;
        episode_threshold FLOAT;
        max_facts INT;
        max_episodes INT;
        use_fulltext BOOLEAN;
    BEGIN
        -- Получаем эффективную конфигурацию
        search_config := COALESCE(p_config, get_effective_config('search_settings', p_user_id));
        
        -- Определяем язык поиска
        effective_language := COALESCE(p_language, 
                                      search_config->>'default_language',
                                      'ru');
        
        -- Извлекаем параметры
        fact_threshold := COALESCE((search_config->>'fact_similarity_threshold')::FLOAT, 0.3);
        episode_threshold := COALESCE((search_config->>'episode_similarity_threshold')::FLOAT, 0.4);
        max_facts := COALESCE((search_config->>'max_fact_results')::INT, 10);
        max_episodes := COALESCE((search_config->>'max_episode_results')::INT, 5);
        use_fulltext := COALESCE((search_config->>'use_fulltext_search')::BOOLEAN, true);
        
        -- Нечеткий поиск фактов
        SELECT jsonb_agg(
            jsonb_build_object(
                'type', 'fact',
                'search_method', 'fuzzy',
                'id', fact_id,
                'key', fact_key,
                'value', fact_value,
                'confidence', confidence,
                'similarity', similarity_score,
                'language', language
            )
        ) INTO fact_results
        FROM fuzzy_search_facts(p_user_id, p_query, fact_threshold, max_facts, effective_language);
        
        -- Полнотекстовый поиск фактов (если включен)
        IF use_fulltext THEN
            SELECT jsonb_agg(
                jsonb_build_object(
                    'type', 'fact',
                    'search_method', 'fulltext',
                    'id', fact_id,
                    'key', fact_key,
                    'value', fact_value,
                    'confidence', confidence,
                    'rank', rank_score,
                    'language', language
                )
            ) INTO fulltext_results
            FROM fulltext_search_facts(p_user_id, p_query, effective_language, max_facts);
        END IF;
        
        -- Поиск эпизодов
        SELECT jsonb_agg(
            jsonb_build_object(
                'type', 'episode',
                'search_method', 'fuzzy',
                'id', episode_id,
                'summary', summary,
                'topics', topics,
                'importance', importance_score,
                'similarity', similarity_score,
                'start_time', extract(epoch from start_time),
                'language', language
            )
        ) INTO episode_results
        FROM fuzzy_search_episodes(p_user_id, p_query, episode_threshold, max_episodes, effective_language);
        
        -- Объединяем результаты
        final_results := jsonb_build_object(
            'query', p_query,
            'user_id', p_user_id,
            'language', effective_language,
            'search_config', search_config,
            'results', jsonb_build_object(
                'fuzzy_facts', COALESCE(fact_results, '[]'::jsonb),
                'fulltext_facts', COALESCE(fulltext_results, '[]'::jsonb),
                'episodes', COALESCE(episode_results, '[]'::jsonb)
            ),
            'search_type', 'combined_text',
            'timestamp', extract(epoch from now())
        );
        
        RETURN final_results;
    END;
    $func$ LANGUAGE plpgsql;
    
    -- 11. Обновляем конфигурацию feature flag с фактическими параметрами
    UPDATE feature_flags 
    SET config = config || jsonb_build_object(
        'status', 'installed',
        'supported_languages', to_jsonb(supported_languages),
        'similarity_thresholds', similarity_thresholds,
        'indexes_created', jsonb_build_object(
            'vector_memories_trgm', NOT indexes_exist.vector_memories_trgm,
            'user_facts_trgm', NOT indexes_exist.user_facts_trgm,
            'episodes_trgm', NOT indexes_exist.episodes_trgm
        ),
        'functions_created', jsonb_build_object(
            'fuzzy_search_facts', NOT functions_exist.fuzzy_search_facts,
            'fuzzy_search_episodes', NOT functions_exist.fuzzy_search_episodes,
            'combined_text_search', NOT functions_exist.combined_text_search,
            'fulltext_search_facts', NOT functions_exist.fulltext_search_facts
        ),
        'installation_completed_at', extract(epoch from now())
    )
    WHERE feature_name = feature_name AND environment = current_env;
    
    -- 12. Финализируем лог и записываем метрики
    migration_log := migration_log || jsonb_build_object(
        'status', 'completed',
        'completed_at', extract(epoch from now()),
        'duration_seconds', extract(epoch from now()) - (migration_log->>'started_at')::FLOAT,
        'languages_configured', supported_languages,
        'indexes_created', (NOT indexes_exist.vector_memories_trgm) OR (NOT indexes_exist.user_facts_trgm) OR (NOT indexes_exist.episodes_trgm),
        'functions_updated', 4
    );
    
    INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
    VALUES ('migration', 'fulltext_support_completed', 1, migration_log, current_env);
    
    RAISE NOTICE '[FULLTEXT_MIGRATION] Fulltext support migration completed successfully';
    
EXCEPTION 
    WHEN OTHERS THEN
        RAISE WARNING '[FULLTEXT_MIGRATION] Migration failed with error: %', SQLERRM;
        
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
        VALUES ('migration', 'fulltext_support_failed', 1, migration_log, current_env);
        
        RAISE NOTICE '[FULLTEXT_MIGRATION] Migration completed with errors, check feature_flags and metrics for details';
END $$;

-- Создаем функцию для отката миграции
CREATE OR REPLACE FUNCTION rollback_fulltext_support(
    p_environment VARCHAR DEFAULT 'production',
    p_force BOOLEAN DEFAULT FALSE
) RETURNS JSONB AS $$
DECLARE
    rollback_log JSONB;
    recent_searches INT;
    supported_languages TEXT[];
    lang TEXT;
    index_name TEXT;
BEGIN
    rollback_log := jsonb_build_object(
        'rollback_started_at', extract(epoch from now()),
        'environment', p_environment,
        'force_mode', p_force
    );
    
    -- Проверяем использование функций в последнее время
    SELECT COUNT(*) INTO recent_searches
    FROM memory_metrics 
    WHERE metric_type = 'search' 
      AND metric_name LIKE '%text_search%'
      AND measured_at > NOW() - INTERVAL '1 day';
    
    IF recent_searches > 0 AND NOT p_force THEN
        rollback_log := rollback_log || jsonb_build_object(
            'status', 'aborted',
            'reason', 'recent_usage_detected',
            'recent_searches', recent_searches
        );
        RETURN rollback_log;
    END IF;
    
    -- Получаем список языков для удаления индексов
    SELECT ARRAY(
        SELECT jsonb_array_elements_text(config->'supported_languages')
        FROM feature_flags 
        WHERE feature_name = 'pg_trgm_support'
    ) INTO supported_languages;
    
    -- Удаляем функции
    DROP FUNCTION IF EXISTS fuzzy_search_facts(VARCHAR, TEXT, FLOAT, INT, VARCHAR);
    DROP FUNCTION IF EXISTS fuzzy_search_episodes(VARCHAR, TEXT, FLOAT, INT, VARCHAR);
    DROP FUNCTION IF EXISTS combined_text_search(VARCHAR, TEXT, JSONB, VARCHAR);
    DROP FUNCTION IF EXISTS fulltext_search_facts(VARCHAR, TEXT, VARCHAR, INT);
    
    rollback_log := rollback_log || jsonb_build_object('functions_dropped', true);
    
    -- Удаляем триграммные индексы
    DROP INDEX IF EXISTS idx_vector_memories_content_trgm;
    DROP INDEX IF EXISTS idx_user_facts_normalized_trgm;
    DROP INDEX IF EXISTS idx_memory_episodes_summary_trgm;
    
    -- Удаляем полнотекстовые индексы по языкам
    IF supported_languages IS NOT NULL THEN
        FOREACH lang IN ARRAY supported_languages LOOP
            index_name := format('idx_user_facts_fulltext_%s', lang);
            EXECUTE format('DROP INDEX IF EXISTS %I', index_name);
        END LOOP;
    END IF;
    
    rollback_log := rollback_log || jsonb_build_object('indexes_dropped', true);
    
    -- Отключаем feature flag
    UPDATE feature_flags 
    SET enabled = false,
        config = config || jsonb_build_object(
            'status', 'rolled_back',
            'rollback_completed_at', extract(epoch from now())
        )
    WHERE feature_name = 'pg_trgm_support' AND environment = p_environment;
    
    rollback_log := rollback_log || jsonb_build_object(
        'status', 'completed',
        'completed_at', extract(epoch from now())
    );
    
    -- Записываем метрику отката
    INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context, environment)
    VALUES ('migration', 'fulltext_support_rollback', 1, rollback_log, p_environment);
    
    RETURN rollback_log;
END;
$$ LANGUAGE plpgsql;

-- Комментарии
COMMENT ON FUNCTION rollback_fulltext_support IS 'Откат миграции fulltext support с проверками безопасности';
COMMENT ON FUNCTION fuzzy_search_facts IS 'Нечеткий поиск фактов с конфигурируемыми параметрами';
COMMENT ON FUNCTION fuzzy_search_episodes IS 'Нечеткий поиск эпизодов с конфигурируемыми параметрами';
COMMENT ON FUNCTION fulltext_search_facts IS 'Полнотекстовый поиск фактов с поддержкой языков';
COMMENT ON FUNCTION combined_text_search IS 'Комбинированный текстовый поиск с множественными методами';
