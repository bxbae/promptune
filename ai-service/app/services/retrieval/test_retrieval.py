from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from bge_m3 import EXPECTED_DIM, encode_dense


def load_chunks(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not isinstance(chunks, list) or not chunks:
        raise ValueError("chunk JSON은 비어 있지 않은 list여야 합니다.")

    return chunks


def cosine_similarity(
    query_embedding: np.ndarray,
    chunk_embeddings: np.ndarray,
) -> np.ndarray:
    """
    query embedding과 모든 chunk embedding의 cosine similarity 계산
    """

    query_norm = np.linalg.norm(query_embedding)

    if query_norm == 0:
        raise RuntimeError("query embedding의 norm이 0입니다.")

    chunk_norms = np.linalg.norm(
        chunk_embeddings,
        axis=1,
        keepdims=True,
    )

    if np.any(chunk_norms == 0):
        raise RuntimeError("norm이 0인 chunk embedding이 있습니다.")

    normalized_query = query_embedding / query_norm
    normalized_chunks = chunk_embeddings / chunk_norms

    return normalized_chunks @ normalized_query


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PrompTune BGE-M3 cosine similarity Top-K retrieval test"
    )

    parser.add_argument(
        "--chunks",
        default="ai-service/app/data/rag/rag_test_chunks.json",
        help="chunk JSON 경로",
    )

    parser.add_argument(
        "--embeddings",
        default="ai-service/app/data/rag/rag_test_embeddings.npy",
        help="chunk embedding .npy 경로",
    )

    parser.add_argument(
        "--query",
        required=True,
        help="검색할 사용자 질문",
    )

    parser.add_argument(
        "--company-id",
        default=None,
        help="검색 대상 company_id",
    )

    parser.add_argument(
        "--expected-doc-id",
        default=None,
        help="테스트용 기대 document_id",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
    )

    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    embeddings_path = Path(args.embeddings)

    # 1. 기존 chunk / embedding 로드
    chunks = load_chunks(chunks_path)
    chunk_embeddings = np.load(embeddings_path)

    print("[1/4] 기존 데이터 로드")
    print(f"      chunks={len(chunks)}")
    print(f"      embeddings={chunk_embeddings.shape}")

    if chunk_embeddings.ndim != 2:
        raise RuntimeError(
            f"embedding이 2차원이 아닙니다: {chunk_embeddings.shape}"
        )

    if chunk_embeddings.shape[0] != len(chunks):
        raise RuntimeError(
            "chunk 개수와 embedding 개수가 다릅니다: "
            f"{len(chunks)} != {chunk_embeddings.shape[0]}"
        )

    if chunk_embeddings.shape[1] != EXPECTED_DIM:
        raise RuntimeError(
            f"embedding 차원이 {EXPECTED_DIM}이 아닙니다: "
            f"{chunk_embeddings.shape[1]}"
        )

    # 2. 질문 embedding 생성
    print()
    print(f"[2/4] Query embedding 생성")
    print(f"      query={args.query}")

    query_embedding = encode_dense(
        [args.query],
        batch_size=1,
        max_length=512,
    )[0]

    print(f"      query_shape={query_embedding.shape}")

    # 3. cosine similarity 계산
    scores = cosine_similarity(
        query_embedding,
        chunk_embeddings,
    )

    candidate_indices = np.arange(len(chunks))

    # company_id가 지정된 경우 해당 회사 chunk만 검색
    if args.company_id:
        candidate_indices = np.array(
            [
                i
                for i, chunk in enumerate(chunks)
                if chunk.get("company_id") == args.company_id
            ]
        )

        if len(candidate_indices) == 0:
            raise RuntimeError(
                f"company_id={args.company_id}에 해당하는 chunk가 없습니다."
            )

    candidate_scores = scores[candidate_indices]

    top_k = min(args.top_k, len(candidate_indices))

    sorted_positions = np.argsort(candidate_scores)[::-1][:top_k]

    top_indices = candidate_indices[sorted_positions]

    # 4. Top-K 결과 출력
    print()
    print(f"[3/4] Cosine Similarity 계산 완료")
    print(f"      candidates={len(candidate_indices)}")

    print()
    print(f"[4/4] TOP-{top_k} 검색 결과")
    print("=" * 90)

    retrieved_doc_ids = []

    for rank, index in enumerate(top_indices, start=1):
        chunk = chunks[index]
        score = float(scores[index])

        document_id = chunk.get("document_id")
        retrieved_doc_ids.append(document_id)

        print(f"TOP {rank}")
        print(f"score       : {score:.6f}")
        print(f"chunk_id    : {chunk.get('chunk_id')}")
        print(f"document_id : {document_id}")
        print(f"company_id  : {chunk.get('company_id')}")
        print(f"title       : {chunk.get('title')}")
        print(f"chunk_index : {chunk.get('chunk_index')}")
        print("-" * 90)
        print(chunk.get("content"))
        print("=" * 90)
        print()

    # 기대 문서가 지정된 경우 간단 평가
    if args.expected_doc_id:
        top1_hit = (
            len(retrieved_doc_ids) >= 1
            and retrieved_doc_ids[0] == args.expected_doc_id
        )

        topk_hit = args.expected_doc_id in retrieved_doc_ids

        print("[검색 결과 검증]")
        print(f"expected_doc_id={args.expected_doc_id}")
        print(f"retrieved_doc_ids={retrieved_doc_ids}")
        print(f"Top-1 Hit={'PASS' if top1_hit else 'FAIL'}")
        print(f"Top-{top_k} Hit={'PASS' if topk_hit else 'FAIL'}")


if __name__ == "__main__":
    main()