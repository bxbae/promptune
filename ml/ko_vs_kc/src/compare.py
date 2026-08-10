"""
outputs/*_metrics.json 을 모아 Ko vs Kc 비교표 출력 + 승자 추천.
"""
import json, glob, os

ELEMENTS = ["TASK","AUDIENCE","CONTEXT","FORMAT","TONE","LENGTH","CONSTRAINT","EXAMPLE"]


def load():
    res = {}
    for p in glob.glob("outputs/*_metrics.json"):
        d = json.load(open(p, encoding="utf-8"))
        res[d["tag"]] = d
    return res


def main():
    res = load()
    if not res:
        print("no metrics found. run baseline/train_eval first."); return

    tags = [t for t in ["baseline", "ko", "kc"] if t in res]
    print("\n" + "=" * 70)
    print("질문 트리거 기준 비교 (주 지표: Macro Recall / Macro F2)")
    print("=" * 70)
    print(f"{'metric':<18}" + "".join(f"{t:>16}" for t in tags))
    print("-" * 70)
    # 종합 지표 (F2/Recall 우선, F1은 참고)
    for key in ["macro_recall", "macro_f2", "macro_precision", "macro_f1",
                "min_precision", "miss_catch_rate", "missed_misses_FN", "false_alarms_FP"]:
        row = f"{key:<18}"
        for t in tags:
            v = res[t].get(key)
            if isinstance(v, float):
                row += f"{v:>16.4f}"
            elif isinstance(v, int):
                row += f"{v:>16d}"
            else:
                row += f"{'-':>16}"
        print(row)
    print("-" * 70)
    # 요소별 Recall (주 지표)
    print("요소별 Recall (누락을 얼마나 잡았나):")
    for e in ELEMENTS:
        row = f"  recall_{e:<10}"
        for t in tags:
            v = res[t].get(f"recall_{e}")
            row += f"{v:>16.4f}" if isinstance(v, float) else f"{'-':>16}"
        print(row)
    print("=" * 70)

    # baseline floor: F2 기준
    base_f2 = res.get("baseline", {}).get("macro_f2", 0.0)
    base_rec = res.get("baseline", {}).get("macro_recall", 0.0)
    print(f"\nbaseline (floor): Macro F2 = {base_f2:.4f}  |  Macro Recall = {base_rec:.4f}")
    for t in ["ko", "kc"]:
        if t in res:
            f2 = res[t]["macro_f2"]; rec = res[t]["macro_recall"]
            ok = "PASS" if f2 > base_f2 else "FAIL"
            print(f"  {t.upper():3s} Macro F2 = {f2:.4f}  Recall = {rec:.4f}  "
                  f"FN(놓침) = {res[t]['missed_misses_FN']}건  [{ok} floor]")

    if "ko" in res and "kc" in res:
        ko, kc = res["ko"], res["kc"]
        # 1순위 F2, 동률이면 FN 적은 쪽
        if abs(kc["macro_f2"] - ko["macro_f2"]) < 1e-6:
            win = "KcELECTRA" if kc["missed_misses_FN"] <= ko["missed_misses_FN"] else "KoELECTRA"
            basis = "F2 동률 → 놓친 누락(FN) 적은 쪽"
        else:
            win = "KcELECTRA" if kc["macro_f2"] > ko["macro_f2"] else "KoELECTRA"
            basis = f"Macro F2 {max(ko['macro_f2'], kc['macro_f2']):.4f}"
        print(f"\n>>> 1차 모델 추천: {win}  ({basis})")
        print("    질문 트리거 용도상 '누락을 덜 놓치는' 모델이 유리.")
        print("    요소별 강약은 recall_* 행 확인.")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
