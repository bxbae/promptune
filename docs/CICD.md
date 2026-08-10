# CI/CD (GitHub Actions)

`.github/workflows/ci.yml` — main 푸시와 모든 PR에서 자동 실행되는 검증 파이프라인.

## 무엇을 검증하나

| Job | 대상 | 하는 일 |
|-----|------|---------|
| **ai-service** | FastAPI | 의존성 설치 → 앱 기동 → 엔드포인트 스모크 테스트 (진단이 실제로 동작하는지) |
| **backend** | Spring Boot | Java 21 컴파일 검증 |
| **frontend** | Next.js | 의존성 설치 → 타입 체크 → 빌드 |
| **docker-build** | 전체 | 위 3개 통과 후 compose 문법 검증 + 이미지 빌드 |

## 흐름

```
PR 생성/푸시
   ├─ ai-service ┐
   ├─ backend    ┤ (병렬 실행)
   └─ frontend   ┘
        ↓ 모두 통과하면
     docker-build (통합 빌드 검증)
```

세 서비스를 병렬로 검증하고, 다 통과해야 Docker 통합 빌드를 돌립니다.
하나라도 깨지면 PR에 ❌가 표시되어 머지 전에 문제를 잡습니다.

## 스모크 테스트 (ai-service)

단순 빌드만이 아니라 **실제로 동작하는지** 확인합니다:
- `/health`가 응답하는가
- "휴가 신청서" 입력 시 `application`으로 분류되고 내부문서 필요 판정이 되는가

즉 흐름도의 핵심 분기가 깨지지 않았는지 매 PR마다 자동 확인합니다.

## 팀 협업

- PR을 올리면 CI가 자동으로 돌아 초록/빨강으로 결과 표시
- `docs/MOCK_GUIDE.md` 형식(schema)을 어기면 스모크 테스트가 잡아냄
- README 상단 배지로 main의 현재 상태를 한눈에 확인

## 확장 아이디어 (향후)

- 실제 모델 연결 후: 모델 추론 테스트 추가
- 배포 자동화: main 머지 시 이미지를 레지스트리에 푸시 → k8s 배포
- 커버리지 리포트, lint 추가
