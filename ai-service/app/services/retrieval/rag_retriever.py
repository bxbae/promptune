from __future__ import annotations

import os
import re
import unicodedata
from functools import lru_cache

import numpy as np
import psycopg
import torch

from app.schemas.models import Document, RetrieveRequest, RetrieveResponse
from app.services.retrieval.retrieval_rule import apply_retrieval_rule


MODEL_NAME = os.getenv("BGE_M3_MODEL", "BAAI/bge-m3")
EXPECTED_DIM = 1024


# 2026-09-02(RAG observability): Internal RAG는 web 검색과 달리 로그가
# 전혀 없어서, "잘못된 chunk가 검색됐는지" vs "올바른 chunk가 검색됐는데
# HCX가 무시했는지" vs "chunk 자체가 잘못 잘렸는지"를 구분할 방법이
# 없었다. 이 helper는 로그 출력 전용 - 원본 Document 객체는 절대
# 건드리지 않고, 로그에 필요한 필드만 뽑아 새 dict 리스트(immutable
# summary)를 만든다. preview_limit=0이면 preview 자체를 안 만든다
# (retrieval_orchestrator.py의 final_documents 로그처럼, raw/selected
# 로그에 이미 preview가 있어서 중복인 경우).
def document_log_summary(
    documents: list[Document],
    *,
    title_limit: int = 80,
    preview_limit: int = 0,
) -> list[dict]:
    summaries: list[dict] = []

    for document in documents:
        title = str(document.title or "")

        if len(title) > title_limit:
            title = title[:title_limit] + "..."

        item = {
            "document_id": document.document_id,
            "chunk_id": document.chunk_id,
            "chunk_index": document.chunk_index,
            "score": round(float(document.score or 0.0), 3),
            "title": title,
        }

        if preview_limit > 0:
            item["preview"] = str(document.content or "")[:preview_limit]

        summaries.append(item)

    return summaries


def bge_runtime_config() -> dict[str, object]:
    requested_device = os.getenv("BGE_M3_DEVICE", "auto").strip().lower()

    if requested_device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = requested_device

    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError(
            f"BGE_M3_DEVICE={device} but CUDA is not available"
        )

    requested_fp16 = os.getenv("BGE_M3_USE_FP16", "auto").strip().lower()
    if requested_fp16 == "auto":
        use_fp16 = device.startswith("cuda")
    else:
        use_fp16 = requested_fp16 in {"1", "true", "yes", "on"}

    if use_fp16 and not device.startswith("cuda"):
        use_fp16 = False

    return {
        "requested_device": requested_device,
        "device": device,
        "use_fp16": use_fp16,
    }


@lru_cache(maxsize=1)
def get_model():
    # BGE/transformers/torch는 실제 embedding 요청이 들어올 때만 로드한다.
    # Router/unit test처럼 retrieval 모듈만 import하는 경로에서
    # 무거운 ML runtime import가 발생하지 않게 한다.
    from FlagEmbedding import BGEM3FlagModel
    config = bge_runtime_config()
    print(
        f"[RAG] loading model: {MODEL_NAME} "
        f"device={config['device']} use_fp16={config['use_fp16']}"
    )

    return BGEM3FlagModel(
        MODEL_NAME,
        use_fp16=bool(config["use_fp16"]),
        device=str(config["device"]),
    )


def encode_query(query: str) -> np.ndarray:
    model = get_model()

    output = model.encode(
        [query],
        batch_size=1,
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )

    vector = np.asarray(
        output["dense_vecs"][0],
        dtype=np.float32,
    )

    if vector.shape != (EXPECTED_DIM,):
        raise RuntimeError(
            f"unexpected embedding shape: {vector.shape}"
        )

    return vector


def vector_literal(vector: np.ndarray) -> str:
    return "[" + ",".join(
        format(float(value), ".9g")
        for value in vector
    ) + "]"


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "promptune"),
        user=os.getenv("DB_USER", "promptune"),
        password=os.getenv("DB_PASSWORD", "promptune"),
        connect_timeout=5,
    )


