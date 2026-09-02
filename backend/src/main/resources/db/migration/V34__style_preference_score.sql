CREATE TABLE style_preference_score (
    user_id BIGINT PRIMARY KEY,
    sample_count INT NOT NULL DEFAULT 0,
    avg_length_ratio DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    avg_structure_delta DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
