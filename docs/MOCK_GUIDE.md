# Mock 교체 가이드

이 레포의 mock을 실제 구현으로 바꾸는 방법. **핵심 원칙: mock과 실제 구현은
입출력 형식(schema)이 같다.** 형식만 지키면 파이프라인 나머지는 안 건드려도 된다.

---

## 교체 방법 (공통 3단계)

1. **찾기** — 코드에서 `# TODO(담당자):` 또는 `// TODO(담당자):` 주석을 검색
2. **형식 확인** — 그 함수의 입력/출력 타입(schema)을 그대로 유지
3. **속만 교체** — mock 로직만 실제 모델 호출로 바꾸고, 반환 형식은 유지

> mock 함수는 `services/*_mock.py` 또는 `*Mock.java`로 분리돼 있다.
> 실제 구현은 `_real.py`로 새로 만들고, 설정에서 스위치만 바꾸면 된다
> (환경변수 `USE_REAL_MODELS=true`).

---

## 담당자별 교체 대상

### 승득 — 5번 통합 진단 (KcELECTRA)
- **파일**: `ai-service/app/services/diagnose_mock.py`
- **지금 (mock)**: 규칙으로 8요소 누락 판정 (키워드 매칭)
- **교체할 것**: 학습한 KcELECTRA로 멀티라벨 분류
- **입출력 형식** (이것만 지키면 됨):
  ```python
  입력: {"text": "회의록 정리해줘 팀장님께"}
  출력: {
    "missing": {"TASK": 0, "AUDIENCE": 0, "CONTEXT": 1, "FORMAT": 1,
                "TONE": 1, "LENGTH": 1, "CONSTRAINT": 1, "EXAMPLE": 1},
    "task_type": "report",     # 업무유형 7종 중
    "typos": []                # 오탈자 위치 리스트
  }
  ```
- **참고**: 학습 코드는 `ml/ko_vs_kc/` (병환이 데이터 harness 구축). 학습된 모델을
  `ai-service`에서 로드하면 된다.

### 승득 — 7,14번 문구/답변 생성 (HyperCLOVA X)
- **파일**: `ai-service/app/services/generate_mock.py`
- **지금 (mock)**: 요소별 템플릿 문구 반환
- **교체할 것**: HyperCLOVA X API 호출
- **입출력 형식**:
  ```python
  입력: {"text": "...", "target_elements": ["AUDIENCE", "TONE"]}
  출력: {"suggestions": ["팀장님께", "정중한 어조로"], "alternatives": [...]}
  ```

### 승연 — 13번 내부문서 검색 (BGE-M3 + pgvector)
- **파일**: `ai-service/app/services/retrieve_mock.py`
- **지금 (mock)**: 샘플 문서 3건 고정 반환
- **교체할 것**: BGE-M3 임베딩 + pgvector 유사도 검색
- **입출력 형식**:
  ```python
  입력: {"query": "휴가 규정", "top_k": 3}
  출력: {"documents": [{"title": "...", "content": "...", "score": 0.87}]}
  ```

### 승득 — 15번 최종 검증 (KcELECTRA NLI + HyperCLOVA)
- **파일**: `ai-service/app/services/validate_mock.py`
- **지금 (mock)**: 규칙으로 숫자·날짜 보존만 검사
- **교체할 것**: KcELECTRA NLI(모순 검출) + HyperCLOVA 자기검증 추가
- **입출력 형식**:
  ```python
  입력: {"original": "...", "generated": "..."}
  출력: {"passed": true, "tone_ok": true, "no_contradiction": true,
         "facts_preserved": true, "issues": []}
  ```

### 승연 — 0,0-1,4번 인증·업무맥락 (OAuth2 + MS Graph)
- **파일**: `backend/.../service/AuthMockService.java`, `GraphMockService.java`
- **지금 (mock)**: 고정 사용자 세션 + 샘플 일정 반환
- **교체할 것**: Spring Security OAuth2 + MS Graph API 실제 호출
- **입출력 형식**:
  ```java
  getUserContext(userId) → { department, position, upcomingEvents[] }
  ```

### 예진 — 프론트 (1,2,9,10)
- 프론트는 **실제 UI로 구현**되어 있음. mock이 아님.
- 백엔드 API가 mock 응답을 주므로, 그 응답으로 화면이 실제로 동작한다.
- 백엔드가 실제로 바뀌면 프론트는 자동으로 실제 데이터를 받는다 (수정 불필요).

---

## 교체 순서 추천

의존성 때문에 이 순서가 편하다:

1. **5번 (진단)** — 파이프라인의 첫 AI 단계. 이게 실제가 되면 나머지 입력이 정확해짐
2. **7,14번 (생성)** — 사용자가 체감하는 결과물
3. **15번 (검증)** — 생성 결과를 검증
4. **13번 (검색)** — 내부문서 RAG (P1, 나중에)
5. **0,4번 (인증·Graph)** — 실서비스 전환 시

각 단계는 독립적으로 교체 가능하다. 하나 바꿔도 나머지 mock과 섞여 돌아간다.

---

## 교체가 잘 됐는지 확인

```bash
# mock 상태로 전체 흐름 테스트
USE_REAL_MODELS=false docker compose up

# 특정 팀원 파트만 실제로 전환
USE_REAL_MODELS=true docker compose up   # (환경변수·API키 설정 후)
```

각 서비스에 `/health`와 `/mock-status` 엔드포인트가 있어, 지금 mock인지
실제인지 확인할 수 있다.
