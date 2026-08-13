from __future__ import annotations

import argparse
import subprocess

import numpy as np

from bge_m3 import encode_dense


def vector_to_sql(vector: np.ndarray) -> str:
    return "[" + ",".join(
        format(float(value), ".9g")
        for value in vector
    ) + "]"


def search_pgvector(
    query_embedding: np.ndarray,
    owner_user_id: int,
    top_k: int = 3,
) -> list[dict]:

    vector_sql = vector_to_sql(query_embedding)

    sql = f"""
SELECT
    d.id,
    d.title,
    dc.id,
    dc.chunk_index,
    1 - (dc.embedding <=> '{vector_sql}'::vector) AS score
FROM document_chunks dc
JOIN documents d
    ON d.id = dc.document_id
WHERE d.owner_user_id = {owner_user_id}
  AND d.tag = 'BGE_M3_TEST'
  AND dc.embedding IS NOT NULL
ORDER BY dc.embedding <=> '{vector_sql}'::vector
LIMIT {top_k};
"""

    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "sh",
        "-lc",
        'psql -v ON_ERROR_STOP=1 '
        '-A -t -F "|" '
        '-U "$POSTGRES_USER" '
        '-d "$POSTGRES_DB"',
    ]

    result = subprocess.run(
        command,
        input=sql,
        text=True,
        capture_output=True,
        check=True,
    )

    rows = []

    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        parts = line.split("|")

        if len(parts) != 5:
            continue

        rows.append({
            "document_id": int(parts[0]),
            "title": parts[1],
            "chunk_id": int(parts[2]),
            "chunk_index": int(parts[3]),
            "score": float(parts[4]),
        })

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--query",
        required=True,
    )

    parser.add_argument(
        "--owner-user-id",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--expected-title",
        default=None,
    )

    args = parser.parse_args()

    print("[1/3] Query Embedding 생성")
    print(f"query={args.query}")
    print(f"owner_user_id={args.owner_user_id}")

    query_embedding = encode_dense(
        [args.query],
        batch_size=1,
        max_length=512,
    )[0]

    print(f"shape={query_embedding.shape}")

    print()
    print("[2/3] pgvector 검색")

    results = search_pgvector(
        query_embedding=query_embedding,
        owner_user_id=args.owner_user_id,
        top_k=args.top_k,
    )

    print()
    print(f"[3/3] TOP-{args.top_k}")
    print("=" * 80)

    if not results:
        print("검색 결과 없음")
        return

    for rank, row in enumerate(results, start=1):
        print(
            f"TOP {rank} | "
            f"score={row['score']:.6f} | "
            f"document_id={row['document_id']} | "
            f"chunk_id={row['chunk_id']} | "
            f"chunk_index={row['chunk_index']}"
        )
        print(f"title={row['title']}")
        print("-" * 80)

    if args.expected_title:
        titles = [row["title"] for row in results]

        top1_hit = titles[0] == args.expected_title
        topk_hit = args.expected_title in titles

        print()
        print("[검색 결과 검증]")
        print(f"expected_title={args.expected_title}")
        print(f"Top-1 Hit={'PASS' if top1_hit else 'FAIL'}")
        print(
            f"Top-{args.top_k} Hit={'PASS' if topk_hit else 'FAIL'}"
        )


if __name__ == "__main__":
    main()
