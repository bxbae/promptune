# Microsoft Graph 프로필 및 Outlook 연동 개발 보고서

## 1. 담당 영역

PrompTune 프로젝트에서 Microsoft 365 조직 계정과 서비스 연동을 위한 Microsoft Graph 기능을 담당하였다.

주요 개발 범위는 다음과 같다.

- Microsoft Entra ID 애플리케이션 연동
- Microsoft OAuth 인증
- Microsoft Graph 사용자 프로필 조회
- Microsoft 연결 정보 및 Token 관리
- Outlook Mail 조회
- Outlook Calendar 조회
- Microsoft 연동 Frontend UI 및 API 연결

---

## 2. Microsoft OAuth 연동

Microsoft 365 조직 계정을 PrompTune에 연결할 수 있도록 OAuth 인증 흐름을 구현하였다.

사용자가 Microsoft 계정 연결을 요청하면 Microsoft 인증을 거쳐 PrompTune Backend Callback으로 돌아오고, 이후 Microsoft Graph API를 사용할 수 있도록 연결 정보를 관리한다.

Microsoft 연동을 위한 주요 설정값은 다음과 같다.

- `MICROSOFT_CLIENT_ID`
- `MICROSOFT_CLIENT_SECRET`
- `MICROSOFT_TENANT`
- `MICROSOFT_TOKEN_KEY`
- `MICROSOFT_REDIRECT_URI`
- `MICROSOFT_FRONTEND_URL`

Microsoft Access Token 및 Refresh Token과 같은 인증 정보는 별도의 Token 처리 서비스를 통해 관리하도록 구성하였다.

---

## 3. Microsoft 사용자 프로필 조회

Microsoft Graph API를 이용하여 사용자의 Microsoft 365 조직 프로필을 조회하도록 구현하였다.

최종적으로 PrompTune에서 활용하기로 한 사용자 프로필 정보는 다음 5개 항목이다.

| Microsoft Graph 필드         | PrompTune 활용 정보 |
| ---------------------------- | ------------------- |
| `displayName`                | 이름                |
| `mail` / `userPrincipalName` | 회사 이메일         |
| `companyName`                | 회사명              |
| `department`                 | 부서                |
| `jobTitle`                   | 직급 / 직함         |

Microsoft Graph에서 제공하는 `id` 값은 사용자에게 표시하는 프로필 항목이 아니라 Microsoft 사용자를 구분하기 위한 내부 식별값으로 활용한다.

### 프로필 처리 흐름

Microsoft 계정 연결
→ Microsoft Graph `/me` 호출
→ 프로필 정보 조회
→ Frontend 전달
→ 설정 화면에서 프로필 표시

---

## 4. Outlook Calendar 연동

Microsoft Graph의 Calendar 권한을 이용하여 연결된 Microsoft 사용자의 Outlook 일정 데이터를 조회하도록 구현하였다.

### 사용 권한

`Calendars.Read`

### Microsoft Graph API

`/v1.0/me/events?$top=10`

최근 일정 최대 10개를 Microsoft Graph에서 조회할 수 있도록 구성하였다.

### PrompTune Backend API

`GET /api/integrations/microsoft/events`

Backend의 `MicrosoftIntegrationController`에서 요청을 받고 `MicrosoftGraphService`를 통해 Microsoft Graph Calendar API를 호출하도록 구성하였다.

Frontend에서도 해당 Backend API를 호출할 수 있도록 Microsoft API 모듈을 구현하였다.

---

## 5. Outlook Mail 연동

Microsoft Graph를 이용하여 연결된 사용자의 Outlook Mail 데이터를 조회하도록 구현하였다.

### 사용 권한

`Mail.Read`

### Microsoft Graph API

`/v1.0/me/messages?$top=10`

최근 메일 최대 10개를 Microsoft Graph에서 조회할 수 있도록 구성하였다.

### PrompTune Backend API

`GET /api/integrations/microsoft/messages`

Backend의 `MicrosoftIntegrationController`가 요청을 전달받아 `MicrosoftGraphService`를 통해 Microsoft Graph Mail API를 호출한다.

Frontend에서도 해당 Backend API를 호출할 수 있도록 Microsoft API 모듈을 연결하였다.

---

## 6. 전체 Microsoft Graph 연동 구조

Microsoft Entra ID
→ Microsoft OAuth 인증
→ PrompTune Backend Callback
→ Microsoft Token 관리
→ Microsoft Graph API
→ 사용자 Profile / Outlook Mail / Outlook Calendar 조회
→ PrompTune Frontend 전달

### Profile

`/me`
→ 이름
→ 회사 이메일
→ 회사명
→ 부서
→ 직급

### Calendar

`/me/events`
→ Outlook 일정 조회

### Mail

`/me/messages`
→ Outlook 메일 조회

---

# 7. 개발 파일

## 7.1 신규 생성 파일

Microsoft Graph 연동을 위해 직접 신규 생성한 파일은 총 11개이다.

### Backend Controller

`backend/src/main/java/com/promptune/controller/MicrosoftIntegrationController.java`

Microsoft 계정 연결과 Microsoft Graph 기능을 외부에 제공하는 API Controller.

주요 역할:

- Microsoft OAuth 연동 API
- Microsoft Graph Profile 요청 처리
- Outlook Calendar `/events` 요청 처리
- Outlook Mail `/messages` 요청 처리

