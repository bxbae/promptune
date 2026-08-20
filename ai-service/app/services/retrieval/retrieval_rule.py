from __future__ import annotations

from collections import defaultdict

from app.schemas.models import Document


# 문서 유형별 아주 작은 보정값.
# semantic similarity가 우선이고, document_type은 동점에 가까울 때만 영향을 준다.
DOCUMENT_TYPE_BOOST = {
    "POLICY": 0.030,
    "GUIDE": 0.015,
    "TEMPLATE": 0.010,
    "REPORT": 0.005,
    "OTHER": 0.000,
}


def adjusted_score(document: Document) -> float:
    """
    원래 cosine similarity에 document_type 보정값을 소폭 반영한다.
    검색 의미 유사도가 가장 중요한 기준이며 type은 보조 기준이다.
    """
    score = float(document.score or 0.0)
    boost = DOCUMENT_TYPE_BOOST.get(document.document_type or "OTHER", 0.0)

    return score + boost


def apply_retrieval_rule(
    documents: list[Document],
    *,
    top_k: int = 3,
    min_score: float = 0.50,
    max_chunks_per_document: int = 2,
) -> list[Document]:
    """
    pgvector 검색 결과에 후처리 Retrieval Rule을 적용한다.

    1. 최소 similarity 미만 결과 제거
    2. document_type soft boost를 적용해 정렬
    3. 하나의 document가 검색 결과를 독식하지 않도록 chunk 수 제한
    4. 최종 top_k 반환
    """

    if top_k <= 0:
        return []

    # 1. similarity threshold
    filtered = [
        document
        for document in documents
        if float(document.score or 0.0) >= min_score
    ]

    # 2. semantic score + 작은 document type boost
    ranked = sorted(
        filtered,
        key=adjusted_score,
        reverse=True,
    )

    # 3. 동일 document chunk 독식 방지
    document_counts: dict[int | None, int] = defaultdict(int)
    selected: list[Document] = []

    for document in ranked:
        document_id = document.document_id

        if (
            document_id is not None
            and document_counts[document_id] >= max_chunks_per_document
        ):
            continue

        selected.append(document)

        if document_id is not None:
            document_counts[document_id] += 1

        if len(selected) >= top_k:
            break

    return selected
