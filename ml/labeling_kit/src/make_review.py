"""
사람 검수용 CSV 생성. prelabeled.csv → review_<labeler>.csv.

각 요소마다 LLM 제안값(*_llm)과 사람이 채울 확정칸(*_final)을 나란히 둔다.
검수자는 *_final 칸만 채우면 됨. 비워두면 LLM 값을 그대로 채택.
need_review=1 행을 위로 정렬해 우선 검수하게 함.
"""
import argparse, csv, os
from config import ELEMENTS, ELEMENT_DESC


def main(a):
    rows = list(csv.DictReader(open(a.in_path, encoding="utf-8")))
    # need_review=1 우선 정렬
    rows.sort(key=lambda r: r.get("need_review", "0"), reverse=True)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    header = ["id", "text"]
    for e in ELEMENTS:
        header += [f"{e}_llm", f"{e}_final"]
    header += ["need_review", "note"]

    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            line = [r["id"], r["text"]]
            for e in ELEMENTS:
                line += [r[e], ""]   # final 칸은 빈칸(검수자 입력)
            line += [r.get("need_review", "0"), ""]
            w.writerow(line)

    guide = a.out.replace(".csv", "_GUIDE.txt")
    with open(guide, "w", encoding="utf-8") as g:
        g.write("검수 가이드\n" + "=" * 40 + "\n")
        g.write("각 요소 *_final 칸에 0(포함) 또는 1(누락)을 입력.\n")
        g.write("비워두면 *_llm 값을 그대로 채택합니다.\n")
        g.write("규칙: 명시적으로 포함=0, 없거나 애매하면=1.\n\n")
        for e in ELEMENTS:
            g.write(f"  {e}: {ELEMENT_DESC[e]}\n")
        g.write("\nneed_review=1 행(맨 위)은 LLM이 실패한 것이니 반드시 확인.\n")

    print(f"wrote review sheet -> {a.out}")
    print(f"wrote guide        -> {guide}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", default="data/prelabeled.csv")
    ap.add_argument("--out", default="data/review_A.csv")
    main(ap.parse_args())
