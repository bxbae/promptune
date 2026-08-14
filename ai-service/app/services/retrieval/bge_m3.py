from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from FlagEmbedding import BGEM3FlagModel


MODEL_NAME = "BAAI/bge-m3"
EXPECTED_DIM = 1024


def load_chunks(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not isinstance(chunks, list) or not chunks:
        raise ValueError("chunk JSON은 비어 있지 않은 list여야 합니다.")

    for i, chunk in enumerate(chunks):
        if "chunk_id" not in chunk or "content" not in chunk:
            raise ValueError(f"{i}번째 chunk에 chunk_id/content가 없습니다.")

    return chunks


def encode_dense(
    texts: list[str],
    batch_size: int = 4,
    max_length: int = 512,
) -> np.ndarray:
    print(f"[1/3] BGE-M3 로드: {MODEL_NAME}")
    print("      device=cpu, use_fp16=False")

    model = BGEM3FlagModel(
        MODEL_NAME,
        use_fp16=False,
        device="cpu",
    )

    print(f"[2/3] embedding 생성: {len(texts)} chunks")
    started = time.perf_counter()

    output = model.encode(
        texts,
        batch_size=batch_size,
        max_length=max_length,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )

    embeddings = np.asarray(output["dense_vecs"], dtype=np.float32)
    elapsed = time.perf_counter() - started

    print(f"      완료: {elapsed:.2f} sec")
    return embeddings


def validate_embeddings(embeddings: np.ndarray, expected_rows: int) -> None:
    if embeddings.ndim != 2:
        raise RuntimeError(f"embedding이 2차원이 아닙니다: shape={embeddings.shape}")

    if embeddings.shape[0] != expected_rows:
        raise RuntimeError(
            f"chunk 수와 embedding 수가 다릅니다: "
            f"{expected_rows} != {embeddings.shape[0]}"
        )

    if embeddings.shape[1] != EXPECTED_DIM:
        raise RuntimeError(
            f"BGE-M3 dense embedding 차원이 {EXPECTED_DIM}이 아닙니다: "
            f"{embeddings.shape[1]}"
        )

    if not np.isfinite(embeddings).all():
        raise RuntimeError("embedding에 NaN 또는 inf가 있습니다.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PrompTune RAG BGE-M3 dense embedding smoke test"
    )
    parser.add_argument("--input", required=True, help="rag_test_chunks.json 경로")
    parser.add_argument("--output", required=True, help="embedding .npy 저장 경로")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=512)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    chunks = load_chunks(input_path)
    texts = [chunk["content"] for chunk in chunks]

    embeddings = encode_dense(
        texts,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )
    validate_embeddings(embeddings, len(chunks))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, embeddings)

    norms = np.linalg.norm(embeddings, axis=1)

    print("[3/3] 검증 완료")
    print(f"      shape={embeddings.shape}")
    print(f"      dtype={embeddings.dtype}")
    print(
        "      norm(min/avg/max)="
        f"{norms.min():.6f}/{norms.mean():.6f}/{norms.max():.6f}"
    )
    print(
        "      first_vector[:5]="
        + np.array2string(embeddings[0, :5], precision=6)
    )
    print(f"      saved={output_path}")
    print("BGE-M3 EMBEDDING OK")


if __name__ == "__main__":
    main()
