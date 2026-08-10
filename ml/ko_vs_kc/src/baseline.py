"""
규칙 기반 baseline. 신경망이 반드시 넘어야 할 성능 바닥(floor).
키워드 사전으로 각 요소의 '포함' 여부를 판정 → 없으면 누락(1).
"""
import argparse, json
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    f1_score, fbeta_score, recall_score, precision_score,
    multilabel_confusion_matrix,
)

ELEMENTS = ["TASK","AUDIENCE","CONTEXT","FORMAT","TONE","LENGTH","CONSTRAINT","EXAMPLE"]
SEED = 42

# 요소별 신호 키워드 (gen_data의 표현과 느슨하게 대응)
CUES = {
    "TASK":     ["요약","초안","리뷰","작성","번역","설명","정리","글","사과문","공지"],
    "AUDIENCE": ["님께","담당자","대상","한테","에게","보고용"],
    "CONTEXT":  ["관련","바탕","기준","상황","건과","접수"],
    "FORMAT":   ["형식","목록","마크다운","문단 구성","리스트","표 "],
    "TONE":     ["어조","친근","톤","단호","느낌","전문적"],
    "LENGTH":   ["자 이내","줄","문단","자 내외","항목"],
    "CONSTRAINT":["빼고","포함","없이","존댓말","말고","추려"],
    "EXAMPLE":  ["처럼","참고","예시","템플릿","스타일"],
}


def predict(text):
    labels = []
    for e in ELEMENTS:
        present = any(cue in text for cue in CUES[e])
        labels.append(0 if present else 1)  # 없으면 누락
    return labels


def main(a):
    df = pd.read_csv(a.data)
    X = df["text"].values
    Y = df[ELEMENTS].values
    _, X_tmp, _, Y_tmp = train_test_split(X, Y, test_size=0.3, random_state=SEED)
    _, X_te, _, Y_te = train_test_split(X_tmp, Y_tmp, test_size=0.5, random_state=SEED)

    import numpy as np
    preds = np.array([predict(t) for t in X_te])
    Y_te = Y_te.astype(int)

    per_recall = recall_score(Y_te, preds, average=None, zero_division=0)
    per_prec = precision_score(Y_te, preds, average=None, zero_division=0)
    per_f1 = f1_score(Y_te, preds, average=None, zero_division=0)
    per_f2 = fbeta_score(Y_te, preds, beta=2, average=None, zero_division=0)

    out = {"tag": "baseline"}
    for i, e in enumerate(ELEMENTS):
        out[f"recall_{e}"] = float(per_recall[i])
        out[f"f2_{e}"] = float(per_f2[i])
        out[f"precision_{e}"] = float(per_prec[i])
        out[f"f1_{e}"] = float(per_f1[i])
    out["macro_recall"] = float(recall_score(Y_te, preds, average="macro", zero_division=0))
    out["macro_f2"] = float(fbeta_score(Y_te, preds, beta=2, average="macro", zero_division=0))
    out["macro_precision"] = float(precision_score(Y_te, preds, average="macro", zero_division=0))
    out["macro_f1"] = float(f1_score(Y_te, preds, average="macro", zero_division=0))
    out["min_precision"] = float(per_prec.min())

    mcm = multilabel_confusion_matrix(Y_te, preds)
    out["missed_misses_FN"] = int(sum(m[1, 0] for m in mcm))
    out["false_alarms_FP"] = int(sum(m[0, 1] for m in mcm))
    tot_miss = int(Y_te.sum())
    out["miss_catch_rate"] = float(1 - out["missed_misses_FN"] / tot_miss) if tot_miss else 0.0

    import os as _os; _os.makedirs("outputs", exist_ok=True)
    with open("outputs/baseline_metrics.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"=== [baseline] TEST (질문 트리거 기준) ===")
    print(f"Macro Recall={out['macro_recall']:.4f}  Macro F2={out['macro_f2']:.4f}  "
          f"(참고 F1={out['macro_f1']:.4f})")
    print(f"놓친 누락 FN={out['missed_misses_FN']}건  헛물음 FP={out['false_alarms_FP']}건  "
          f"누락 포착률={out['miss_catch_rate']:.4f}")
    print(f"  {'요소':10s} {'Recall':>8} {'F2':>8} {'Prec':>8}")
    for i, e in enumerate(ELEMENTS):
        print(f"  {e:10s} {per_recall[i]:>8.4f} {per_f2[i]:>8.4f} {per_prec[i]:>8.4f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synth.csv")
    main(ap.parse_args())
