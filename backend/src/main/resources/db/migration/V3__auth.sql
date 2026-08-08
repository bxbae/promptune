-- 인증 관련 컬럼 추가 (로컬 로그인 + 향후 소셜 대비)

ALTER TABLE users
    ADD COLUMN password_hash VARCHAR(255),         -- BCrypt 해시 (로컬 로그인용)
    ADD COLUMN name VARCHAR(100),                  -- 표시 이름
    ADD COLUMN provider VARCHAR(20) DEFAULT 'local', -- local / google / kakao / naver
    ADD COLUMN provider_id VARCHAR(255);           -- 소셜 로그인 시 제공자의 사용자 ID

-- 소셜 로그인은 이메일이 없을 수도 있어 이메일 unique 제약을 완화하고
-- (provider, provider_id) 조합으로 고유성 보장
CREATE UNIQUE INDEX idx_provider_user ON users(provider, provider_id)
    WHERE provider_id IS NOT NULL;
