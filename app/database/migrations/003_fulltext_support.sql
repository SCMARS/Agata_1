-- Условная миграция: Поддержка полнотекстового поиска
-- Версия: 1.0  
-- Выполняется только если включен feature_flag 'pg_trgm_support'

DO $$
DECLARE
    trgm_enabled BOOLEAN;
    trgm_config JSONB;
    supported_languages TEXT[];
    lang TEXT;
BEGIN
    -- Проверяем флаг функции
    SELECT enabled, config INTO trgm_enabled, trgm_config
    FROM feature_flags 
    WHERE feature_name = 'pg_trgm_support' 
      AND environment = COALESCE(current_setting('app.environment', true), 'production');
    
    IF NOT FOUND OR NOT trgm_enabled THEN
        RAISE NOTICE 'Skipping fulltext support migration - feature disabled';
        RETURN;
    END IF;
    
    RAISE NOTICE 'Installing fulltext search support';
    
    -- Создаем расширение pg_trgm если доступно
    BEGIN
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
        RAISE NOTICE 'pg_trgm extension installed successfully';
    EXCEPTION 
        WHEN OTHERS THEN
            RAISE WARNING 'Failed to install pg_trgm extension: %', SQLERRM;
            -- Обновляем флаг как неактивный
            UPDATE feature_flags 
            SET enabled = false, 
                config = config || '{"error": "extension_unavailable"}'::jsonb
            WHERE feature_name = 'pg_trgm_support';
            RETURN;
    END;
    
    -- Получаем поддерживаемые языки из конфигурации multilingual_support
    SELECT config->'supported' INTO supported_languages
    FROM feature_flags 
    WHERE feature_name = 'multilingual_support' AND enabled = true;
    
    supported_languages := COALESCE(supported_languages, '["ru", "en"]'::jsonb);
    
    -- Создаем триграммные индексы для векторных воспоминаний (если таблица существует)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vector_memories') THEN
        CREATE INDEX IF NOT EXISTS idx_vector_memories_content_trgm 
        ON vector_memories USING gin (content gin_trgm_ops);
        
        RAISE NOTICE 'Created trigram index for vector_memories.content';
    END IF;
    
    -- Создаем дополнительные индексы для фактов пользователей
    CREATE INDEX IF NOT EXISTS idx_user_facts_normalized_trgm 
    ON user_facts USING gin (normalized_value gin_trgm_ops) 
    WHERE is_active = TRUE;
    
    -- Создаем индексы для эпизодов
    CREATE INDEX IF NOT EXISTS idx_memory_episodes_summary_trgm 
    ON memory_episodes USING gin (summary gin_trgm_ops) 
    WHERE summary IS NOT NULL;
    
    -- Функция для нечеткого поиска
    CREATE OR REPLACE FUNCTION fuzzy_search_facts(
        p_user_id VARCHAR,
        p_query TEXT,
        p_similarity_threshold FLOAT DEFAULT 0.3,
        p_limit INT DEFAULT 10
    ) RETURNS TABLE (
        fact_id BIGINT,
        fact_key VARCHAR,
        fact_value TEXT,
        confidence FLOAT,
        similarity_score FLOAT
    ) AS $func$
    BEGIN
        RETURN QUERY
        SELECT 
            uf.id,
            uf.fact_key,
            uf.fact_value,
            uf.confidence,
            similarity(uf.normalized_value, p_query) AS sim_score
        FROM user_facts uf
        WHERE uf.user_id = p_user_id 
          AND uf.is_active = TRUE
          AND similarity(uf.normalized_value, p_query) >= p_similarity_threshold
        ORDER BY sim_score DESC, uf.confidence DESC
        LIMIT p_limit;
    END;
    $func$ LANGUAGE plpgsql;
    
    -- Функция для поиска по эпизодам
    CREATE OR REPLACE FUNCTION fuzzy_search_episodes(
        p_user_id VARCHAR,
        p_query TEXT,
        p_similarity_threshold FLOAT DEFAULT 0.3,
        p_limit INT DEFAULT 5
    ) RETURNS TABLE (
        episode_id VARCHAR,
        summary TEXT,
        topics JSONB,
        importance_score FLOAT,
        similarity_score FLOAT
    ) AS $func$
    BEGIN
        RETURN QUERY
        SELECT 
            me.id,
            me.summary,
            me.topics,
            me.importance_score,
            similarity(me.summary, p_query) AS sim_score
        FROM memory_episodes me
        WHERE me.user_id = p_user_id 
          AND me.summary IS NOT NULL
          AND similarity(me.summary, p_query) >= p_similarity_threshold
        ORDER BY sim_score DESC, me.importance_score DESC
        LIMIT p_limit;
    END;
    $func$ LANGUAGE plpgsql;
    
    -- Функция для комбинированного поиска
    CREATE OR REPLACE FUNCTION combined_text_search(
        p_user_id VARCHAR,
        p_query TEXT,
        p_config JSONB DEFAULT NULL
    ) RETURNS JSONB AS $func$
    DECLARE
        search_config JSONB;
        fact_results JSONB;
        episode_results JSONB;
        final_results JSONB;
        fact_threshold FLOAT;
        episode_threshold FLOAT;
        max_facts INT;
        max_episodes INT;
    BEGIN
        -- Получаем конфигурацию поиска
        search_config := COALESCE(p_config, get_effective_config('search_settings', p_user_id));
        
        fact_threshold := COALESCE((search_config->>'fact_similarity_threshold')::FLOAT, 0.3);
        episode_threshold := COALESCE((search_config->>'episode_similarity_threshold')::FLOAT, 0.3);
        max_facts := COALESCE((search_config->>'max_fact_results')::INT, 10);
        max_episodes := COALESCE((search_config->>'max_episode_results')::INT, 5);
        
        -- Ищем факты
        SELECT jsonb_agg(
            jsonb_build_object(
                'type', 'fact',
                'id', fact_id,
                'key', fact_key,
                'value', fact_value,
                'confidence', confidence,
                'similarity', similarity_score
            )
        ) INTO fact_results
        FROM fuzzy_search_facts(p_user_id, p_query, fact_threshold, max_facts);
        
        -- Ищем эпизоды
        SELECT jsonb_agg(
            jsonb_build_object(
                'type', 'episode',
                'id', episode_id,
                'summary', summary,
                'topics', topics,
                'importance', importance_score,
                'similarity', similarity_score
            )
        ) INTO episode_results
        FROM fuzzy_search_episodes(p_user_id, p_query, episode_threshold, max_episodes);
        
        -- Объединяем результаты
        final_results := jsonb_build_object(
            'query', p_query,
            'user_id', p_user_id,
            'facts', COALESCE(fact_results, '[]'::jsonb),
            'episodes', COALESCE(episode_results, '[]'::jsonb),
            'search_type', 'fuzzy_text',
            'timestamp', extract(epoch from now())
        );
        
        RETURN final_results;
    END;
    $func$ LANGUAGE plpgsql;
    
    -- Обновляем конфигурацию флага
    UPDATE feature_flags 
    SET config = config || '{"status": "installed", "indexes_created": true}'::jsonb
    WHERE feature_name = 'pg_trgm_support';
    
    RAISE NOTICE 'Fulltext search support migration completed successfully';
    
EXCEPTION 
    WHEN OTHERS THEN
        RAISE WARNING 'Fulltext support migration failed: %', SQLERRM;
        -- Записываем ошибку в конфигурацию
        UPDATE feature_flags 
        SET enabled = false,
            config = config || jsonb_build_object('error', SQLERRM, 'status', 'failed')
        WHERE feature_name = 'pg_trgm_support';
END $$;
