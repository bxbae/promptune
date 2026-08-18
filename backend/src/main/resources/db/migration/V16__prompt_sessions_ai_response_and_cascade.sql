-- AI 생성 응답 원문 저장 컬럼 (지금까지 저장 안 되고 있던 것)
ALTER TABLE prompt_sessions ADD COLUMN ai_response_text TEXT;

-- 채팅 삭제 시 메시지도 같이 지워지도록 CASCADE로 변경
-- ⚠️ 제약조건 이름은 위에서 확인한 실제 이름으로 바꿔서 쓸 것 (아래는 기본값 가정)
ALTER TABLE prompt_sessions DROP CONSTRAINT prompt_sessions_chat_session_id_fkey;
ALTER TABLE prompt_sessions
    ADD CONSTRAINT prompt_sessions_chat_session_id_fkey
    FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE;
