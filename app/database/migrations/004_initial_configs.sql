-- Загрузка начальных конфигураций (заменяет YAML файлы)
-- Версия: 1.0
-- Выполняется после создания основных таблиц

-- Вставка базовых конфигураций
INSERT INTO config_versions (config_key, version, payload, active, description, environment, feature_flags) VALUES

-- Пороги и параметры памяти
('memory_thresholds', '1.0', '{
  "semantic_similarity": 0.5,
  "text_fuzzy_min": 0.25,
  "fact_accept_immediate": 0.95,
  "low_confidence": 0.3,
  "fact_confidence_min": 0.7,
  "importance_threshold": 0.6,
  "episode_min_messages": 5,
  "summary_trigger_count": 50,
  "auto_calibration_enabled": false,
  "adaptive_thresholds": true
}', true, 'Конфигурируемые пороги для системы памяти', 'production', '{}'),

-- Веса для поиска
('search_weights', '1.0', '{
  "deterministic_facts": 1.0,
  "fuzzy_text": 0.7,
  "semantic_vector": 0.6,
  "episodic": 0.4,
  "recency_bonus": 0.2,
  "confidence_weight": 0.8,
  "occurrence_weight": 0.3
}', true, 'Веса для комбинирования результатов поиска', 'production', '{}'),

-- Настройки LLM
('llm_settings', '1.0', '{
  "enabled": true,
  "primary_model": "gpt-4o-mini",
  "fallback_model": "gpt-3.5-turbo",
  "temperature": 0.1,
  "max_tokens": 500,
  "timeout_seconds": 30,
  "retry_attempts": 3,
  "extraction_enabled": true,
  "summarization_enabled": true,
  "intent_detection_enabled": true,
  "batch_processing": false
}', true, 'Настройки LLM для всех операций', 'production', '{}'),

-- Настройки векторной БД
('vector_db_settings', '1.0', '{
  "provider": "chroma",
  "embedding_model": "text-embedding-3-small",
  "embedding_dimension": 1536,
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "similarity_threshold": 0.6,
  "max_results": 5,
  "distance_metric": "cosine",
  "index_parameters": {
    "ivfflat_lists": 100,
    "hnsw_m": 16,
    "hnsw_ef_construction": 200
  }
}', true, 'Настройки векторной БД', 'production', '{}'),

-- Основные настройки памяти
('memory_settings', '1.0', '{
  "short_term": {
    "max_messages": 10,
    "ttl_seconds": 3600,
    "buffer_type": "langchain",
    "compression_enabled": false
  },
  "episodic": {
    "auto_save": true,
    "timeout_minutes": 30,
    "min_importance": 0.3,
    "summarization_trigger": "auto"
  },
  "long_term": {
    "fact_store_enabled": true,
    "vector_store_enabled": true,
    "max_facts_per_key": 5,
    "fact_merge_enabled": true,
    "deduplication_threshold": 0.9
  },
  "multilingual": {
    "enabled": true,
    "default_language": "ru",
    "auto_detect": true,
    "translation_enabled": false
  }
}', true, 'Основные настройки всех уровней памяти', 'production', '{}'),

-- Настройки извлечения информации
('extraction_settings', '1.0', '{
  "llm_primary": true,
  "regex_fallback": true,
  "confidence_boosters": {
    "named_entities": 0.1,
    "pattern_matches": 0.05,
    "context_confirmation": 0.15
  },
  "normalization": {
    "enabled": true,
    "case_normalization": true,
    "transliteration": false,
    "stopwords_removal": true
  },
  "validation": {
    "enabled": true,
    "cross_reference": true,
    "anomaly_detection": false
  }
}', true, 'Настройки извлечения фактов', 'production', '{}'),

