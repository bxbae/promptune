-- MS 조직도에서 자동 동기화된 프로필인지 구분. true면 department는 MS가 실제 소스라
-- 히스토리 화면에서 사용자가 직접 수정하지 못하게 막는다 (이름/직함도 MS 값을 그대로 씀).
ALTER TABLE receiver_profile ADD COLUMN ms_synced BOOLEAN NOT NULL DEFAULT false;
