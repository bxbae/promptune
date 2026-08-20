from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.services.retrieval.rag_retriever import get_model


@dataclass
class SemanticValidationResult:
    semantic_ok: bool
    score: float
    issues: list[str] = field(default_factory=list)


def _calculate_similarity(
    original: str,
    generated: str,
) -> float:
    """
    BGE-M3 dense embedding을 사용해
    원본 요청과 생성 응답의 cosine similarity를 계산한다.

    기존 RAG의 get_model()을 재사용하므로
    BGE-M3 모델은 프로세스당 한 번만 로딩된다.
    """
    model = get_model()

    output = model.encode(
        [original, generated],
        batch_size=2,
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )

    embeddings = np.asarray(
        output["dense_vecs"],
        dtype=np.float32,
    )

    if embeddings.shape != (2, 1024):
        raise RuntimeError(
            f"unexpected BGE-M3 embedding shape: {embeddings.shape}"
        )

    original_vector = embeddings[0]
    generated_vector = embeddings[1]

    original_norm = float(np.linalg.norm(original_vector))
    generated_norm = float(np.linalg.norm(generated_vector))

    if original_norm == 0.0 or generated_norm == 0.0:
        raise RuntimeError("BGE-M3 returned a zero-length embedding vector.")

    similarity = float(
        np.dot(original_vector, generated_vector)
        / (original_norm * generated_norm)
    )

    return similarity


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