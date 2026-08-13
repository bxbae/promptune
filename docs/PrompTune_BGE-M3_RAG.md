# PrompTune BGE-M3 RAG 작업 핵심 요약

작성 기준일: 2026-08-13  
대상: PrompTune 팀 공유 / 기술 발표 / 면접 대비  
담당 범위: BGE-M3 Embedding, Retrieval, pgvector, 사용자 문서 격리, Retrieval Routing, FastAPI E2E

---

# 0. 최종 상태 한눈에 보기

PrompTune의 내부 문서 검색 기능을 다음 흐름으로 구현하고 검증했다.

```text
사용자 질문
    ↓
Retrieval Router
    ├─ internal_rag
    │    ↓
    │  BGE-M3 Query Embedding
    │    ↓
    │  PostgreSQL + pgvector
    │    ↓
    │  owner_user_id 필터
    │    ↓
    │  Top-K 문서 반환
    │
    ├─ web_search
    ├─ external_or_realtime
    ├─ user_context
    └─ not_rag_or_restricted
```

현재 PrompTune 자체 테스트셋 기준 최종 결과:

```text
테스트 문서                18개
문서 Chunk                 36개
Embedding 차원             1024
전체 테스트 질문           60개
internal_rag 질문          54개
negative/routing 질문       6개

Top-1 Retrieval            52 / 54 = 96.30%
Top-3 Retrieval            54 / 54 = 100.00%
Routing                    6 / 6 PASS
owner_user_id 격리         PASS
FastAPI 실제 E2E           PASS
```

> 정확한 표현: **“현재 PrompTune 자체 internal_rag 테스트셋 54문항 기준 Top-3 Retrieval Accuracy 100%”**  
> BGE-M3라는 모델 자체의 일반 성능이 100%라는 의미는 아니다.

---

# 1. RAG와 BGE-M3의 역할

## RAG란?

RAG(Retrieval-Augmented Generation)는 생성 모델이 바로 답을 만들기 전에, 관련 문서나 근거를 먼저 검색한 뒤 그 정보를 생성 단계에 전달하는 구조다.

PrompTune에서는 다음과 같이 사용한다.

```text
사용자 질문
↓
내부 문서 검색
↓
관련 문서 Top-K
↓
생성 모델에 근거로 전달
↓
최종 답변 생성
```

즉 BGE-M3는 RAG 전체가 아니라 **RAG 안의 검색/Retrieval 단계에서 텍스트를 Vector로 변환하는 Embedding 모델**이다.

## 이번 구현에서 BGE-M3가 한 일

```text
문서 Chunk
↓
BGE-M3
↓
1024차원 Dense Vector

사용자 질문
↓
BGE-M3
↓
1024차원 Dense Vector

질문 Vector ↔ 문서 Vector
↓
Cosine Similarity
↓
가장 가까운 문서 Top-K
```

이번 범위에서는 BGE-M3의 기능 중:

```text
Dense Vector   사용
Sparse Vector  미사용
ColBERT        미사용
```

으로 구현했다.

---

# 2. DB Schema와 RAG 코드의 역할 차이

DB Schema는 데이터베이스의 구조를 정의한다.

현재 RAG에서 사용하는 핵심 구조는 다음과 같다.

```text
documents
- id
- owner_user_id
- title
- tag
- s3_key
- file_type

document_chunks
- id
- document_id
- chunk_index
- content
- embedding vector(1024)
- created_at
```

관계:

```text
documents 1
    ↓
document_chunks N
```

즉 하나의 문서를 여러 검색용 Chunk로 나누고, Embedding은 `document_chunks.embedding`에 저장한다.

### 역할 분리

```text
DB 담당
→ documents / document_chunks 구조와 관계 정의

Retrieval 작업
→ 문서 준비
→ Chunking
→ BGE-M3 Embedding
→ Vector DB 저장
→ pgvector 검색
→ Retrieval 평가
→ 사용자 격리
→ API 연결
```

### company_id 관련 변경

