ALTER TABLE chat_sessions ADD COLUMN user_sequence INT;

-- 기존 채팅들도 사용자별로 순번을 소급 부여 (생성 순서 기준)
WITH numbered AS (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at ASC) AS seq
    FROM chat_sessions
)
UPDATE chat_sessions cs
SET user_sequence = numbered.seq
FROM numbered
WHERE cs.id = numbered.id;

ALTER TABLE chat_sessions ALTER COLUMN user_sequence SET NOT NULL;
