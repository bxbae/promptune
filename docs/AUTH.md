# 인증 (Authentication)

0번 로그인 단계의 실제 구현. 로컬(이메일/비밀번호) 로그인 완료, 소셜은 다음 단계.

## 로컬 로그인 흐름

```
[회원가입]
프론트 폼 → POST /api/auth/signup
  → 이메일 중복 확인 → 비밀번호 BCrypt 해싱 → DB 저장 → JWT 발급 → 반환

[로그인]
프론트 폼 → POST /api/auth/login
  → 사용자 조회 → 비밀번호 해시 대조 → JWT 발급 → 반환

[인증이 필요한 요청]
프론트가 Authorization: Bearer <token> 첨부
  → JwtAuthFilter가 토큰 검증 → 인증 상태 설정 → 처리
```

## 핵심 개념

- **BCrypt 해싱**: 비밀번호를 단방향 암호화해 저장. 원본은 복구 불가, 로그인 시
  `matches()`로 대조만. 평문 저장은 절대 금지.
- **JWT**: 로그인 성공 시 발급하는 서명된 토큰. 서버가 상태를 저장하지 않고
  (STATELESS), 토큰 자체로 인증을 증명. 24시간 유효.
- **Spring Security**: 위 과정을 프레임워크가 처리. `SecurityConfig`가 어떤
  경로에 인증이 필요한지 정의.

## 엔드포인트

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|:----:|------|
| POST | `/api/auth/signup` | 불필요 | 회원가입 (이메일·비번·이름) |
| POST | `/api/auth/login` | 불필요 | 로그인 → JWT 반환 |

## 구조

```
backend/
├── domain/User.java              # 사용자 엔티티
├── repository/UserRepository.java
├── dto/AuthDtos.java             # 요청·응답 형식
├── service/
│   ├── AuthService.java          # 회원가입·로그인 로직
│   └── JwtService.java           # 토큰 발급·검증
├── config/
│   ├── SecurityConfig.java       # Spring Security 설정
│   └── JwtAuthFilter.java        # 요청 토큰 검증 필터
└── controller/AuthController.java
frontend/
├── lib/auth.ts                   # 인증 API 호출 + 토큰 관리
└── components/AuthForm.tsx       # 로그인·회원가입 화면
```

## 소셜 로그인 (구조 완성, 키 설정 대기)

구글·카카오·네이버 OAuth2 코드가 모두 구현됨. **각 제공자 키를 환경변수로
넣으면 자동 활성화**된다. 키 없는 제공자는 자동 비활성(앱은 정상 기동).
설정법은 `docs/SOCIAL_LOGIN_SETUP.md` 참고.

각 제공자는 OAuth 2.0으로, 구조는 동일하고 설정값만 다르다:

| 제공자 | 등록처 | 담당(예정) |
|--------|--------|-----------|
| Google | Google Cloud Console | 승연 |
| Kakao | Kakao Developers | 승연 |
| Naver | Naver Developers | 승연 |

Spring Security OAuth2 Client를 추가하고 `application.yml`에 각 provider를
등록하면 된다. (역할표상 외부 인증은 승연 담당)

## 보안 메모 (실서비스 전환 시)

- JWT secret은 환경변수로 (`JWT_SECRET`). 현재 기본값은 개발용.
- 토큰을 지금은 localStorage에 저장(목업). 실서비스는 httpOnly 쿠키 권장 (XSS 대비).
- HTTPS 필수, 비밀번호 정책(길이·복잡도) 추가 권장.