초기 테스트 JSON에는 `company_id` 필드가 남아 있었지만, 최종 DB 검색 구조에서는 회사 공유 문서 기능을 제외하면서 `company_id`를 사용하지 않는다.

현재 실제 검색 격리 기준:

```text
owner_user_id
```

DB 적재 시 테스트 JSON의 `company_id`는 검색 필터로 사용하지 않았고, 개인 문서는 `documents.owner_user_id`로 분리했다.

---

# 3. 전체 BGE-M3 RAG 15단계

| 단계 | 작업 | 목적 | 최종 결과 |
|---|---|---|---|
| 1 | 테스트 문서 작성 | 내부 문서 검색용 데이터 구성 | 18개 |
| 2 | 테스트 질문 작성 | 검색/라우팅 평가셋 구성 | 60개 |
| 3 | Chunking | 검색 가능한 의미 단위로 분리 | 18 docs → 36 chunks |
| 4 | BGE-M3 Embedding | Dense Vector 생성 | 36 × 1024 |
| 5 | NumPy Cosine 검색 | DB 연결 전 baseline 검증 | 수동 4개 PASS |
| 6 | DB Schema 연결 | documents/document_chunks 구조 사용 | 완료 |
| 7 | documents DB 적재 | 테스트 문서를 사용자 소유 문서로 저장 | owner_user_id=2 |
| 8 | chunks/embedding 적재 | pgvector 검색 데이터 준비 | 36개 저장 |
| 9 | DB 무결성 검증 | 개수/NULL/차원 확인 | NULL 0, dim 1024 |
| 10 | pgvector Top-3 구현 | PostgreSQL Vector 검색 전환 | 완료 |
| 11 | NumPy vs pgvector 비교 | 저장소 전환 후 검색 동일성 검증 | 4/4 PASS |
| 12 | 사용자 격리 | 타 사용자 문서 노출 방지 | PASS |
| 13 | 54문항 자동평가 | Retrieval 정량 평가 | Top-1 96.30%, Top-3 100% |
| 14 | Routing 평가 | RAG가 아닌 질문 분리 | 6/6 PASS |
| 15 | FastAPI E2E | 실제 서비스 경로 검증 | PASS |

---

# 4. 1~5단계: DB 연결 전 모델 기능 검증

## 4.1 테스트 문서 18개

파일:

```text
ai-service/app/data/rag/rag_test_documents.json
```

업무 규정과 지침을 가정한 테스트 문서 18개를 구성했다.

대표 문서:

```text
DOC001 → 휴가 및 연차 사용 규정
DOC002 → 경비 처리 지침
DOC004 → 병가 및 질병휴직 규정
DOC007 → 출장 및 출장비 정산 규정
DOC011 → 회의록 작성 및 공유 기준
DOC012 → 주간업무보고 작성 기준
```

이 데이터는 실제 회사 기밀 문서가 아니라 RAG 검색 기능을 검증하기 위한 테스트 문서다.

---

## 4.2 테스트 질문 60개

파일:

```text
ai-service/app/data/rag/rag_test_queries.json
```

구성:

```text
internal_rag             54개
negative/routing          6개
합계                      60개
```

`internal_rag` 질문은 정답 문서 `expected_doc_id`를 지정했다.

예:

```text
Q001
질문: 연차 사용 규정 알려줘
expected_doc_id: DOC001
expected_route: internal_rag
```

negative/routing 질문은 검색 정확도와 분리해서 평가했다.

---

## 4.3 Chunking

파일:

```text
ai-service/app/services/retrieval/chunker.py
```

목표:

```text
최소 약 300자
목표 약 400자
최대 약 500자
```

문장을 단순히 일정 글자 수에서 자르지 않고 문장 경계를 최대한 고려해 분리했다.

결과:

```text
18 documents
↓
36 chunks
```

왜 Chunking을 했는가?

문서 전체를 하나의 Vector로 만들면 문서 안의 여러 주제가 한 Vector에 섞일 수 있다. 검색 단위를 Chunk로 나누면 질문과 직접 관련된 구간을 더 세밀하게 찾을 수 있고, 생성 모델에도 필요한 부분만 전달할 수 있다.

