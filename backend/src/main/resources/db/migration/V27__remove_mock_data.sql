-- Remove legacy runtime mock/test data.
-- Keep V2/V21 unchanged because they may already be recorded by Flyway.

CREATE TEMP TABLE mock_user_ids (
    id BIGINT PRIMARY KEY
) ON COMMIT DROP;

INSERT INTO mock_user_ids (id)
SELECT id
FROM users
WHERE email IN (
    'byeonghwan@promptune.dev',
    'test@promptune.dev'
);

-- Remove dependent data first to satisfy foreign-key constraints.
DELETE FROM behavior_logs
WHERE user_id IN (SELECT id FROM mock_user_ids);

DELETE FROM response_edits
WHERE user_id IN (SELECT id FROM mock_user_ids);

DELETE FROM consent_records
WHERE user_id IN (SELECT id FROM mock_user_ids);

DELETE FROM personalization_score
WHERE user_id IN (SELECT id FROM mock_user_ids);

DELETE FROM microsoft_oauth_states
WHERE user_id IN (SELECT id FROM mock_user_ids);

DELETE FROM microsoft_connections
WHERE user_id IN (SELECT id FROM mock_user_ids);

DELETE FROM documents
WHERE owner_user_id IN (SELECT id FROM mock_user_ids);

DELETE FROM receiver_profile
WHERE user_id IN (SELECT id FROM mock_user_ids);

DELETE FROM prompt_sessions
WHERE user_id IN (SELECT id FROM mock_user_ids);

DELETE FROM chat_sessions
WHERE user_id IN (SELECT id FROM mock_user_ids);

DELETE FROM user_preferences
WHERE user_id IN (SELECT id FROM mock_user_ids);

DELETE FROM users
WHERE id IN (SELECT id FROM mock_user_ids);

-- Legacy V2 RAG samples had no real owner and used zero-vector embeddings.
DELETE FROM documents
WHERE owner_user_id IS NULL
  AND title IN (
      '?? ?? ??',
      '?? ?? ??',
      '??? ?? ??'
  );
