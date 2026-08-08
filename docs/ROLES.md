# 팀 역할 분담 (R&R)

## 책임자 구조

| 책임자 | 역할 | 참여 사원 |
|--------|------|-----------|
| 예진 | 프론트 코드 구조 책임자 | 승연(하) |
| 형기 | 백엔드 코드 구조 책임자 | 예진(중), 승득(상), 승연(상) |
| 병환 | 전체 Repository·Docker·Git·배포 구조 책임자 | 형기(하), 예진(하) |
| 승득 | AI/FastAPI 코드 구조 책임자 | 형기(상), 승연(상) |
| 승연 | Microsoft/외부 API 모듈 구조 책임자 | 형기(중) |

> 참여도: 상(무조건 참여) / 중(무조건은 아님) / 하(팀장 도움 요청 시)

## 담당 상세

| 책임자 | 메인 역할 | 담당 기술 | 구체 업무 |
|--------|-----------|-----------|-----------|
| **예진** | Frontend / UX | Next.js, React, TS, CSS | Prompt Editor, Ghost Text, 밑줄, Tab/Esc/↑↓, debounce, AbortController |
| **형기** | Backend / DB / 개인화 | Spring Boot, JPA, PostgreSQL, Security, Rule Engine | 설정·행동로그 저장, 개인화 점수, Gateway, 요청 분류 |
| **병환** | DevOps / Data Eng | Git, Docker, CI/CD, Python/API | **전체 Repo·Docker·Git·CI/CD·배포**, 학습 데이터 생성·정제·분할·버전관리 |
| **승득** | AI / ML | KcELECTRA, HyperCLOVA X, FastAPI, Pydantic | 모델 비교실험·학습·추론·평가, FastAPI 서버, Validator |
| **승연** | Retrieval / 외부연동 | MS Graph, Entra OAuth, Outlook, Tavily, BGE-M3, pgvector, S3 | MS 로그인·연동, Outlook 조회, Tavily, BGE-M3 임베딩, pgvector RAG |

---

## 이 레포에서 각자 건드리는 곳

| 담당 | 폴더/파일 | 단계 |
|------|-----------|------|
| **병환** (Repo·Docker·배포·데이터) | 루트 구조, `docker-compose.yml`, `.github/` (CI/CD), `ml/` (데이터) | 인프라 전반 |
| **예진** (프론트) | `frontend/` | 1,2,9,10 |
| **형기** (백엔드) | `backend/` | 0,3,4,6,11,12,16 |
| **승득** (AI) | `ai-service/app/services/diagnose_mock.py`, `pipeline_mock.py` | 5,7,8,14,15 |
| **승연** (외부 API) | `ai-service/.../retrieve_mock.py`(13), `backend/.../GraphMockService`(0,4) | 13, 0-1, 4 |

> 병환은 **전체 스캐폴드·Docker·CI/CD·데이터 파이프라인**을 담당하므로,
> 이 목업 레포 구조 자체가 병환의 산출물이다. 각 서비스의 내부 로직은
> 해당 담당자가 채운다.

## AI 단계 교체 담당 (ai-service)

| 단계 | 엔드포인트 | 담당 | mock → 실제 |
|------|-----------|------|-------------|
| 5 진단 | `/api/ai/diagnose` | 승득 | 규칙 → KcELECTRA |
| 7 추천 | `/api/ai/suggest` | 승득 | 템플릿 → HyperCLOVA |
| 8 안전 | `/api/ai/safety-check` | 승득 | 규칙 (실제) |
| 13 검색 | `/api/ai/retrieve` | 승연 | 샘플 → BGE-M3+pgvector |
| 14 생성 | `/api/ai/generate` | 승득 | 템플릿 → HyperCLOVA |
| 15 검증 | `/api/ai/validate` | 승득 | 규칙 → NLI+HyperCLOVA |