---

## 4.4 BGE-M3 Dense Embedding

파일:

```text
ai-service/app/services/retrieval/bge_m3.py
```

사용 모델:

```text
BAAI/bge-m3
```

코드 설정:

```text
return_dense=True
return_sparse=False
return_colbert_vecs=False
```

검증 결과:

```text
shape=(36, 1024)
dtype=float32
norm(min/avg/max)=1.000000/1.000000/1.000000
```

저장:

```text
ai-service/app/data/rag/rag_test_embeddings.npy
```

즉 36개 Chunk 각각을 1024차원 Dense Vector로 변환했다.

---

## 4.5 DB 이전 NumPy Cosine Baseline

파일:

```text
ai-service/app/services/retrieval/test_retrieval.py
```

DB를 연결하기 전에 검색 모델과 유사도 계산 로직 자체가 정상인지 분리해서 확인했다.

```text
질문
↓
BGE-M3 Query Embedding
↓
기존 Chunk Embedding과 Cosine Similarity
↓
점수 내림차순
↓
Top-3
```

수동 검증 4문항:

| 질문 | 기대 문서 | Top-1 | Top-3 |
|---|---|---|---|
| 연차 사용 규정 알려줘 | DOC001 | PASS | PASS |
| 경비 처리 절차 알려줘 | DOC002 | PASS | PASS |
| 회의록은 어떻게 작성해야 해? | DOC011 | PASS | PASS |
| 병가 신청 기준 알려줘 | DOC004 | PASS | PASS |

이 시점의 4/4는 **기능 Smoke Test**이며 전체 성능 수치로 사용하지 않았다.

---

# 5. 6~9단계: PostgreSQL / pgvector 적재

## 5.1 DB 연결

사용 구조:

```text
documents
↓
document_chunks
↓
embedding vector(1024)
```

테스트 문서 소유자:

```text
owner_user_id = 2
```

테스트 데이터 구분:

```text
tag = BGE_M3_TEST
```

---

## 5.2 DB 적재

파일:

```text
ai-service/app/services/retrieval/import_rag_test_to_db.py
```

적재 결과:

```text
test documents     18
test chunks        36
embedding NULL      0
embedding dim    1024
```

기존 DB seed 문서를 지우지 않고 `BGE_M3_TEST` 테스트 데이터만 별도로 적재했다.

---

## 5.3 DB 무결성 검증

검증 항목:

```text
documents 개수
document_chunks 개수
embedding NULL 여부
vector dimension
owner_user_id
```

최종 결과:

```text
36 test chunks
NULL embedding = 0
min_dim = 1024
max_dim = 1024
owner_user_id = 2
```

---

# 6. 오늘 완료한 10~15단계 상세 결과

# 6.1 10단계 — pgvector Top-3 구현

파일:

```text
ai-service/app/services/retrieval/test_pgvector_retrieval.py
```

PostgreSQL pgvector의 cosine distance 연산을 이용했다.

개념:

```text
cosine distance = embedding <=> query_vector

similarity score
= 1 - cosine distance
```

검색 시 반드시:

```text
WHERE documents.owner_user_id = 요청 사용자
```

조건을 적용했다.

---

# 6.2 11단계 — NumPy vs pgvector 동일성 검증

같은 질문과 같은 Embedding을 사용해서 기존 NumPy 검색과 pgvector 검색의 순위와 점수를 비교했다.

| 질문 | NumPy Top-1 score | pgvector Top-1 score | 결과 |
|---|---:|---:|---|
| 연차 사용 규정 알려줘 | 0.700220 | 0.700220 | PASS |
| 경비 처리 절차 알려줘 | 0.716175 | 0.716175 | PASS |
| 회의록은 어떻게 작성해야 해? | 0.689778 | 0.689778 | PASS |
| 병가 신청 기준 알려줘 | 0.678961 | 0.678961 | PASS |

회의록 Top-2는 출력 자릿수 기준:

```text
NumPy    0.640070
pgvector 0.640071
```

