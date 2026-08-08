# 진행 현황

🟢 **목업 스캐폴드 완성** — 4개 서비스 통합, 전체 흐름 동작. 팀원 교체 대기.

목업 스캐폴드 구축 상태. ✅ 완료 / 🟡 목업(교체대상) / ⬜ 미착수

## 인프라
- ✅ 폴더 구조 · docs
- ✅ CI/CD (GitHub Actions — 3서비스 빌드·테스트)
- ✅ docker-compose (통합, 헬스체크·순서 보장)
- ✅ PostgreSQL + pgvector 시드 (Flyway V2)

## Frontend (Next.js) — 1,2,9,10
- ✅ 프롬프트 입력 화면
- ✅ 입력중단 감지 (debounce + AbortController)
- ✅ 인라인 진단·Ghost text
- ✅ 키보드 선택 (Tab/Esc/↑↓/Enter)

## Backend (Spring Boot) — 0,3,4,6,11,12,16
- ✅ 게이트 검사 (금칙어·PII, 실제 규칙)
- 🟡 업무맥락 조회 (Graph mock)
- 🟡 수정요소 선정 (점수로직 mock)
- ✅ 요청 분류 (진단 연동)
- 🟡 행동저장 (주석, DB 연결 대기)
- 🟡 인증 (mock 세션)
- ✅ AI 오케스트레이션 (ai-service HTTP 연동)
- ✅ Flyway 스키마 (PostgreSQL+pgvector)

## AI Service (FastAPI) — 5,7,8,13,14,15
- 🟡 5 통합진단 (규칙 mock → KcELECTRA)
- 🟡 7 문구생성 (템플릿 mock → HyperCLOVA)
- ✅ 8 안전검사 (규칙, 실제 동작)
- 🟡 13 내부검색 (샘플 mock → BGE-M3)
- 🟡 14 답변생성 (템플릿 mock → HyperCLOVA)
- 🟡 15 최종검증 (규칙 mock → NLI+HyperCLOVA)

## ML (별도) — 모델 학습
- ✅ ko_vs_kc 학습·비교 (5-fold 완료, KoELECTRA 선정)
- ✅ labeling_kit (라벨링·kappa)

---

## 다음 작업 순서
1. ✅ 1단계: 뼈대 + docs  ← **지금 여기**
2. ⬜ 2단계: ai-service (FastAPI mock)
3. ✅ 3단계: backend (Spring Boot)  ← 방금 완료
4. ✅ 4단계: frontend (Next.js)  ← 방금 완료
5. ✅ 5단계: db 시드 + docker-compose 통합  ← 완료
