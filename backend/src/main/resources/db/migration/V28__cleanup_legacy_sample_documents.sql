-- Correct legacy sample-document cleanup.
-- V27 is already applied and must remain unchanged for Flyway checksum safety.

DELETE FROM documents
WHERE owner_user_id IS NULL
  AND title IN (
      '휴가 규정 안내',
      '경비 처리 지침',
      '보고서 작성 표준'
  );
