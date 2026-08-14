from __future__ import annotations

import json

from retrieval_router import classify_retrieval_route


QUERY_PATH = "ai-service/app/data/rag/rag_test_queries.json"


def main() -> None:
    with open(QUERY_PATH, encoding="utf-8") as f:
        queries = json.load(f)

    targets = [
        q for q in queries
        if q.get("expected_route") != "internal_rag"
    ]

    passed = 0

    print("[Routing Evaluation]")
    print("=" * 80)

    for q in targets:
        expected = q["expected_route"]
        predicted = classify_retrieval_route(q["query"])
        success = predicted == expected

        if success:
            passed += 1

        status = "PASS" if success else "FAIL"

        print(
            f"{q['id']} | "
            f"{status} | "
            f"expected={expected} | "
            f"predicted={predicted}"
        )

    total = len(targets)
    accuracy = passed / total * 100 if total else 0.0

    print()
    print("=" * 80)
    print(f"Total    : {total}")
    print(f"Correct  : {passed}/{total}")
    print(f"Accuracy : {accuracy:.2f}%")


if __name__ == "__main__":
    main()
