CREATE TABLE personalization_score (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    element VARCHAR(20) NOT NULL,
    accept_count INT DEFAULT 0,
    dismiss_count INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE(user_id, element)
);