정도로 아주 작은 부동소수점 차이가 있었지만 검색 순위와 판정에는 영향을 주지 않았다.

### 왜 이 검증이 중요한가?

DB로 옮긴 뒤 검색 결과가 나빠졌다면 원인이 모델인지 DB Vector 저장인지 검색 수식인지 구분하기 어렵다.

그래서:

```text
NumPy baseline
↓
pgvector
↓
동일 질문/동일 결과 비교
```

로 전환 전후 parity를 확인했다.

---

# 6.3 12단계 — owner_user_id 사용자 격리

테스트 문서:

```text
owner_user_id=2
```

검색:

```text
owner_user_id=2
→ 본인 BGE_M3_TEST 문서 검색 성공

owner_user_id=1
→ 검색 결과 없음
```

즉 타 사용자의 개인 문서가 검색 후보에 들어가지 않는 것을 확인했다.

이 단계는 정확도보다 **데이터 격리와 보안 관점**에서 중요하다.

---

# 6.4 13단계 — internal_rag 54문항 자동평가

파일:

```text
ai-service/app/services/retrieval/evaluate_internal_rag.py
```

질문마다 모델을 새로 로드하면 비효율적이므로 BGE-M3를 한 번 로드하고 54개 질문을 Batch Embedding했다.

결과:

```text
전체 질문       54
Top-1 정답      52 / 54
Top-1 Accuracy  96.30%

Top-3 정답      54 / 54
Top-3 Accuracy  100.00%

Top-1 실패       2
```

## Top-1 실패 사례

### Q027

질문:

```text
개인카드로 먼저 산 업무용 장비도 회사 비용 처리할 수 있어?
```

기대 문서:

```text
비품 구매 및 비용 신청 규정
```

실제 Top-1:

```text
법인카드 사용 지침
```

해석:

`개인카드`, `비용`, `구매`와 같은 의미가 카드/비용 규정 양쪽에 겹쳐 semantic overlap이 발생한 것으로 볼 수 있다.

정답 문서는 Top-3 안에는 포함됐다.

### Q053

질문:

```text
근속연수만 채우면 자동으로 승진하는 거야?
```

기대 문서:

```text
성과평가 및 승진 기준
```

실제 Top-1:

```text
출퇴근 및 근태 관리 규정
```

해석:

`근속`, `근무` 계열 표현이 근태 문서와 의미적으로 가까워 Top-1에서 혼동한 사례다.

이 역시 정답 문서는 Top-3 안에 포함됐다.

---

# 6.5 Top-1과 Top-3를 같이 본 이유

Top-1:

```text
검색 결과 1위가 바로 정답인가?
```

Top-3:

```text
상위 3개 근거 안에 정답 문서가 들어오는가?
```

RAG에서는 생성 모델에 Top-K 근거를 같이 전달하는 경우가 많기 때문에 Top-1뿐 아니라 Top-3도 중요하다.

이번 결과:

```text
Top-1 = 96.30%
Top-3 = 100.00%
```

즉 두 개의 Top-1 혼동 사례에서도 정답 근거는 Top-3 안에 존재했다.

---

# 6.6 14단계 — negative / routing 평가

파일:

```text
ai-service/app/services/retrieval/retrieval_router.py
ai-service/app/services/retrieval/evaluate_routing.py
```

검색 모델은 질문을 받으면 DB 안에서 무조건 가장 가까운 문서를 찾으려고 한다.

따라서 날씨나 주가 같은 질문은 BGE-M3의 검색 정확도로 평가하는 것이 아니라 **애초에 internal_rag로 보내지 않는 것**이 중요하다.

평가 데이터:

| ID | 질문 | 기대 Route |
|---|---|---|
| Q055 | 오늘 서울 날씨 알려줘 | external_or_realtime |
| Q056 | 2026년 최신 AI 뉴스 알려줘 | web_search |
| Q057 | 현재 삼성전자 주가 얼마야? | external_or_realtime |
| Q058 | 내일 원달러 환율이 어떻게 돼? | external_or_realtime |
| Q059 | 내 캘린더에 내일 회의 몇 개 있어? | user_context |
| Q060 | 김대리 개인 휴대폰 번호 알려줘 | not_rag_or_restricted |

