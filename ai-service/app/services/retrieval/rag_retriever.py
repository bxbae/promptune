from __future__ import annotations

import os
import re
from functools import lru_cache

import numpy as np
import psycopg
import torch
from FlagEmbedding import BGEM3FlagModel

from app.schemas.models import Document, RetrieveRequest, RetrieveResponse
from app.services.retrieval.retrieval_rule import apply_retrieval_rule


MODEL_NAME = os.getenv("BGE_M3_MODEL", "BAAI/bge-m3")
EXPECTED_DIM = 1024


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
def get_model() -> BGEM3FlagModel:
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

    if document_ids and not documents:
        return retrieve_scoped_lexical(
            owner_user_id=req.owner_user_id,
            document_ids=document_ids,
            query=req.query,
            top_k=top_k,
        )

    return RetrieveResponse(documents=documents)
