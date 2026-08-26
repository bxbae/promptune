from __future__ import annotations

import os
from functools import lru_cache

import numpy as np
import psycopg
from FlagEmbedding import BGEM3FlagModel

from app.schemas.models import Document, RetrieveRequest, RetrieveResponse
from app.services.retrieval.retrieval_rule import apply_retrieval_rule


MODEL_NAME = os.getenv("BGE_M3_MODEL", "BAAI/bge-m3")
EXPECTED_DIM = 1024


@lru_cache(maxsize=1)
def get_model() -> BGEM3FlagModel:
    print(f"[RAG] loading model: {MODEL_NAME}")

    return BGEM3FlagModel(
        MODEL_NAME,
        use_fp16=False,
        device="cpu",
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


def fetch_documents_by_id(
    document_ids: list[int],
    owner_user_id: int,
    *,
    max_chunks_per_document: int = 6,
) -> list[Document]:
    """
    2026-08-26: 사용자가 이 메시지에 직접 첨부한 문서는 query와의 의미
    유사도에 기대지 않고 내용을 그대로 가져온다. "DOCX 첨부하고 '이게 무슨
    내용이야?' 라고 물으면" 같은 질의는 문서 본문과 벡터상 유사도가 낮아서
    (질문 자체엔 문서 내용과 겹치는 단어가 없음) retrieve()의 유사도 검색 +
    min_score=0.50 필터를 그대로 쓰면 걸러져 버림 - 그래서 여기선 점수
    기준 없이, chunk_index 순서대로(문서 앞부분부터) 그냥 가져온다.

    d.owner_user_id = %s AND d.id = ANY(%s)로 소유권을 반드시 같이 확인한다
    (다른 사람 문서 id를 끼워넣어도 무시되도록 - 파이프라인 다른 곳의
    "본인 소유 문서만 연결" 패턴과 동일).
    """
    if not document_ids:
        return []

    sql = """
SELECT
    d.id AS document_id,
    dc.id AS chunk_id,
    dc.chunk_index,
    d.title,
    d.document_type,
    d.description,
    dc.content
FROM document_chunks dc
JOIN documents d
    ON d.id = dc.document_id
WHERE d.owner_user_id = %s
  AND d.id = ANY(%s)
ORDER BY d.id, dc.chunk_index
"""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (owner_user_id, list(document_ids)))
            rows = cur.fetchall()

    document_counts: dict[int, int] = {}
    documents: list[Document] = []

    for (
        document_id,
        chunk_id,
        chunk_index,
        title,
        document_type,
        description,
        content,
    ) in rows:
        count = document_counts.get(document_id, 0)
        if count >= max_chunks_per_document:
            continue
        document_counts[document_id] = count + 1

        documents.append(
            Document(
                document_id=int(document_id),
                chunk_id=int(chunk_id),
                chunk_index=int(chunk_index),
                title=title,
                document_type=document_type or "OTHER",
                description=description,
                content=content,
                # 유사도 검색이 아니라 명시적으로 첨부된 문서라 score 자체가
                # 의미 없음 - 최고점(1.0)으로 채워서 apply_retrieval_rule의
                # min_score 필터에 걸리지 않게 함(retrieve()에서 이 경로를
                # 쓸 때는 min_score=0.0으로 호출하지만, 다른 경로에서 이
                # 함수를 재사용해도 안전하도록 방어적으로 1.0을 넣는다).
                score=1.0,
            )
        )

    return documents


def retrieve(req: RetrieveRequest) -> RetrieveResponse:
    top_k = max(1, min(int(req.top_k), 10))

    # 2026-08-26: 이 메시지에 직접 첨부된 문서가 있으면, 의미 유사도 검색을
    # 아예 타지 않고 그 문서들의 내용을 순서대로 가져온다 (위 함수 docstring
    # 참고). 첨부 문서가 있는데 검색 결과가 0건이면 "문서를 확인할 수 없다"는
    # 잘못된 답 대신, 뭐가 문제인지 알 수 있도록 여기선 그대로 빈 리스트를
    # 반환한다 - 아직 임베딩이 안 끝난 직후 업로드일 가능성이 가장 크다.
    if req.document_ids:
        documents = fetch_documents_by_id(
            req.document_ids,
            req.owner_user_id,
            max_chunks_per_document=max(2, min(top_k * 2, 10)),
        )
        return RetrieveResponse(documents=documents[: max(top_k, 6)])

    # Retrieval Rule 적용 전에 후보를 넉넉히 가져온다.
    candidate_k = min(top_k * 3, 30)

    embedding = encode_query(req.query)
    vector = vector_literal(embedding)

    sql = """
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
  AND dc.embedding IS NOT NULL
ORDER BY dc.embedding <=> %s::vector
LIMIT %s
"""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    vector,
                    req.owner_user_id,
                    vector,
                    candidate_k,
                ),
            )

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
        min_score=0.50,
        max_chunks_per_document=2,
    )

    return RetrieveResponse(documents=documents)
