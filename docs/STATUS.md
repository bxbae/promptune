# 진행 현황

🟢 **목업 완성 + 실제 구현 진행 중** — 4개 서비스 통합·전체 흐름 동작. 팀원들이
각자 담당 mock을 실제 구현으로 교체하는 중.

> 최종 갱신: 형기(개인화 V4·V5), 승득(KcELECTRA 진단 실제구현 완료) 반영.

---

## 인프라 (병환) — 완료 ✅
- ✅ 폴더 구조 · docs
- ✅ CI/CD (GitHub Actions — 3서비스 빌드·테스트, 통과)
- ✅ docker-compose 통합 (헬스체크·기동 순서 보장)
- ✅ PostgreSQL + pgvector 시드 (Flyway)
- ✅ 빌드 캐시·산출물 git 추적 제거, .gitignore 정비
- ⬜ AWS RDS 배포 (예정 — 팀 공용 DB)

## Frontend (예진) — 1,2,9,10 — 완료 ✅
- ✅ 프롬프트 입력 화면
- ✅ 입력중단 감지 (debounce + AbortController)
- ✅ 인라인 진단 · Ghost text
- ✅ 키보드 선택 (Tab/Esc/↑↓/Enter)

## Backend (형기) — 0,3,4,6,11,12,16
- ✅ 게이트 검사 (3, 금칙어·PII, 실제 규칙)
- ✅ 요청 분류 (12, RequestClassificationService — V5)
- ✅ AI 오케스트레이션 (HTTP 연동)
- ✅ Flyway 스키마 (V1~V5)
- 🟢 행동 저장 (16, BehaviorLogService + V4) — mock→실제 진행 중
- 🟢 개인화 점수 (6, PersonalizationScore + V4) — mock→실제 진행 중
- 🟡 수정요소 선정 (6, RecommendService) — 점수로직 실제화 진행 중
- 🟡 업무맥락 조회 (4, Graph mock) — 실제 연동 대기
- 🟡 인증 (0, 로컬 완료 / 소셜 구조 완료·키 대기) — 실연결은 승연과 협의

## AI Service — 5,7,8,13,14,15
- ✅ FastAPI mock 스캐폴드 (전체 엔드포인트 동작)
- ✅ 8 안전검사 (규칙, 실제 동작)
- ✅ 5 통합진단 (승득) — **KcELECTRA 실제 구현 완료** (USE_REAL_DIAGNOSIS로 mock/real 전환)
- 🟡 7 문구생성 (승득) — 템플릿→HyperCLOVA
- 🟡 14 답변생성 (승득) — 템플릿→HyperCLOVA
- 🟡 15 최종검증 (승득) — 규칙→NLI+HyperCLOVA
- 🟡 13 내부검색 (승연) — 샘플→BGE-M3+pgvector

## ML (병환/승득) — 완료 ✅
- ✅ KoELECTRA vs KcELECTRA 5-fold 교차검증 → KoELECTRA 선정
- ✅ 라벨링 킷 (kappa 측정)
- ✅ 라벨링 기준 개정 ("보완 필요" 기준)

## 인증 (형기/승연) — 0단계
- ✅ 로컬 로그인 (이메일/비밀번호, JWT) — 완전 작동
- ✅ 소셜 로그인 구조 (구글·카카오·네이버 OAuth2) — 키 설정 후 작동
- ✅ 키 없이도 앱 기동 (빈 제공자 자동 제외)
- 🟡 소셜 실연결·테스트 (승연) — 키 입력됨, 배포 도메인 확정 후 redirect URI 추가

---

## 범례
✅ 완료 / 🟢 실제 구현 진행 중 / 🟡 mock (교체 대기) / ⬜ 미착수

## 남은 큰 작업
1. AWS RDS 배포 (병환) — 팀 공용 DB
2. AI 모델 3개 실제화 (승득) — HyperCLOVA (문구생성7·답변생성14·검증15). 진단(5) 완료 ✅
3. 내부검색 실제화 (승연) — BGE-M3+pgvector
4. 외부맥락·소셜 실연결 (승연) — MS Graph, OAuth 실테스트
5. 배포 시 환경변수·CORS·redirect URI 정리 (→ docs/DEPLOYMENT.md)

## 브랜치 현황 (참고)
- `main` — 통합 (진단 real 병합됨)
- `feat/backend-personalization` (형기) — 개인화·행동로그
- `feature/kcelectra-diagnosis` (승득) — 5단계 진단 (main 병합 완료)
