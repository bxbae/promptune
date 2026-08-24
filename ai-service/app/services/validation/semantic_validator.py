from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.services.retrieval.rag_retriever import get_model


@dataclass
class SemanticValidationResult:
    semantic_ok: bool
    score: float
    issues: list[str] = field(default_factory=list)


def calculate_similarities(
    reference: str,
    candidates: list[str],
) -> list[float]:
    """
    하나의 기준 문장(reference)과 여러 후보 문장의
    BGE-M3 cosine similarity를 한 번의 batch inference로 계산한다.

    기존 RAG의 get_model()을 재사용하므로
    BGE-M3 모델은 프로세스당 한 번만 로딩된다.
    """

    if not candidates:
        return []

    model = get_model()

    texts = [
        reference,
        *candidates,
    ]

    output = model.encode(
        texts,
        batch_size=len(texts),
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )

    embeddings = np.asarray(
        output["dense_vecs"],
        dtype=np.float32,
    )

    expected_shape = (
        len(texts),
        1024,
    )

    if embeddings.shape != expected_shape:
        raise RuntimeError(
            "unexpected BGE-M3 embedding shape: "
            f"{embeddings.shape}"
        )

    reference_vector = embeddings[0]
    candidate_vectors = embeddings[1:]

    reference_norm = float(
        np.linalg.norm(reference_vector)
    )

    candidate_norms = np.linalg.norm(
        candidate_vectors,
        axis=1,
    )

    if reference_norm == 0.0:
        raise RuntimeError(
            "BGE-M3 returned a zero-length reference vector."
        )

    if np.any(candidate_norms == 0.0):
        raise RuntimeError(
            "BGE-M3 returned a zero-length candidate vector."
        )

    similarities = (
        candidate_vectors @ reference_vector
    ) / (
        candidate_norms * reference_norm
    )

    return [
        float(score)
        for score in similarities
    ]


def _calculate_similarity(
    original: str,
    generated: str,
) -> float:
    """
    BGE-M3 dense embedding을 사용해
    원본 요청과 생성 응답의 cosine similarity를 계산한다.

    단일 비교도 calculate_similarities()를 재사용해
    임베딩/정규화 계산 로직을 한 곳에서 관리한다.
    """
    scores = calculate_similarities(
        reference=original,
        candidates=[generated],
    )

    if not scores:
        raise RuntimeError(
            "BGE-M3 similarity could not be calculated."
        )

    return scores[0]


def validate_semantic(
    original: str,
    generated: str,
    threshold: float,
) -> SemanticValidationResult:
    if not original.strip():
        return SemanticValidationResult(
            semantic_ok=False,
            score=0.0,
            issues=["원본 요청이 비어 있습니다."],
        )

    if not generated.strip():
        return SemanticValidationResult(
            semantic_ok=False,
            score=0.0,
            issues=["생성 응답이 비어 있습니다."],
        )

    score = _calculate_similarity(
        original=original,
        generated=generated,
    )

    semantic_ok = score >= threshold

    issues: list[str] = []

    if not semantic_ok:
        issues.append(
            "의미 기반 지시 준수 점수가 기준보다 낮습니다: "
            f"score={score:.4f}, threshold={threshold:.4f}"
        )

    return SemanticValidationResult(
        semantic_ok=semantic_ok,
        score=score,
        issues=issues,
    )