def _normalized_document_ids(document_ids: list[int] | None) -> list[int]:
    result: list[int] = []

    for value in document_ids or []:
        try:
            document_id = int(value)
        except (TypeError, ValueError):
            continue

        if document_id > 0 and document_id not in result:
            result.append(document_id)

    return result[:20]


def retrieve_document_overview(
    owner_user_id: int,
    document_ids: list[int],
    *,
    max_total_chars: int = 9000,
) -> RetrieveResponse:
    """
    문서 전체 요약/변환 요청용.

    semantic Top-K를 사용하지 않고 확정된 document_id의 chunk를
    원래 순서대로 가져온다.

    여러 파일을 동시에 첨부한 경우 첫 번째 파일이 전체 context
    budget을 독점하지 않도록 문서별 예산을 동일하게 나눈다.
    """
    ids = _normalized_document_ids(document_ids)

    if not ids:
        return RetrieveResponse(documents=[])

    sql = """
SELECT
    d.id AS document_id,
    dc.id AS chunk_id,
    dc.chunk_index,
    d.title,
    d.document_type,
    d.description,
    dc.content
FROM documents d
JOIN document_chunks dc
    ON dc.document_id = d.id
WHERE d.owner_user_id = %s
  AND d.id = ANY(%s::bigint[])
ORDER BY d.id, dc.chunk_index
"""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (owner_user_id, ids)
            )
            rows = cur.fetchall()

    rows_by_document = {
        document_id: []
        for document_id in ids
    }

    for row in rows:
        rows_by_document.setdefault(
            int(row[0]),
            []
        ).append(row)

    documents = []

    per_document_budget = max(
        1,
        max_total_chars // len(ids)
    )

    for wanted_document_id in ids:

        used_for_document = 0

        for (
            document_id,
            chunk_id,
            chunk_index,
            title,
            document_type,
            description,
            content,
        ) in rows_by_document.get(
            wanted_document_id,
            []
        ):

            chunk_text = str(
                content or ""
            ).strip()

            if not chunk_text:
                continue

            remaining = (
                per_document_budget
                - used_for_document
            )

            if remaining <= 0:
                break

            if len(chunk_text) > remaining:
                chunk_text = chunk_text[:remaining]

            documents.append(
                Document(
                    document_id=int(document_id),
                    chunk_id=int(chunk_id),
                    chunk_index=int(chunk_index),
                    title=title,
                    document_type=(
                        document_type
                        or "OTHER"
                    ),
                    description=description,
                    content=chunk_text,
                    score=1.0,
                )
            )

            used_for_document += len(
                chunk_text
            )

    return RetrieveResponse(
        documents=documents
    )


_LEXICAL_STOP_WORDS = {
    "이거", "이걸", "그거", "그걸", "그것", "저거",
    "문서", "파일", "내용", "알려줘", "알려", "해줘", "에서", "으로",
    "해당", "아까", "전에", "올린", "무슨", "어떤", "요약",
}


def _query_tokens(query: str) -> list[str]:
    tokens = re.findall(r"[가-힣A-Za-z0-9_]{2,}", str(query or "").lower())
    return [token for token in tokens if token not in _LEXICAL_STOP_WORDS]


