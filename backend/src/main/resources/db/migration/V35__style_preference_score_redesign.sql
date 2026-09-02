DROP TABLE IF EXISTS style_preference_score;

CREATE TABLE style_preference_score (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL,
    field VARCHAR(20) NOT NULL,   -- 'format' | 'structure' | 'detail_level'
    value VARCHAR(50) NOT NULL,   -- 'table' | 'concise' 등
    use_count INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (user_id, field, value)
);
