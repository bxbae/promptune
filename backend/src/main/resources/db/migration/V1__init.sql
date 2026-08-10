-- PrompTune 초기 스키마 (PostgreSQL + pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- 사용자
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    department VARCHAR(100),
    position VARCHAR(100),
    created_at TIMESTAMP DEFAULT now()
);

-- 선호 설정 (0-2번 온보딩)
CREATE TABLE user_preferences (
    user_id BIGINT PRIMARY KEY REFERENCES users(id),
    speed VARCHAR(20),         -- 빠르게 / 정확하게
    detail VARCHAR(20),        -- 간결하게 / 자세하게
    preserve VARCHAR(20)       -- 원문유지 / 적극보완
);

-- 프롬프트 세션
CREATE TABLE prompt_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    original_text TEXT NOT NULL,
    final_text TEXT,
    task_type VARCHAR(30),
    created_at TIMESTAMP DEFAULT now()
);

-- 행동 로그 (16번 개인화)
CREATE TABLE behavior_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    element VARCHAR(20),       -- 어떤 요소 추천에 대해
    action VARCHAR(20),        -- tab(적용) / esc(무시) / alt(대안선택)
    created_at TIMESTAMP DEFAULT now()
);

-- 내부 문서 임베딩 (13번 RAG, pgvector)
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255),
    content TEXT,
    embedding vector(1024)     -- BGE-M3 차원
);
