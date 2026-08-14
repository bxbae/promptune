ALTER TABLE prompt_sessions ADD COLUMN IF NOT EXISTS satisfaction VARCHAR(10);

CREATE TABLE IF NOT EXISTS response_edits (
    id BIGSERIAL PRIMARY KEY,
    prompt_session_id BIGINT REFERENCES prompt_sessions(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id),
    generated_result TEXT NOT NULL,
    user_final_result TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);
