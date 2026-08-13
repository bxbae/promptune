from __future__ import annotations

import os
from functools import lru_cache

import numpy as np
import psycopg
from FlagEmbedding import BGEM3FlagModel

from app.schemas.models import Document, RetrieveRequest, RetrieveResponse


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


def retrieve(req: RetrieveRequest) -> RetrieveResponse:
    top_k = max(1, min(int(req.top_k), 10))

    embedding = encode_query(req.query)
    vector = vector_literal(embedding)

    sql = """
SELECT
    d.title,
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
                    top_k,
                ),
            )

            rows = cur.fetchall()

    documents = [
        Document(
            title=title,
            content=content,
            score=float(score),
        )
        for title, content, score in rows
    ]

    return RetrieveResponse(documents=documents)
