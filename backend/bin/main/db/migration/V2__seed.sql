-- PrompTune 목업 시드 데이터
-- Flyway V2: V1(스키마) 다음에 자동 실행됨. 순서 보장됨.

-- 샘플 사용자 (프론트가 userId=1로 호출)
INSERT INTO users (id, email, department, position) VALUES
  (1, 'byeonghwan@promptune.dev', '마케팅팀', '사원')
ON CONFLICT (id) DO NOTHING;

-- 선호 설정 (0-2번 온보딩 완료 상태)
INSERT INTO user_preferences (user_id, speed, detail, preserve) VALUES
  (1, '정확하게', '자세하게', '적극보완')
ON CONFLICT (user_id) DO NOTHING;

-- 내부 문서 샘플 (13번 RAG용). embedding은 목업이라 0벡터로 채움.
-- 실제로는 승연이 BGE-M3로 임베딩 생성.
INSERT INTO documents (title, content, embedding) VALUES
  ('휴가 규정 안내', '연차는 입사 1년 후 15일 부여되며, 반차는 오전/오후로 나뉜다.', array_fill(0, ARRAY[1024])::vector),
  ('경비 처리 지침', '경비 신청은 지출 후 7일 이내에 영수증과 함께 제출한다.', array_fill(0, ARRAY[1024])::vector),
  ('보고서 작성 표준', '사내 보고서는 요약-본문-결론 순으로 작성하며 3장을 넘기지 않는다.', array_fill(0, ARRAY[1024])::vector);

-- 시퀀스 보정 (수동 id 삽입 후)
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
