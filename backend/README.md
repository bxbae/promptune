# Backend (Spring Boot)

PrompTune 파이프라인의 **백엔드 단계 0,3,4,6,11,12,16** 담당 + AI 오케스트레이션.
흐름도의 "사용자 입력/조작" 백엔드 처리 + AI 서비스 호출.

## 실행

```bash
# DB 먼저 (docker compose up db)
./gradlew bootRun

# Docker
docker build -t promptune-backend . && docker run -p 8080:8080 promptune-backend
```

## 엔드포인트

| 단계 | 메서드 | 경로 | 하는 일 |
|------|--------|------|---------|
| 2 | POST | `/api/analyze` | 게이트(3)→진단(5,AI)→추천선정(6) |
| 11 | POST | `/api/execute` | 분류(12)→생성(14,AI)→저장(16) |
| 0 | GET | `/api/context/{userId}` | 로그인 후 사용자 맥락(4) |

## 구조

```
service/
├── GateService.java        # 3번 게이트 (형기, 실제 규칙)
├── RecommendService.java   # 6번 점수로직 (형기, mock)
├── AiServiceClient.java    # ai-service HTTP 호출
└── GraphMockService.java   # 0,4번 인증·Graph (승연, mock)
controller/
└── PipelineController.java # 오케스트레이터
resources/
├── application.yml
└── db/migration/V1__init.sql  # PostgreSQL + pgvector 스키마
```

## 교체 대상 (mock)

| 담당 | 파일 | mock → 실제 |
|------|------|-------------|
| 형기 | RecommendService | 단순 우선순위 → Tab/Esc기록+MS365 점수로직 |
| 승연 | GraphMockService | 샘플 → OAuth2 + MS Graph API |
| 형기 | execute()의 16번 | (주석) → PostgreSQL 행동로그 저장 |

## DB (PostgreSQL + pgvector)

Flyway가 스키마 관리 (`V1__init.sql`). 테이블: users, user_preferences,
prompt_sessions, behavior_logs, documents(vector 1024차원 = BGE-M3).
