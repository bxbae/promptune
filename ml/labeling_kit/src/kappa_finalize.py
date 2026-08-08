"""
검수 결과 취합 + 라벨 신뢰도 측정 + 최종(gold) 라벨 산출.

기능:
  1) 한 명 검수본 → gold CSV로 확정 (train_eval.py 입력 형식)
  2) 두 명 이상 검수본 → 요소별 Cohen's kappa로 라벨러 간 일치도 측정
     (2명 초과면 쌍별 kappa 평균 = Fleiss 근사 대신 pairwise 평균)

사용:
  # 단일 검수본 확정
  python src/kappa_finalize.py --reviews data/review_A.csv --gold data/gold.csv

  # 두 검수본 일치도 + 다수결 gold
  python src/kappa_finalize.py --reviews data/review_A.csv data/review_B.csv \
      --gold data/gold.csv
"""
import argparse, csv, os, itertools
from config import ELEMENTS


def resolve(row, e):
    """final 칸이 있으면 그 값, 없으면 llm 값."""
    fin = row.get(f"{e}_final", "").strip()
    if fin in ("0", "1"):
        return int(fin)
    return int(row.get(f"{e}_llm", "1"))


def load_review(path):
    d = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        d[r["id"]] = {"text": r["text"], **{e: resolve(r, e) for e in ELEMENTS}}
    return d


def cohen_kappa(a, b):
    """이진 라벨 두 리스트의 Cohen's kappa (직접 구현, 외부 의존 없음)."""
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1 = sum(a) / n; pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def interpret(k):
    if k != k:  # nan
        return "N/A"
    if k < 0.0:  return "poor"
    if k < 0.20: return "slight"
    if k < 0.40: return "fair"
    if k < 0.60: return "moderate"
    if k < 0.80: return "substantial"
    return "almost perfect"


def main(a):
    reviews = [load_review(p) for p in a.reviews]
    ids = set(reviews[0])
    for r in reviews[1:]:
        ids &= set(r)          # 공통 id만 사용
    ids = sorted(ids)

    # --- kappa (2명 이상일 때) ---
    if len(reviews) >= 2:
        print("\n=== 라벨러 간 일치도 (Cohen's kappa) ===")
        print(f"{'element':<12}{'kappa':>8}   해석")
        print("-" * 40)
        macro = []
        for e in ELEMENTS:
            pair_ks = []
            for r1, r2 in itertools.combinations(reviews, 2):
                a1 = [r1[i][e] for i in ids]
                a2 = [r2[i][e] for i in ids]
                pair_ks.append(cohen_kappa(a1, a2))
            k = sum(pair_ks) / len(pair_ks)
            macro.append(k)
            print(f"{e:<12}{k:>8.3f}   {interpret(k)}")
        mk = sum(macro) / len(macro)
        print("-" * 40)
        print(f"{'MEAN':<12}{mk:>8.3f}   {interpret(mk)}")
        print("\n※ kappa<0.40인 요소는 라벨 기준이 모호하다는 신호 → 가이드 재정의 권장.\n")

    # --- gold 산출 (다수결; 동률이면 누락=1로 보수적) ---
    os.makedirs(os.path.dirname(a.gold), exist_ok=True)
    with open(a.gold, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text"] + ELEMENTS)
        for i in ids:
            text = reviews[0][i]["text"]
            labels = []
            for e in ELEMENTS:
                votes = [r[i][e] for r in reviews]
                ones = sum(votes)
                labels.append(1 if ones * 2 >= len(votes) else 0)  # 동률→1
            w.writerow([text] + labels)
    print(f"gold labels -> {a.gold}  (rows={len(ids)})")
    print("→ 이 파일을 ko_vs_kc harness의 --data 로 사용하세요.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews", nargs="+", required=True)
    ap.add_argument("--gold", default="data/gold.csv")
    main(ap.parse_args())
