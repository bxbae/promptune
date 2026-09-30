# PrompTune (프롬프튠)

[![CI](https://github.com/bxbae/promptune/actions/workflows/ci.yml/badge.svg)](https://github.com/bxbae/promptune/actions/workflows/ci.yml)

한국어 프롬프트 개선 AI 코파일럿. 사용자가 입력한 거친 업무 지시문에서
**부족한 요소(8요소)를 감지해 되묻고**, 보완된 프롬프트로 최종 결과물을 생성한다.

> 팀 프로젝트. 16단계 파이프라인 전체가 실제로
> 연결되어 흐르는 "동작하는 목업" 위에서, 각 담당자가 mock을 실제 구현으로 교체하는 방식으로 진행했다.
> 교체 방법은 [`docs/MOCK_GUIDE.md`](docs/MOCK_GUIDE.md) 참고.

---

## My Role — 병환 (인프라·데이터 / KoELECTRA 담당)

| 영역 | 한 일 |
|------|-------|
| 인프라 | 모노레포 구성, 4개 서비스 Docker Compose 통합, CI/CD 구축 |
| 데이터 파이프라인 | 8요소 라벨링 키트 제작 — 원문 추출(PII 마스킹·중복 제거) → LLM/규칙 사전 라벨링 → 사람 검수 → kappa 측정 → gold 확정 |
| 검수 도구 | `review_tool.html` — 규칙 라벨을 숨긴 독립 검수용 웹 도구 |
| 라벨 신뢰도 | 2인 독립 검수(검수자 A) 수행, 요소별 Cohen's kappa 분석 |
| 모델 비교 | KoELECTRA vs KcELECTRA 학습·평가 harness 구축, Recall·F2 기반 검증 기준 수립 |

---

## 주요 결과

### 1) 라벨 신뢰도 — 2인 독립 검수 (30건)
검수자 A(병환)·B(팀원 hg)가 상의 없이 각자 판정한 결과. **평균 kappa 0.404 (moderate)**.

| 잘 합의된 요소 | 합의가 안 된 요소 |
|---|---|
| AUDIENCE 0.862 · LENGTH 0.706 · TONE 0.658 | CONTEXT 0.070 · FORMAT 0.179 · CONSTRAINT 0.233 |

→ 낮은 요소는 **라벨링 기준 자체가 모호하다는 신호**. 판정 예시를 가이드에 명문화한 뒤 재검수 예정.
(TASK는 거의 모든 건이 '포함'이라 kappa 0.000이지만 단순 일치율은 93%.)

### 2) K모델 비교 — 질문 트리거 용도 (합성 1,500건)
"빠진 요소를 놓치면 되묻지 않는다" → 놓침(FN)이 치명적이므로 **Recall·F2** 중심으로 평가.

| 모델 | Macro F2 | 놓친 누락 |
|------|:---:|:---:|
| 규칙 baseline | 0.907 | 37건 |
| **KoELECTRA** (1차 추천) | 0.776 | 188건 |
| KcELECTRA | 0.737 | 205건 |

- 두 신경망 모두 baseline 미달. 합성 데이터가 규칙과 같은 키워드로 생성돼 baseline이 과대평가됐고, Ko는 4에폭에도 상승 중(과소적합).
- **결론은 잠정적** — 실사용 데이터 + 2인 검수 gold로 재학습·재검증 필요.

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
docker compose up --build

# 프론트:      http://localhost:3000
# 백엔드 API:  http://localhost:8080
# AI 서비스:   http://localhost:8000/docs
```

개별 실행: [`frontend/README.md`](frontend/README.md) · [`backend/README.md`](backend/README.md) · [`ai-service/README.md`](ai-service/README.md)

---

## 팀 역할 분담

| 영역 | 단계 | 담당 | mock → 실제 |
|------|------|------|-------------|
| AI 진단 | 5 | 승득·병환 | 규칙 8요소 판정 → KcELECTRA |
| AI 생성 | 7,14 | 승득·병환 | 템플릿 문구 → HyperCLOVA X |
| AI 검색 | 13 | 승연·병환 | 샘플 문서 → BGE-M3 + pgvector |
| AI 검증 | 15 | 승득·병환 | 규칙 검증 → KcELECTRA NLI + HyperCLOVA |
| 백엔드 인증 | 0,4 | 승연·병환 | mock 세션 → OAuth2 + MS Graph |
| 프론트 | 1,2,9,10 | 예진·병환 | 실제 UI 구현 |
| 인프라·데이터 | 전체 | 병환 | Repo·Docker·CI/CD·라벨링 파이프라인·KoELECTRA 비교 |
| 라벨 검수 | — | 병환·hg | 2인 독립 검수 |

상세는 [`docs/ROLES.md`](docs/ROLES.md).

---

## 기술 스택

- **Frontend**: Next.js 14 (App Router), React, TypeScript
- **Backend**: Spring Boot 3, JPA, Flyway, Spring Security (OAuth2)
- **AI Service**: FastAPI, Python 3.11
- **ML**: KoELECTRA, KcELECTRA (Hugging Face Transformers)
- **DB**: PostgreSQL 16 + pgvector
- **Infra**: Docker Compose, GitHub Actions

## 프로젝트 상태

- 🟢 목업 완성 — 4개 서비스 통합, 전체 흐름 동작
- 🟢 8요소 라벨링 파이프라인 · 2인 검수 · Ko vs Kc 1차 비교 완료
- 🟡 다음 — 실사용 데이터 확보(dogfooding) → 라벨 기준 합의·재검수 → 재학습

진행 현황은 [`docs/STATUS.md`](docs/STATUS.md) 참고.