-- Настройки поиска
('search_settings', '1.0', '{
  "pipeline_order": ["deterministic", "fuzzy", "semantic", "episodic"],
  "fact_similarity_threshold": 0.3,
  "episode_similarity_threshold": 0.4,
  "max_fact_results": 10,
  "max_episode_results": 5,
  "result_deduplication": true,
  "result_ranking": {
    "importance_weight": 0.4,
    "recency_weight": 0.3,
    "confidence_weight": 0.3
  },
  "timeout_ms": 5000
}', true, 'Настройки поиска по всем уровням', 'production', '{}'),

-- Настройки расчета важности
('importance_calculation', '1.0', '{
  "key_weights": {
    "name": 1.0,
    "age": 0.9, 
    "profession": 0.9,
    "location": 0.8,
    "friends": 0.8,
    "family": 0.85,
    "company": 0.7,
    "hobbies": 0.6,
    "preferences": 0.4,
    "temporary_info": 0.2
  },
  "thresholds": {
    "max_occurrence_bonus": 0.3,
    "occurrence_multiplier": 0.1,
    "confidence_multiplier": 1.0
  },
  "recency_bonuses": {
    "week": 0.2,
    "month": 0.1,
    "quarter": 0.05,
    "default": 0.0
  },
  "context_bonuses": {
    "explicit_statement": 0.1,
    "repeated_mention": 0.05,
    "high_confidence_extraction": 0.15
  }
}', true, 'Параметры расчета важности фактов', 'production', '{}'),

-- Промпты для LLM
('llm_prompts', '1.0', '{
  "fact_extraction": {
    "system_prompt": "Ты - экстрактор фактов. Анализируй сообщения пользователя и извлекай персональную информацию. Возвращай только валидный JSON в формате: {\"facts\": [{\"key\": \"canonical_key\", \"value\": \"normalized_value\", \"confidence\": 0.0-1.0}]}",
    "canonical_keys": ["name", "age", "profession", "company", "location", "friends", "family", "hobbies", "education", "goals", "preferences"],
    "examples": [
      {
        "input": "Меня зовут Анна, работаю врачом в больнице",
        "output": "{\"facts\": [{\"key\": \"name\", \"value\": \"Анна\", \"confidence\": 0.95}, {\"key\": \"profession\", \"value\": \"врач\", \"confidence\": 0.9}]}"
      }
    ]
  },
  "summarization": {
    "episode_prompt": "Создай краткое резюме диалога между пользователем и ассистентом. Выдели основные темы, важные факты и эмоциональную окраску. Максимум 200 слов на русском языке.",
    "session_prompt": "Создай краткое резюме этой части диалога. Выдели ключевые темы, важную информацию о пользователе и основные вопросы. Максимум 150 слов на русском языке."
  },
  "intent_detection": {
    "system_prompt": "Определи намерение пользователя из сообщения. Верни JSON с intent и confidence: {\"intent\": \"asking_name|asking_friends|asking_work|general_conversation\", \"confidence\": 0.0-1.0}"
  }
}', true, 'Промпты для LLM операций', 'production', '{}');

-- Вставка конфигураций для разработки (более агрессивные настройки)
INSERT INTO config_versions (config_key, version, payload, active, description, environment) VALUES
('memory_thresholds', '1.0-dev', '{
  "semantic_similarity": 0.3,
  "text_fuzzy_min": 0.2,
  "fact_accept_immediate": 0.8,
  "low_confidence": 0.2,
  "fact_confidence_min": 0.5,
  "importance_threshold": 0.4,
  "episode_min_messages": 3,
  "summary_trigger_count": 20
}', true, 'Пороги для разработки (более мягкие)', 'development'),

('llm_settings', '1.0-dev', '{
  "enabled": true,
  "primary_model": "gpt-3.5-turbo",
  "temperature": 0.2,
  "max_tokens": 300,
  "timeout_seconds": 15,
  "retry_attempts": 2,
  "extraction_enabled": true,
  "summarization_enabled": true,
  "batch_processing": true
}', true, 'LLM настройки для разработки', 'development');

-- Настройка feature flags (актуализация)
UPDATE feature_flags SET 
  config = config || jsonb_build_object(
    'default_language', 'ru',
    'supported_languages', '["ru", "en"]'::jsonb,
    'fallback_patterns', true
  )
