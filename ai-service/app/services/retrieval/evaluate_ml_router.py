import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

from app.services.retrieval.ml_router import MLRetrievalRouter
from app.services.retrieval.retrieval_router import classify_retrieval_route

APP = Path(__file__).resolve().parents[2]
TRAIN = APP / "data/rag/routing_train_242.json"
TEST = APP / "data/rag/routing_blind_batch05.json"


def normalize(value):
    return str(getattr(value, "value", value))


def evaluate(name, fn, rows):
    correct = 0
    stats = defaultdict(lambda: [0, 0])

    for row in rows:
        expected = row["expected_route"]
        predicted = normalize(fn(row["query"]))

        stats[expected][1] += 1
        if predicted == expected:
            correct += 1
            stats[expected][0] += 1

    acc = correct / len(rows) * 100

    print(f"\n{name}: {correct}/{len(rows)} = {acc:.2f}%")
    for route in sorted(stats):
        ok, total = stats[route]
        print(f"{route:24s} {ok}/{total} = {ok/total*100:.1f}%")

    return acc


def latency(name, fn, rows):
    for row in rows:
        fn(row["query"])

    times = []

    for _ in range(50):
        for row in rows:
            start = time.perf_counter()
            fn(row["query"])
            times.append((time.perf_counter() - start) * 1000)

    times.sort()
    avg = statistics.mean(times)
    p95 = times[int(len(times) * 0.95) - 1]

    print(f"{name}: avg={avg:.4f}ms p95={p95:.4f}ms")
    return avg, p95


train = json.loads(TRAIN.read_text(encoding="utf-8"))
test = json.loads(TEST.read_text(encoding="utf-8"))

ml = MLRetrievalRouter()

start = time.perf_counter()
ml.fit(
    [x["query"] for x in train],
    [x["expected_route"] for x in train],
)
training_ms = (time.perf_counter() - start) * 1000

rule_acc = evaluate("RULE", classify_retrieval_route, test)
ml_acc = evaluate("TF-IDF + LinearSVC", ml.predict, test)

print("\nLATENCY")
rule_avg, rule_p95 = latency("RULE", classify_retrieval_route, test)
ml_avg, ml_p95 = latency("LinearSVC", ml.predict, test)

print("\n===== FINAL =====")
print(f"Training   : {training_ms:.2f}ms")
print(f"RULE       : accuracy={rule_acc:.2f}% avg={rule_avg:.4f}ms p95={rule_p95:.4f}ms")
print(f"LinearSVC  : accuracy={ml_acc:.2f}% avg={ml_avg:.4f}ms p95={ml_p95:.4f}ms")
