CREATE TABLE consent_records (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    consent_type VARCHAR(30),
    granted_at TIMESTAMP DEFAULT now(),
    revoked_at TIMESTAMP
);