WHERE feature_name = 'multilingual_support';

UPDATE feature_flags SET 
  config = config || jsonb_build_object(
    'model', 'gpt-4o-mini',
    'temperature', 0.1,
    'max_tokens', 500,
    'batch_size', 10,
    'parallel_processing', false
  )
WHERE feature_name = 'llm_extraction';

UPDATE feature_flags SET 
  config = config || jsonb_build_object(
    'trigger_count', 50,
    'max_summary_length', 200,
    'include_emotions', true,
    'include_topics', true
  )
WHERE feature_name = 'auto_summarization';

-- Функция для создания пользовательских A/B конфигураций
CREATE OR REPLACE FUNCTION create_ab_test_config(
    p_base_config_key VARCHAR,
    p_test_name VARCHAR,
    p_user_ids TEXT[],
    p_overrides JSONB,
    p_duration_days INT DEFAULT 30
) RETURNS BOOLEAN AS $$
DECLARE
    user_id TEXT;
    expires_time TIMESTAMPTZ;
BEGIN
    expires_time := NOW() + INTERVAL '1 day' * p_duration_days;
    
    -- Создаем пользовательские конфигурации для A/B теста
    FOREACH user_id IN ARRAY p_user_ids LOOP
        INSERT INTO user_configs (user_id, config_key, config_value, expires_at, priority)
        VALUES (
            user_id, 
            p_base_config_key,
            p_overrides || jsonb_build_object('ab_test', p_test_name),
            expires_time,
            50  -- более высокий приоритет для A/B тестов
        )
        ON CONFLICT (user_id, config_key) 
        DO UPDATE SET 
            config_value = EXCLUDED.config_value,
            expires_at = EXCLUDED.expires_at,
            priority = EXCLUDED.priority,
            updated_at = NOW();
    END LOOP;
    
    -- Логируем создание A/B теста
    INSERT INTO memory_metrics (metric_type, metric_name, metric_value, context)
    VALUES (
        'ab_test', 
        'config_created', 
        array_length(p_user_ids, 1),
        jsonb_build_object(
            'test_name', p_test_name,
            'config_key', p_base_config_key,
            'duration_days', p_duration_days,
            'overrides', p_overrides
        )
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Пример создания A/B теста для порогов памяти
SELECT create_ab_test_config(
    'memory_thresholds',
    'high_sensitivity_test',
    ARRAY['test_user_1', 'test_user_2'],
    '{"fact_confidence_min": 0.5, "importance_threshold": 0.4}'::jsonb,
    14
);

-- Функция для очистки устаревших пользовательских конфигов
CREATE OR REPLACE FUNCTION cleanup_expired_user_configs() RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM user_configs 
    WHERE expires_at IS NOT NULL AND expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Логируем очистку
    INSERT INTO memory_metrics (metric_type, metric_name, metric_value)
    VALUES ('maintenance', 'expired_configs_cleaned', deleted_count);
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Представление для мониторинга A/B тестов
CREATE VIEW ab_test_status AS
SELECT 
    (config_value->>'ab_test') as test_name,
    config_key,
    COUNT(*) as user_count,
    MIN(created_at) as started_at,
    MAX(expires_at) as expires_at,
    CASE 
        WHEN MAX(expires_at) > NOW() THEN 'active'
        ELSE 'expired'
    END as status
FROM user_configs 
WHERE config_value ? 'ab_test'
GROUP BY (config_value->>'ab_test'), config_key;

-- Комментарии
COMMENT ON FUNCTION create_ab_test_config IS 'Создание A/B тестов для конфигураций памяти';
COMMENT ON FUNCTION cleanup_expired_user_configs IS 'Очистка устаревших пользовательских конфигураций';
COMMENT ON VIEW ab_test_status IS 'Мониторинг статуса A/B тестов конфигураций';

-- Сообщение о завершении
SELECT 'Initial configurations loaded successfully' AS status,
       COUNT(*) as config_count 
FROM config_versions WHERE active = true;
