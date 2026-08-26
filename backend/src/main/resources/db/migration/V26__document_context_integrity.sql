-- Document context integrity and indexing state.
--
-- 1) A document upload and AI-readiness are separate states.
-- 2) A prompt session can reference many documents and the same document can
--    be referenced by many prompt sessions, so attachment memory is N:M.

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS index_status VARCHAR(20) NOT NULL DEFAULT 'UPLOADED';

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS index_error TEXT;

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS indexed_at TIMESTAMP;

-- Existing documents already have document_chunks from the previous indexer.
-- Backfill their readiness from the actual stored data rather than pretending
-- every historical document is merely UPLOADED.
UPDATE documents d
SET index_status = CASE
        WHEN EXISTS (
            SELECT 1
            FROM document_chunks dc
            WHERE dc.document_id = d.id
              AND dc.embedding IS NOT NULL
        ) THEN 'READY'
        WHEN EXISTS (
            SELECT 1
            FROM document_chunks dc
            WHERE dc.document_id = d.id
        ) THEN 'TEXT_READY'
        ELSE 'UPLOADED'
    END,
    indexed_at = CASE
        WHEN EXISTS (
            SELECT 1
            FROM document_chunks dc
            WHERE dc.document_id = d.id
        ) THEN COALESCE(d.indexed_at, NOW())
        ELSE d.indexed_at
    END;

ALTER TABLE documents
    DROP CONSTRAINT IF EXISTS ck_documents_index_status;

ALTER TABLE documents
    ADD CONSTRAINT ck_documents_index_status
    CHECK (index_status IN ('UPLOADED', 'INDEXING', 'TEXT_READY', 'READY', 'FAILED'));

CREATE TABLE IF NOT EXISTS prompt_session_documents (
    id BIGSERIAL PRIMARY KEY,
    prompt_session_id BIGINT NOT NULL
        REFERENCES prompt_sessions(id) ON DELETE CASCADE,
    document_id BIGINT NOT NULL
        REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_prompt_session_document
        UNIQUE (prompt_session_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_psd_prompt_session_id
    ON prompt_session_documents(prompt_session_id);

CREATE INDEX IF NOT EXISTS idx_psd_document_id
    ON prompt_session_documents(document_id);

-- Preserve all attachment relations recorded by V25 before the N:M table
-- existed. Keep documents.prompt_session_id for backward compatibility during
-- this migration phase; application reads/writes use the join table now.
INSERT INTO prompt_session_documents(prompt_session_id, document_id)
SELECT d.prompt_session_id, d.id
FROM documents d
WHERE d.prompt_session_id IS NOT NULL
ON CONFLICT (prompt_session_id, document_id) DO NOTHING;
