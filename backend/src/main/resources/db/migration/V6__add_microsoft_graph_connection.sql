-- Microsoft Graph 외부 업무 계정 연결
-- PostgreSQL 기준

CREATE TABLE microsoft_connections (
    user_id BIGINT PRIMARY KEY,
    microsoft_user_id VARCHAR(255),
    microsoft_email VARCHAR(255),
    display_name VARCHAR(255),
    token_cache_encrypted TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_microsoft_connections_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE microsoft_oauth_states (
    state VARCHAR(36) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_microsoft_oauth_states_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_es_expires_at
    ON microsoft_oauth_states(expires_at);

CREATE INDEX idx_microsoft_connections_microsoft_user
    ON microsoft_connections(microsoft_user_id);