def retrieve_scoped_lexical(
    owner_user_id: int,
    document_ids: list[int],
    query: str,
    top_k: int,
) -> RetrieveResponse:
    """
    특정 document_id가 이미 확정됐지만 embedding이 없거나 BGE가 실패한 경우의
    안전 폴백. 전체 파일관리 검색에는 사용하지 않고 현재/이전 첨부 문서 안에서만
    단순 lexical relevance를 계산한다.
    """
    ids = _normalized_document_ids(document_ids)
    if not ids:
        return RetrieveResponse(documents=[])

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    d.id AS document_id,
                    dc.id AS chunk_id,
                    dc.chunk_index,
                    d.title,
                    d.document_type,
                    d.description,
                    dc.content
                FROM documents d
                JOIN document_chunks dc
                  ON dc.document_id = d.id
                WHERE d.owner_user_id = %s
                  AND d.id = ANY(%s::bigint[])
                ORDER BY d.id, dc.chunk_index
                """,
                (owner_user_id, ids),
            )
            rows = cur.fetchall()

    tokens = _query_tokens(query)
    scored: list[tuple[float, tuple]] = []

    for row in rows:
        document_id, chunk_id, chunk_index, title, document_type, description, content = row
        haystack = " ".join(
            str(value or "").lower()
            for value in (title, description, content)
        )

        if tokens:
            score = sum(haystack.count(token) for token in tokens)
        else:
            score = 0

        # 동점에서는 앞쪽 chunk를 조금 우선하되 relevance가 있으면 그게 절대 우선.
        rank_score = float(score) + (1.0 / (1000 + int(chunk_index or 0)))
        scored.append((rank_score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = scored[: max(1, min(top_k, 10))]

    documents = [
        Document(
            document_id=int(row[0]),
            chunk_id=int(row[1]),
            chunk_index=int(row[2]),
            title=row[3],
            document_type=row[4] or "OTHER",
            description=row[5],
            content=row[6],
            score=float(score),
        )
        for score, row in selected
    ]

    return RetrieveResponse(documents=documents)



_INTERNAL_QUERY_STOP_WORDS = {
    "우리회사",
    "우리",
    "회사",
    "사내",
    "내부",
    "내부문서",
    "문서함",
    "업로드한",
    "있는",
    "있어",
    "있나요",
    "알려줘",
    "알려주세요",
    "보여줘",
    "찾아줘",
    "해줘",
}


def _nfc_text(value) -> str:
    return unicodedata.normalize(
        "NFC",
        str(value or ""),
    )


def _metadata_query_tokens(query: str) -> list[str]:
    tokens = re.findall(
        r"[가-힣A-Za-z0-9_]{2,}",
        _nfc_text(query).lower(),
    )

    return [
        token
        for token in tokens
        if token not in _INTERNAL_QUERY_STOP_WORDS
    ]


def retrieve_document_catalog(
    owner_user_id: int,
    *,
    limit: int = 50,
) -> RetrieveResponse:
    """
    '내부문서에 뭐 있어?' 같은 catalog 요청.

    chunk embedding 검색을 하지 않고 사용자가 접근 가능한 documents
    metadata를 직접 조회한다.
    """
    sql = """
SELECT
    d.id,
    d.title,
    d.document_type,
    d.description
FROM documents d
WHERE d.owner_user_id = %s
ORDER BY d.id DESC
LIMIT %s
"""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    owner_user_id,
                    max(1, min(int(limit), 100)),
                ),
            )
            rows = cur.fetchall()

    documents = []

    for (
        document_id,
        title,
        document_type,
        description,
    ) in rows:
        metadata_text = (
            f"파일명: {title}\n"
            f"문서 유형: {document_type or 'OTHER'}"
        )

        if description:
            metadata_text += (
                f"\n설명: {description}"
            )

        documents.append(
            Document(
                document_id=int(document_id),
                chunk_id=None,
                chunk_index=None,
                title=str(title or ""),
                document_type=(
                    document_type or "OTHER"
                ),
                description=description,
                content=metadata_text,
                score=1.0,
            )
        )

    return RetrieveResponse(
        documents=documents
    )


def find_metadata_document_ids(
    owner_user_id: int,
    query: str,
    *,
    limit: int = 5,
) -> list[int]:
    """
    내부문서 lookup의 1단계.

    title / description / document_type metadata를 이용해 문서 후보를
    먼저 고른다. 이후 실제 내용 retrieval은 해당 document_id 안에서
    수행한다.
    """
    tokens = _metadata_query_tokens(query)

    if not tokens:
        return []

    sql = """
SELECT
    d.id,
    d.title,
    d.document_type,
    d.description
