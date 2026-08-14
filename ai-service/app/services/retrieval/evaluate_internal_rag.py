from __future__ import annotations

import json
from pathlib import Path

from bge_m3 import encode_dense
from test_pgvector_retrieval import search_pgvector


BASE_DIR = Path("ai-service/app/data/rag")

DOCUMENTS_PATH = BASE_DIR / "rag_test_documents.json"
QUERIES_PATH = BASE_DIR / "rag_test_queries.json"
OUTPUT_PATH = BASE_DIR / "rag_pgvector_eval_results.json"

OWNER_USER_ID = 2
TOP_K = 3


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    documents = load_json(DOCUMENTS_PATH)
    queries = load_json(QUERIES_PATH)

    internal_queries = [
        q for q in queries
        if q.get("expected_route") == "internal_rag"
    ]

    documents_by_id = {
        doc["id"]: doc
        for doc in documents
    }

    print("[1/4] 평가 데이터 확인")
    print(f"documents={len(documents)}")
    print(f"internal_rag_queries={len(internal_queries)}")

    query_texts = [
        q["query"]
        for q in internal_queries
    ]

    print()
    print("[2/4] BGE-M3 Batch Embedding")

    embeddings = encode_dense(
        query_texts,
        batch_size=8,
        max_length=512,
    )

    print(f"embedding_shape={embeddings.shape}")

    print()
    print("[3/4] pgvector Top-3 평가")

    results = []
    top1_hits = 0
    top3_hits = 0

    for index, (query, embedding) in enumerate(
        zip(internal_queries, embeddings),
        start=1,
    ):
        expected_doc_id = query["expected_doc_id"]
        expected_title = documents_by_id[expected_doc_id]["title"]

        retrieved = search_pgvector(
            query_embedding=embedding,
            owner_user_id=OWNER_USER_ID,
            top_k=TOP_K,
        )

        retrieved_titles = [
            row["title"]
            for row in retrieved
        ]

        top1_hit = (
            len(retrieved_titles) > 0
        and retrieved_titles[0] == expected_title
        )

        top3_hit = expected_title in retrieved_titles

        if top1_hit:
            top1_hits += 1

        if top3_hit:
            top3_hits += 1

        result = {
            "id": query["id"],
            "query": query["query"],
            "expected_doc_id": expected_doc_id,
            "expected_title": expected_title,
            "top1_hit": top1_hit,
            "top3_hit": top3_hit,
            "retrieved": retrieved,
        }

        results.append(result)

        status1 = "PASS" if top1_hit else "FAIL"
        status3 = "PASS" if top3_hit else "FAIL"

        print(
            f"[{index:02d}/{len(internal_queries)}] "
            f"{query['id']} | "
            f"Top-1={status1} | "
            f"Top-3={status3}"
        )

    total = len(results)

    top1_accuracy = (
        top1_hits / total * 100
        if total else 0.0
    )

    top3_accuracy = (
        top3_hits / total * 100
        if total else 0.0
    )

    failures = [
        result
        for result in results
        if not result["top1_hit"]
    ]

    summary = {
        "total": total,
        "top1_hits": top1_hits,
        "top3_hits": top3_hits,
        "top1_accuracy": top1_accuracy,
        "top3_accuracy": top3_accuracy,
        "top1_failures": len(failures),
        "results": results,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("[4/4] 최종 결과")
    print("=" * 60)
    print(f"전체 질문       : {total}")
    print(f"Top-1 정답      : {top1_hits}/{total}")
    print(f"Top-1 Accuracy  : {top1_accuracy:.2f}%")
    print(f"Top-3 정답      : {top3_hits}/{total}")
    print(f"Top-3 Accuracy  : {top3_accuracy:.2f}%")
    print(f"Top-1 실패 질문 : {len(failures)}")
    print(f"결과 저장       : {OUTPUT_PATH}")

    if failures:
        print()
        print("[Top-1 실패 질문]")

        for failure in failures:
            first = (
                failure["retrieved"][0]["title"]
                if failure["retrieved"]
                else "검색 결과 없음"
            )

            print(
                f"- {failure['id']} | "
                f"{failure['query']} | "
                f"expected={failure['expected_title']} | "
                f"actual={first}"
            )


if __name__ == "__main__":
    main()