결과:

```text
6 / 6 PASS
Accuracy = 100.00%
```

주의:

이 수치는 **초기 규칙 기반 Router의 6개 테스트 케이스 결과**다. 일반적인 Routing 모델 성능이 100%라는 의미로 사용하면 안 된다.

---

# 6.7 15단계 — FastAPI 실제 E2E

기존 `/api/ai/retrieve`는 `pipeline_mock.py`의 샘플 문서를 반환하고 있었다.

최종적으로 real/mock retrieval 스위치를 추가했다.

```text
USE_REAL_RETRIEVAL=false
→ 기존 mock

USE_REAL_RETRIEVAL=true
→ 실제 BGE-M3 + pgvector
```

실제 흐름:

```text
POST /api/ai/retrieve
↓
RetrieveRequest
- query
- owner_user_id
- top_k
↓
BGE-M3 Query Embedding
↓
PostgreSQL 연결
↓
pgvector cosine search
↓
owner_user_id SQL filter
↓
RetrieveResponse
↓
Top-K Document JSON
```

실제 테스트:

```text
query = "연차 사용 규정 알려줘"
owner_user_id = 2
top_k = 3
```

Top-1:

```text
휴가 및 연차 사용 규정
score = 0.700220224...
```

이는 기존 NumPy와 pgvector 단독 테스트의:

```text
0.700220
```

결과와 동일하게 재현됐다.

격리 테스트:

```text
owner_user_id = 1
```

응답:

```json
{"documents":[]}
```

따라서 Mock 함수가 아니라 실제 FastAPI Endpoint에서:

```text
BGE-M3
→ Query Embedding
→ PostgreSQL
→ pgvector
→ 사용자 필터
→ JSON 반환
```

까지 End-to-End로 확인했다.

---

# 7. 최종 파일 구조

```text
ai-service/
├── requirements.txt
└── app/
    ├── data/
    │   └── rag/
    │       ├── rag_test_documents.json
    │       ├── rag_test_queries.json
    │       ├── rag_test_chunks.json
    │       ├── rag_test_embeddings.npy
    │       └── rag_pgvector_eval_results.json
    │
    ├── routers/
    │   └── pipeline.py
    │
    ├── schemas/
    │   └── models.py
    │
    └── services/
        └── retrieval/
            ├── __init__.py
            ├── chunker.py
            ├── bge_m3.py
            ├── test_retrieval.py
            ├── import_rag_test_to_db.py
            ├── test_pgvector_retrieval.py
            ├── evaluate_internal_rag.py
            ├── retrieval_router.py
            ├── evaluate_routing.py
            └── rag_retriever.py
```

관련 공용 파일:

```text
docker-compose.yml
ai-service/requirements.txt
ai-service/app/main.py
ai-service/app/routers/pipeline.py
ai-service/app/schemas/models.py
```

---

# 8. 모델 테스트를 이렇게 나눈 이유

이번 테스트는 한 번에 E2E만 실행하지 않고 계층적으로 검증했다.

## Layer 1 — Embedding 자체 검증

확인:

```text
shape
dtype
dimension
norm
NaN / inf
```

목적:

BGE-M3 출력 자체가 정상인지 확인.

---

## Layer 2 — Retrieval 로직 검증

```text
NumPy Cosine Similarity
```

목적:

DB와 무관하게 질문 Embedding과 Chunk Embedding의 검색 로직이 맞는지 확인.

---

## Layer 3 — Storage/Search Engine 전환 검증

```text
NumPy
vs
PostgreSQL pgvector
```

목적:

DB 저장 및 pgvector 전환 후에도 동일한 순위와 점수가 재현되는지 확인.

---

## Layer 4 — 전체 데이터셋 평가

```text
54 internal_rag 질문
```

목적:

몇 개의 예시가 아니라 전체 Retrieval 테스트셋에서 Top-1/Top-3를 계산.

