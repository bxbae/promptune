# 소셜 로그인 설정 가이드

코드는 이미 완성돼 있다. **각 제공자에서 키를 발급받아 환경변수로 넣으면** 그
제공자가 자동 활성화된다. 키를 안 넣은 제공자는 자동으로 비활성(앱은 정상 기동).

## 공통: 리다이렉트 URI

각 제공자 콘솔에 아래 **redirect URI**를 등록해야 한다 (로컬 개발 기준):

| 제공자 | Redirect URI |
|--------|--------------|
| Google | `http://localhost:8080/login/oauth2/code/google` |
| Naver | `http://localhost:8080/login/oauth2/code/naver` |
| Kakao | `http://localhost:8080/login/oauth2/code/kakao` |

배포 시엔 `localhost:8080`을 실제 백엔드 도메인으로 바꾼다.

## 1. Google

1. https://console.cloud.google.com → 프로젝트 생성
2. "API 및 서비스 → OAuth 동의 화면" 설정
3. "사용자 인증 정보 → OAuth 클라이언트 ID 생성" (웹 애플리케이션)
4. 승인된 리다이렉트 URI에 위 Google URI 추가
5. 발급된 **클라이언트 ID·비밀** 을 환경변수로:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```

## 2. Kakao

1. https://developers.kakao.com → 애플리케이션 추가
2. "앱 키"에서 **REST API 키** 확인 → `KAKAO_CLIENT_ID`로 사용
3. "카카오 로그인" 활성화 ON
4. "Redirect URI"에 위 Kakao URI 등록
5. "동의항목"에서 닉네임·이메일 사용 설정
6. (선택) "보안 → Client Secret" 생성 시 `KAKAO_CLIENT_SECRET`
   ```
   KAKAO_CLIENT_ID=<REST API 키>
   KAKAO_CLIENT_SECRET=<Client Secret, 없으면 비워도 됨>
   ```

## 3. Naver

1. https://developers.naver.com → "애플리케이션 등록"
2. 사용 API: "네이버 로그인" 선택, 이메일·이름 권한
3. 서비스 URL·Callback URL에 위 Naver URI 등록
4. 발급된 **Client ID·Secret**:
   ```
   NAVER_CLIENT_ID=...
   NAVER_CLIENT_SECRET=...
   ```

## 환경변수 넣는 법

**로컬 개발** — `backend/.env` 또는 실행 환경에:
```bash
export GOOGLE_CLIENT_ID=...
export GOOGLE_CLIENT_SECRET=...
# (원하는 제공자만)
```

**Docker Compose** — `docker-compose.yml`의 backend environment에 추가:
```yaml
  backend:
    environment:
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
      # ...
```
그리고 프로젝트 루트 `.env`에 실제 값 (이 파일은 .gitignore로 제외됨).

## 동작 확인

1. 키 넣고 백엔드 재시작
2. 프론트 로그인 화면에서 "Google로 계속" 클릭
3. 구글 로그인·동의 → 자동으로 우리 서비스에 가입/로그인 → 메인으로

## 흐름 (참고)

```
버튼 클릭 → /oauth2/authorization/google
  → 구글 로그인·동의
  → /login/oauth2/code/google (백엔드가 코드 받음)
  → 사용자 정보 조회 → DB 자동가입 → JWT 발급
  → 프론트 /oauth/callback?token=... 로 리다이렉트
  → 프론트가 토큰 저장 → 로그인 완료
```

## 보안 주의

- 키(secret)는 **절대 코드·git에 넣지 않는다**. 환경변수만.
- `.env`는 `.gitignore`에 포함돼 있다 (확인 완료).
