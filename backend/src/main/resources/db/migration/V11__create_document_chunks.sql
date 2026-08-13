CREATE TABLE IF NOT EXISTS document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT DEFAULT 0,
    content TEXT,
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT now()
);

INSERT INTO document_chunks (document_id, chunk_index, content, embedding)
SELECT id, 0, content, embedding
FROM documents
WHERE content IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM document_chunks WHERE document_chunks.document_id = documents.id);

-- 문서당 같은 조각순서 번호가 중복 안 생기게 방지
ALTER TABLE document_chunks ADD CONSTRAINT uq_document_chunk_version UNIQUE (document_id, chunk_index);
