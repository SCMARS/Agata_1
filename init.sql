-- Agatha Database Schema
-- PostgreSQL initialization script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension для VECTOR типа
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- User profile data
    name VARCHAR(255),
    preferences JSONB DEFAULT '{}',
    communication_style JSONB DEFAULT '{}',
    interests TEXT[],
    
    -- Conversation tracking
    total_messages INTEGER DEFAULT 0,
    days_since_start INTEGER DEFAULT 1,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Behavioral adaptation
    current_strategy VARCHAR(50) DEFAULT 'caring',
    question_count INTEGER DEFAULT 0,
    
    -- Metadata
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'ru'
);

-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Conversation metadata
    day_number INTEGER NOT NULL,
    session_id VARCHAR(255),
    context JSONB DEFAULT '{}',
    
    -- State tracking
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Message content
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    
    -- Response metadata (for assistant messages)
    parts TEXT[] DEFAULT '{}',
    delays_ms INTEGER[] DEFAULT '{}',
    has_question BOOLEAN DEFAULT false,
    
    -- Processing metadata
    prompt_strategy VARCHAR(50),
    processing_time_ms INTEGER,
    
    -- Vector embeddings (для semantic search) - ТЕПЕРЬ С РАСШИРЕНИЕМ
    embedding vector(1536) -- OpenAI embeddings dimension
);

-- Memory summaries table
CREATE TABLE memory_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Summary content
    summary_type VARCHAR(50) NOT NULL, -- 'daily', 'weekly', 'topic'
    content TEXT NOT NULL,
    
    -- Reference data
    messages_count INTEGER DEFAULT 0,
    date_range DATERANGE,
    topics TEXT[],
    
    -- Vector embedding for semantic search - ИСПРАВЛЕНО
    embedding vector(1536)
);

-- User insights table (for behavioral adaptation)
CREATE TABLE user_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Insight data
    insight_type VARCHAR(50) NOT NULL, -- 'communication_pattern', 'interest', 'emotional_state'
    insight_data JSONB NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    
    -- Temporal data
    observed_date DATE DEFAULT CURRENT_DATE,
    is_active BOOLEAN DEFAULT true
);

-- Vector Memory table for semantic search
CREATE TABLE IF NOT EXISTS vector_memories (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    role VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    day_number INTEGER NOT NULL,
    importance_score FLOAT NOT NULL,
    topics JSONB,
    emotions JSONB,
    metadata JSONB,
    embedding VECTOR(1536), -- OpenAI text-embedding-ada-002 dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_users_last_activity ON users(last_activity);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_day_number ON conversations(day_number);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_role ON messages(role);

-- VECTOR INDEXES для быстрого семантического поиска
CREATE INDEX idx_messages_embedding ON messages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_memory_summaries_embedding ON memory_summaries USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_memory_summaries_user_id ON memory_summaries(user_id);
CREATE INDEX idx_memory_summaries_type ON memory_summaries(summary_type);
CREATE INDEX idx_memory_summaries_date_range ON memory_summaries USING GIST(date_range);

CREATE INDEX idx_user_insights_user_id ON user_insights(user_id);
CREATE INDEX idx_user_insights_type ON user_insights(insight_type);
CREATE INDEX idx_user_insights_date ON user_insights(observed_date);

-- Indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_vector_memories_user_id ON vector_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_vector_memories_timestamp ON vector_memories(timestamp);
CREATE INDEX IF NOT EXISTS idx_vector_memories_importance ON vector_memories(importance_score);

-- Vector index for semantic search using cosine similarity
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Functions for automatic updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memory_summaries_updated_at BEFORE UPDATE ON memory_summaries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Sample data (optional for development)
INSERT INTO users (user_id, name) VALUES 
('demo_user', 'Demo User'),
('test_user', 'Test User'); 