ALTER TABLE documents
  ADD COLUMN prompt_session_id BIGINT NULL
  REFERENCES prompt_sessions(id) ON DELETE SET NULL;

CREATE INDEX idx_documents_prompt_session_id ON documents(prompt_session_id);
