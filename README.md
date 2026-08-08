# PrompTune (프롬프튠)

한국어 프롬프트 개선 AI 코파일럿. 사용자가 입력한 거친 업무 지시문에서
**부족한 요소(8요소)를 감지해 되묻고**, 보완된 프롬프트로 최종 결과물을 생성한다.

> **이 레포는 "동작하는 목업(mockup)"이다.** 16단계 파이프라인 전체가 실제로
> 연결되어 흐르지만, AI 모델·외부 API 부분은 가짜 응답(mock)으로 채워져 있다.
> 각 팀원이 자기 담당 mock을 실제 구현으로 **교체**하면 된다.
> 교체 방법은 [`docs/MOCK_GUIDE.md`](docs/MOCK_GUIDE.md) 참고.

---

## 목업 3원칙

1. **흐름은 진짜** — 프론트→백엔드→AI 서비스가 실제 HTTP로 연결되고, 데이터가
   16단계를 따라 흐른다.
2. **내용은 가짜** — KcELECTRA·HyperCLOVA X·BGE-M3·MS Graph 등은 규칙 기반
   또는 샘플 응답으로 대체(mock). 모델 없이도 전체가 돌아간다.
3. **교체 지점 명시** — 모든 mock에 `# TODO(담당자): 실제 구현` 주석과 입출력
   형식이 문서화되어 있다. 팀원은 이 지점만 바꾸면 된다.

---

## 아키텍처

```
[frontend]  Next.js + React + TypeScript      단계 1,2,9,10 (입력·표시·선택)
     │  HTTP
[backend]   Spring Boot + JPA + Flyway         단계 0,3,4,6,11,12,16 (게이트·맥락·점수·저장)
     │  HTTP
[ai-service] FastAPI + Python                  단계 5,7,8,13,14,15 (진단·생성·검증·검색)
     │
[db]        PostgreSQL + pgvector              온보딩·개인화·문서 임베딩
```

전체 16단계 상세는 [`docs/PIPELINE.md`](docs/PIPELINE.md) 참고.

---

## 빠른 시작

```bash
# 전체 스택 한 번에 실행 (Docker)
docker compose up --build

# 접속
# 프론트:      http://localhost:3000
# 백엔드 API:  http://localhost:8080
# AI 서비스:   http://localhost:8000/docs  (FastAPI 자동 문서)
```

개별 실행·개발 방법은 각 폴더의 README 참고:
- [`frontend/README.md`](frontend/README.md)
- [`backend/README.md`](backend/README.md)
- [`ai-service/README.md`](ai-service/README.md)

---

## 담당자별 교체 대상 (요약)

| 영역 | 단계 | 담당(예시) | mock → 실제 |
|------|------|-----------|-------------|
| AI 진단 | 5 | 승득 | 규칙 8요소 판정 → KcELECTRA |
| AI 생성 | 7,14 | 승득 | 템플릿 문구 → HyperCLOVA X |
| AI 검색 | 13 | 승연 | 샘플 문서 → BGE-M3 + pgvector |
| AI 검증 | 15 | 승득 | 규칙 검증 → KcELECTRA NLI + HyperCLOVA |
| 백엔드 인증 | 0,4 | 승연 | mock 세션 → OAuth2 + MS Graph |
| 프론트 | 1,2,9,10 | 예진 | (실제 UI 구현됨) |
| 인프라·데이터 | 전체 | 병환 | Repo·Docker·CI/CD·데이터 파이프라인 |

정확한 교체 절차는 [`docs/MOCK_GUIDE.md`](docs/MOCK_GUIDE.md).

---

## 기술 스택

- **Frontend**: Next.js 14 (App Router), React, TypeScript
- **Backend**: Spring Boot 3, JPA, Flyway, Spring Security (OAuth2)
- **AI Service**: FastAPI, Python 3.11
- **DB**: PostgreSQL 16 + pgvector
- **Infra**: Docker Compose

## 프로젝트 상태

🟢 **목업 완성** — 4개 서비스(프론트·백·AI·DB) 통합, 전체 흐름 동작. 실제 모델·API는 교체 대기.
진행 현황은 [`docs/STATUS.md`](docs/STATUS.md), 역할 분담은 [`docs/ROLES.md`](docs/ROLES.md) 참고.