---

## Layer 5 — Routing 검증

```text
6 negative questions
```

목적:

RAG로 보내면 안 되는 질문을 검색 모델의 성능과 분리해서 검증.

---

## Layer 6 — Security / Isolation

```text
owner_user_id
```

목적:

검색 정확도가 높더라도 다른 사용자의 문서가 노출되면 서비스로 사용할 수 없기 때문에 사용자별 검색 범위를 검증.

---

## Layer 7 — API E2E

```text
FastAPI
→ BGE-M3
→ PostgreSQL
→ pgvector
→ Response
```

목적:

개별 함수 테스트가 아니라 실제 서비스 Endpoint에서 전체 흐름이 동작하는지 확인.

---

# 9. 왜 BGE-M3를 선택했는가?

PrompTune은 한국어 업무 문서를 의미 기반으로 검색해야 한다.

BGE-M3는 다국어 텍스트 Retrieval에 사용할 수 있는 Embedding 모델이고 Dense, Sparse, Multi-vector Retrieval 방식을 지원한다.

이번 프로젝트에서는 구현 복잡도와 초기 검증 범위를 고려해 **Dense Retrieval만 우선 사용**했다.

면접 답변 예시:

> “PrompTune은 한국어 업무 문서를 의미 기반으로 검색해야 했기 때문에 다국어 Retrieval에 사용할 수 있는 BGE-M3를 선택했습니다. 이번 구현에서는 Dense 1024차원 Embedding만 사용했고, Sparse와 Multi-vector Retrieval은 후속 개선 범위로 남겼습니다.”

---

# 10. 왜 pgvector를 사용했는가?

PrompTune의 문서 메타데이터는 PostgreSQL에 저장된다.

Embedding도 PostgreSQL의 `document_chunks`와 함께 관리하면:

```text
문서 Metadata
+
Chunk Content
+
Embedding
+
owner_user_id
```

를 하나의 검색 쿼리 안에서 연결할 수 있다.

특히:

```sql
WHERE d.owner_user_id = ...
```

조건과 Vector Similarity 검색을 같은 DB Query 안에서 적용할 수 있다는 점이 사용자 문서 격리에 유리했다.

---

# 11. 현재 구현의 한계와 개선 방향

현재 결과가 좋더라도 다음 한계가 있다.

## 11.1 테스트셋 크기

현재:

```text
18 documents
54 internal_rag queries
6 routing queries
```

소규모 자체 테스트셋이다.

따라서 Top-3 100%를 일반적인 BGE-M3 성능으로 해석하면 안 된다.

---

## 11.2 Dense Retrieval만 사용

현재:

```text
Dense only
```

향후:

```text
Dense + Sparse Hybrid
Multi-vector
```

를 비교할 수 있다.

---

## 11.3 Reranker 미적용

Q027과 Q053처럼 의미가 비슷한 문서끼리 Top-1 순서가 바뀌는 문제가 있었다.

향후:

```text
BGE-M3 Retrieval
↓
Top-K Candidate
↓
Reranker
↓
Final Top-K
```

구조로 개선할 수 있다.

---

## 11.4 Hard Negative 데이터

현재 실패 사례처럼 헷갈리는 문서쌍을 평가셋에 더 추가하면 실제 Retrieval 품질을 더 엄격하게 검증할 수 있다.

예:

```text
법인카드 사용 지침
vs
비품 구매 및 비용 신청 규정
```

---

## 11.5 Vector Index

현재 테스트 데이터는 36 chunks라 전체 Vector Scan으로도 충분하다.

실제 문서 수가 커지면:

```text
HNSW
또는
IVFFlat
```

등 ANN Index를 검토해야 한다.

---

## 11.6 인증된 사용자 ID

현재 검색 함수는 `owner_user_id`를 기준으로 격리한다.

운영 환경에서는 클라이언트가 임의로 `owner_user_id`를 보내는 구조보다:

```text
로그인 사용자 인증
↓
Backend가 user id 결정
↓
AI Service에 전달
```

방식으로 강제해야 한다.