FROM documents d
WHERE d.owner_user_id = %s
ORDER BY d.id DESC
"""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (owner_user_id,),
            )
            rows = cur.fetchall()

    scored = []

    for (
        document_id,
        title,
        document_type,
        description,
    ) in rows:
        title_text = _nfc_text(title).lower()
        description_text = _nfc_text(
            description
        ).lower()
        type_text = _nfc_text(
            document_type
        ).lower()

        score = 0.0

        for token in tokens:
            if token in title_text:
                score += 4.0

            if token in description_text:
                score += 2.0

            if token in type_text:
                score += 1.5

        if score > 0:
            scored.append(
                (
                    score,
                    int(document_id),
                )
            )

    scored.sort(
        key=lambda item: (
            item[0],
            item[1],
        ),
        reverse=True,
    )

    return [
        document_id
        for _, document_id in scored[
            : max(1, min(limit, 10))
        ]
    ]

def retrieve(req: RetrieveRequest) -> RetrieveResponse:
    top_k = max(1, min(int(req.top_k), 10))
    document_ids = _normalized_document_ids(req.document_ids)

    # Retrieval Rule 적용 전에 후보를 넉넉히 가져온다.
    candidate_k = min(top_k * 3, 30)

    try:
        embedding = encode_query(req.query)
        vector = vector_literal(embedding)
    except Exception:
        if document_ids:
            print(
                "[RAG] fallback='scoped_lexical' "
                "reason='semantic_error'"
            )
            return retrieve_scoped_lexical(
                owner_user_id=req.owner_user_id,
                document_ids=document_ids,
                query=req.query,
                top_k=top_k,
            )
        raise

    document_filter = ""
    params: list[object] = [vector, req.owner_user_id]

    if document_ids:
        document_filter = " AND d.id = ANY(%s::bigint[])"
        params.append(document_ids)

    params.extend([vector, candidate_k])

    sql = f"""
SELECT
    d.id AS document_id,
    dc.id AS chunk_id,
    dc.chunk_index,
    d.title,
    d.document_type,
    d.description,
    dc.content,
    1 - (dc.embedding <=> %s::vector) AS score
FROM document_chunks dc
JOIN documents d
    ON d.id = dc.document_id
WHERE d.owner_user_id = %s
  {document_filter}
  AND dc.embedding IS NOT NULL
ORDER BY dc.embedding <=> %s::vector
LIMIT %s
"""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

    documents = [
        Document(
            document_id=int(document_id),
            chunk_id=int(chunk_id),
            chunk_index=int(chunk_index),
            title=title,
            document_type=document_type or "OTHER",
            description=description,
            content=content,
            score=float(score),
        )
        for (
            document_id,
            chunk_id,
            chunk_index,
            title,
            document_type,
            description,
            content,
            score,
        ) in rows
    ]

    # 순서 중요: apply_retrieval_rule()이 documents 변수를 덮어써서
    # 필터/정렬 전 RAW 후보가 이 시점 이후로는 사라진다 - 그래서 로그는
    # 여기서 즉시(순수 문자열 변환만) 남긴다. documents 리스트 자체는
    # 로그 때문에 복사/재정렬/수정하지 않는다.
    print(
        f"[RAG] semantic_raw count={len(documents)} "
        f"results={document_log_summary(documents, preview_limit=120)}"
    )

    documents = apply_retrieval_rule(
        documents,
        top_k=top_k,
        # 사용자가 특정 첨부문서를 명시한 순간 검색 공간은 이미 그 문서로
        # 확정됐다. 이때 0.50 threshold로 결과를 전부 버리면 "문서는 있는데
        # 내용을 못 읽는" 현상이 생기므로 scoped retrieval에서는 상위 chunk를
        # 점수와 무관하게 반환한다. 일반 파일관리 검색에만 threshold를 유지한다.
        min_score=(-1.0 if document_ids else 0.50),
        max_chunks_per_document=(top_k if document_ids else 2),
    )

    print(
        f"[RAG] semantic_selected count={len(documents)} "
        f"results={document_log_summary(documents, preview_limit=120)}"
    )

    if document_ids and not documents:
        print(
            "[RAG] fallback='scoped_lexical' "
            "reason='empty_after_retrieval_rule'"
        )
        return retrieve_scoped_lexical(
            owner_user_id=req.owner_user_id,
            document_ids=document_ids,
            query=req.query,
            top_k=top_k,
        )

    return RetrieveResponse(documents=documents)