---

### Backend Service

`backend/src/main/java/com/promptune/service/MicrosoftGraphService.java`

Microsoft Graph와 직접 통신하는 핵심 Service.

주요 역할:

- Microsoft OAuth 처리
- Microsoft Graph API 호출
- 사용자 Profile 조회
- `Mail.Read` 권한 사용
- `Calendars.Read` 권한 사용
- `/v1.0/me/messages` 조회
- `/v1.0/me/events` 조회

---

`backend/src/main/java/com/promptune/service/TokenCryptoService.java`

Microsoft 인증 Token을 안전하게 관리하기 위한 Token 암호화 및 복호화 처리.

---

### Backend Domain

`backend/src/main/java/com/promptune/domain/MicrosoftConnection.java`

PrompTune 사용자와 Microsoft 계정 간 연결 상태 및 인증 정보를 표현하는 Domain.

---

`backend/src/main/java/com/promptune/domain/MicrosoftOauthState.java`

Microsoft OAuth 인증 과정에서 사용하는 State 정보를 관리하기 위한 Domain.

---

### Backend Repository

`backend/src/main/java/com/promptune/repository/MicrosoftConnectionRepository.java`

Microsoft 계정 연결 정보를 데이터베이스에서 조회 및 관리.

---

`backend/src/main/java/com/promptune/repository/MicrosoftOauthStateRepository.java`

Microsoft OAuth State 데이터를 데이터베이스에서 조회 및 관리.

---

### Database Migration

`backend/src/main/resources/db/migration/V6__add_microsoft_graph_connection.sql`

Microsoft Graph 계정 연결 기능에 필요한 데이터베이스 구조 추가.

---

### Frontend Profile Component

`frontend/src/app/settings/components/MicrosoftProfileView.tsx`

Microsoft Graph에서 조회한 사용자 조직 프로필을 설정 화면에 표시.

주요 표시 항목:

- 이름
- 회사 이메일
- 회사명
- 부서
- 직급 / 직함

---

### Frontend Settings

`frontend/src/app/settings/page.tsx`

PrompTune 설정 화면에 Microsoft 계정 연결 및 Profile 기능을 연결.

---

### Frontend Microsoft API

`frontend/src/lib/microsoft.ts`

Frontend와 Microsoft 연동 Backend API 사이의 통신 담당.

주요 기능:

- Microsoft 연결 API 호출
- 사용자 Profile 조회
- Outlook Calendar 조회
- Outlook Mail 조회

---

## 7.2 기존 파일 수정

`backend/src/main/resources/application.yml`

기존 Backend 설정 파일에 Microsoft Graph 및 OAuth 연동을 위한 설정을 추가하였다.

---

## 8. Git 작업 기록

### 2026-08-10

`feat: Microsoft Graph 계정 연동 구현`

Microsoft Graph 계정 연동의 기본 구조를 구현하였다.

주요 작업:

- Microsoft Graph Controller
- Microsoft Graph Service
- Token 암호화 처리
- Microsoft 연결 Domain
- OAuth State Domain
- Repository
- DB Migration
- Frontend Microsoft API
- Settings 연동

### 2026-08-11

`feat: Microsoft Graph 사용자 프로필 조회 추가`

Microsoft Graph에서 조직 사용자 Profile을 조회하여 PrompTune Frontend에 표시하는 기능을 추가하였다.

주요 추가 항목:

- 이름
- 회사 이메일
- 회사명
- 부서
- 직급 / 직함

---

## 9. 담당 파일 요약

### 신규 생성 — 11개

1. `MicrosoftIntegrationController.java`
2. `MicrosoftGraphService.java`
3. `TokenCryptoService.java`
4. `MicrosoftConnection.java`
5. `MicrosoftOauthState.java`
6. `MicrosoftConnectionRepository.java`
7. `MicrosoftOauthStateRepository.java`
8. `V6__add_microsoft_graph_connection.sql`
9. `MicrosoftProfileView.tsx`
10. `frontend/src/app/settings/page.tsx`
11. `frontend/src/lib/microsoft.ts`

### 기존 파일 수정 — 1개

1. `backend/src/main/resources/application.yml`

---

## 10. 담당 범위에서 제외한 파일

Microsoft 관련 문자열이 포함되어 검색되었지만 직접 생성한 Microsoft Graph 담당 파일이 아닌 다음 파일은 본 보고서의 담당 파일 목록에서 제외하였다.

- `GraphMockService.java`
- `OAuth2ClientConfig.java`
- `OAuth2SuccessHandler.java`
- `OAuth2UserService.java`
- `.env.example`
- `docker-compose.yml`
- `User.java`
- `V1__init.sql`
- `V2__seed.sql`

---

## 11. 최종 구현 결과

Microsoft 365 조직 계정을 PrompTune과 연결할 수 있는 Microsoft Graph 연동 기반을 구축하였다.

Microsoft Graph를 통해 사용자의 이름, 회사 이메일, 회사명, 부서, 직급 정보를 조회할 수 있도록 구현하였으며, Outlook Mail과 Calendar 데이터를 조회하기 위한 API도 구현하였다.

이를 통해 PrompTune에서 Microsoft 365 조직 정보와 업무 데이터를 활용할 수 있는 외부 서비스 연동 기반을 구성하였다.
