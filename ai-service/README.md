# AI Service (FastAPI)

PrompTune 파이프라인의 **AI 단계 5,7,8,13,14,15** 담당.
흐름도의 "프롬프트 분석/수정 추천" + "결과 생성" 영역.

## 실행

```bash
# 로컬
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Docker
docker build -t promptune-ai . && docker run -p 8000:8000 promptune-ai
```

- API 문서(자동): http://localhost:8000/docs
- 상태 확인: http://localhost:8000/mock-status

## 엔드포인트

| 단계 | 메서드 | 경로 | 담당 | mock→실제 |
|------|--------|------|------|-----------|
| 5 | POST | `/api/ai/diagnose` | 승득 | 규칙 → KcELECTRA |
| 7 | POST | `/api/ai/suggest` | 승득 | 템플릿 → HyperCLOVA |
| 8 | POST | `/api/ai/safety-check` | — | 규칙 (실제) |
| 13 | POST | `/api/ai/retrieve` | 승연 | 샘플 → BGE-M3+pgvector |
| 14 | POST | `/api/ai/generate` | 승득 | 템플릿 → HyperCLOVA |
| 15 | POST | `/api/ai/validate` | 승득 | 규칙 → NLI+HyperCLOVA |

## 구조

```
app/
├── main.py                 # FastAPI 앱, /health, /mock-status
├── routers/pipeline.py     # 엔드포인트 정의
├── schemas/models.py       # 입출력 형식(계약서) — 교체해도 이건 유지
└── services/
    ├── diagnose_mock.py     # 5번 (승득, KcELECTRA 자리)
    └── pipeline_mock.py     # 7,8,13,14,15번
```

## 교체 방법

각 `*_mock.py`의 `# TODO(담당자)` 주석을 찾아, mock 로직만 실제 모델 호출로
바꾼다. **입출력 형식(schemas/models.py)은 그대로** 두면 파이프라인 나머지는
안 건드려도 된다. 자세한 건 `docs/MOCK_GUIDE.md`.

## 흐름도 분기 반영

- **통합 진단(5)** → 8요소/오탈자/업무유형 3갈래를 한 번에 판정
- **업무유형 → 내부문서 필요 여부**: `_internal` 또는 `application`이면
  `needs_internal_docs=True` → 13번(RAG) 실행 (흐름도 분기 그대로)
- **답변 생성(14)** → `use_web_search`면 Tavily 결과 반영 (흐름도 "최신정보" 갈래)