이 부분은 보안상 중요한 후속 작업이다.

---

## 11.7 첫 모델 로딩 시간

실제 E2E 첫 호출에서는 컨테이너 내부에서 BGE-M3 모델을 처음 로드하므로 시간이 오래 걸렸다.

이를 줄이기 위해:

```text
model warm-up
persistent Hugging Face cache
model singleton/cache
```

방식을 사용할 수 있다.

현재 `rag_retriever.py`에서는 모델 객체를 프로세스당 재사용하도록 캐시한다.

---

# 12. 면접에서 모델 테스트 방법 설명

## 12.1 “모델을 어떻게 테스트했나요?”

답변:

> “먼저 모델 출력 자체가 정상인지 36개 Chunk Embedding의 shape, dtype, norm과 1024차원 여부를 확인했습니다. 그다음 DB를 붙이기 전에 NumPy cosine similarity로 검색 baseline을 만들고 4개 대표 질문을 검증했습니다. 이후 같은 Embedding을 PostgreSQL pgvector에 저장한 뒤 동일 질문을 다시 검색해 순위와 점수가 재현되는지 확인했습니다. 그 후 54개의 internal RAG 질문을 Batch Embedding해서 Top-1과 Top-3 정확도를 계산했고, 검색 대상이 아닌 6개 질문은 Routing 평가로 분리했습니다. 마지막으로 owner_user_id 격리와 실제 FastAPI `/api/ai/retrieve` E2E까지 확인했습니다.”

---

## 12.2 “왜 NumPy 테스트를 먼저 했나요?”

답변:

> “처음부터 DB까지 붙이면 문제가 생겼을 때 Embedding 문제인지 Vector 저장 문제인지 검색 SQL 문제인지 구분하기 어렵습니다. 그래서 NumPy cosine을 baseline으로 먼저 검증하고, 그 결과와 pgvector 결과를 비교해 저장소 전환이 정확했는지를 확인했습니다.”

---

## 12.3 “Top-1 96.3%인데 Top-3가 100%인 이유는?”

답변:

> “54문항 중 두 질문에서 의미가 비슷한 다른 규정이 1위로 올라왔지만 정답 문서는 모두 Top-3 안에 있었습니다. 실제 RAG에서는 여러 개의 검색 근거를 생성 모델에 전달할 수 있기 때문에 Top-3도 함께 평가했습니다.”

---

## 12.4 “실패 케이스를 어떻게 봤나요?”

답변:

> “Q027은 비품 구매와 법인카드 문서가 비용·카드라는 의미를 공유했고, Q053은 승진 질문의 근속 표현이 근태 문서와 가까워지는 semantic overlap이 있었습니다. 단순히 실패를 제거하지 않고, reranker와 hard negative 평가가 필요한 근거로 남겼습니다.”

---

## 12.5 “사용자 문서 보안은 어떻게 처리했나요?”

답변:

> “Vector 검색 SQL에서 documents.owner_user_id 조건을 함께 적용했습니다. 테스트 문서가 owner 2일 때 owner 1로 동일한 검색을 수행하면 결과가 0건이었고, 실제 `/api/ai/retrieve` API에서도 `{"documents":[]}`를 확인했습니다. 다만 운영에서는 owner_user_id를 클라이언트가 임의로 지정하지 못하도록 인증된 Backend 사용자 ID를 전달해야 합니다.”

---

# 13. 30초 설명

> “PrompTune에서 개인 내부 문서를 검색하는 RAG Retrieval을 담당했습니다. 테스트 문서 18개를 36개 Chunk로 나누고 BGE-M3로 1024차원 Dense Embedding을 생성했습니다. 먼저 NumPy cosine으로 baseline을 검증한 뒤 PostgreSQL pgvector로 전환했고, 같은 4개 질문에서 순위와 점수가 동일하게 재현되는 것을 확인했습니다. 전체 54개 internal RAG 질문에서는 Top-1 96.30%, Top-3 100%였고, owner_user_id 기반 사용자 격리와 FastAPI 실제 E2E까지 검증했습니다.”

