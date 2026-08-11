CREATE TABLE model_usage_log (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(30),
    endpoint VARCHAR(50),
    response_time_ms INT,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT now()
);