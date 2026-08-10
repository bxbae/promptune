"""
데모용 검수본 자동 생성기.
review 시트의 *_final 칸을 채우되, 두 검수자(A/B)가 서로 다르게 판단한 것처럼
일부 요소를 확률적으로 뒤집어 현실적인 불일치를 만든다.
→ kappa_finalize.py 를 돌리면 요소별로 다양한 kappa 값이 나와 시연에 적합.

주의: 이건 '실제 검수'가 아니라 시연용 합성 라벨이다. 실제 라벨링에는 쓰지 말 것.

사용:
  python src/make_demo_reviews.py --in data/prelabeled.csv \
      --out-a data/review_A.csv --out-b data/review_B.csv
"""
import argparse, csv, random
from config import ELEMENTS

# 요소별 '불일치 확률'을 다르게 줘서 kappa가 요소마다 달라지게 함.
# TONE/CONSTRAINT처럼 경계가 애매한 요소는 높게 → 낮은 kappa로 시연.
DISAGREE_P = {
    "TASK": 0.03, "AUDIENCE": 0.10, "CONTEXT": 0.15, "FORMAT": 0.08,
    "TONE": 0.30, "LENGTH": 0.10, "CONSTRAINT": 0.28, "EXAMPLE": 0.12,
}


def write_sheet(rows, path, flip_map=None):
    header = ["id", "text"]
    for e in ELEMENTS:
        header += [f"{e}_llm", f"{e}_final"]
    header += ["need_review", "note"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            line = [r["id"], r["text"]]
            for e in ELEMENTS:
                llm = int(r[e])
                final = llm
                if flip_map is not None:      # B: 확률적으로 뒤집기
                    if random.random() < DISAGREE_P[e]:
                        final = 1 - final
                line += [llm, final]
            line += [r.get("need_review", "0"), ""]
            w.writerow(line)


def main(a):
    random.seed(a.seed)
    rows = list(csv.DictReader(open(a.in_path, encoding="utf-8")))
    # A: 규칙 라벨을 그대로 확정(검수자 A가 규칙에 동의했다고 가정)
    write_sheet(rows, a.out_a, flip_map=None)
    # B: 일부 요소를 뒤집어 A와 다른 판단 시뮬레이션
    write_sheet(rows, a.out_b, flip_map=DISAGREE_P)
    print(f"wrote {a.out_a} (검수자 A)")
    print(f"wrote {a.out_b} (검수자 B, 일부 불일치 주입)")
    print("→ python src/kappa_finalize.py --reviews", a.out_a, a.out_b, "--gold data/gold.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", default="data/prelabeled.csv")
    ap.add_argument("--out-a", default="data/review_A.csv")
    ap.add_argument("--out-b", default="data/review_B.csv")
    ap.add_argument("--seed", type=int, default=42)
    main(ap.parse_args())