---

# 14. 1분 설명

> “제가 맡은 부분은 PrompTune의 내부 문서 Retrieval입니다. 먼저 업무 규정 형태의 테스트 문서 18개와 질문 60개를 만들었습니다. 문서는 약 300~500자를 목표로 36개 Chunk로 분리했고, BGE-M3 Dense Embedding을 사용해 1024차원 Vector를 생성했습니다. DB 연결 전에 NumPy cosine similarity로 검색 기능을 먼저 검증해 문제 구간을 분리했고, 이후 documents와 document_chunks에 데이터를 저장해 PostgreSQL pgvector 검색으로 교체했습니다. 동일한 대표 4문항에서 NumPy와 pgvector의 Top-1 점수가 동일하게 재현됐고, 54개의 internal_rag 질문 전체 평가에서는 Top-1 96.30%, Top-3 100%였습니다. 두 개의 Top-1 실패는 비슷한 규정 간 semantic overlap 사례였고 정답은 모두 Top-3에 있었습니다. 마지막으로 owner_user_id로 개인 문서를 격리하고 실제 FastAPI `/api/ai/retrieve`에서 BGE-M3 → pgvector → Top-3 JSON 응답까지 E2E로 검증했습니다.”

---

# 15. 재현용 주요 명령

## Embedding 생성

```bash
python ai-service/app/services/retrieval/bge_m3.py \
  --input ai-service/app/data/rag/rag_test_chunks.json \
  --output ai-service/app/data/rag/rag_test_embeddings.npy
```

## NumPy Retrieval

```bash
python ai-service/app/services/retrieval/test_retrieval.py \
  --query "연차 사용 규정 알려줘" \
  --expected-doc-id DOC001
```

## pgvector Retrieval

```bash
python ai-service/app/services/retrieval/test_pgvector_retrieval.py \
  --query "연차 사용 규정 알려줘" \
  --owner-user-id 2 \
  --expected-title "휴가 및 연차 사용 규정"
```

## 54개 Retrieval 자동평가

```bash
python ai-service/app/services/retrieval/evaluate_internal_rag.py
```

## Routing 평가

```bash
python ai-service/app/services/retrieval/evaluate_routing.py
```

## 실제 RAG API 모드

```bash
USE_REAL_RETRIEVAL=true docker compose up -d --build ai-service
```

## 실제 E2E

```bash
curl -X POST \
  http://localhost:8000/api/ai/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "연차 사용 규정 알려줘",
    "owner_user_id": 2,
    "top_k": 3
  }'
```

사용자 격리:

```bash
curl -X POST \
  http://localhost:8000/api/ai/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "연차 사용 규정 알려줘",
    "owner_user_id": 1,
    "top_k": 3
  }'
```

기대:

```json
{"documents":[]}
```

---

# 16. 팀 공유 시 핵심 포인트

팀원에게는 다음 네 가지를 우선 공유하면 된다.

1. **RAG Retrieval 전체 1~15단계 완료**
2. **PrompTune 자체 테스트셋 기준 Top-1 96.30%, Top-3 100%**
3. **owner_user_id 기반 개인 문서 격리 및 실제 API E2E 검증 완료**
4. **현재 한계는 dense-only, 소규모 자체 테스트셋, reranker/ANN 미적용이며 후속 개선 가능**

---

# 17. 외부 기술 참고

- BGE-M3 paper: https://arxiv.org/abs/2402.03216
- BAAI/bge-m3 model card: https://huggingface.co/BAAI/bge-m3
- FlagEmbedding: https://github.com/FlagOpen/FlagEmbedding
- pgvector: https://github.com/pgvector/pgvector

---

# 18. 최종 한 줄 요약

**PrompTune 내부 문서 검색을 위해 BGE-M3 Dense Embedding → PostgreSQL pgvector → owner_user_id 기반 개인 문서 격리 → Top-K Retrieval → FastAPI E2E까지 구현했고, 자체 internal_rag 54문항 기준 Top-1 96.30%, Top-3 100%를 확인했다.**
