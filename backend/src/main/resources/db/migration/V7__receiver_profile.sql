CREATE TABLE receiver_profile (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    receiver_name VARCHAR(100) NOT NULL,
    relationship VARCHAR(50),
    preferred_tone VARCHAR(50),
    avg_length INT,
    apply_rate NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);