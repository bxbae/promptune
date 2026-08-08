"""
단일 모델 학습·평가 harness (멀티라벨 8요소 누락 탐지).
Ko/Kc를 동일 하이퍼파라미터·동일 데이터·동일 split으로 돌리기 위한 공통 코드.

검증 기준 (K모델 = 질문 트리거 용도):
  - 주 지표: 요소별 Recall, Macro F2 (재현율 우선 — 누락을 놓치면 치명적)
  - 감시 지표: Precision, min_precision (질문 폭탄 방지 하한)
  - 질문 트리거 직접 집계: 놓친 누락 수(FN), 헛물음 수(FP), 누락 포착률
  - 참고: Macro F1 (기존 균형 지표)
  baseline(F2) 초과 여부가 통과 기준.

사용:
  python src/train_eval.py --model monologg/koelectra-base-v3-discriminator --tag ko
  python src/train_eval.py --model beomi/KcELECTRA-base --tag kc
"""
import argparse, json, os, random
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    f1_score, fbeta_score, precision_score, recall_score,
    multilabel_confusion_matrix,
)
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    TrainingArguments, Trainer, set_seed,
)

ELEMENTS = ["TASK","AUDIENCE","CONTEXT","FORMAT","TONE","LENGTH","CONSTRAINT","EXAMPLE"]
SEED = 42


def seed_all(s=SEED):
    random.seed(s); np.random.seed(s); torch.manual_seed(s); set_seed(s)


class MLDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len=128):
        self.enc = tokenizer(list(texts), truncation=True, padding="max_length",
                             max_length=max_len)
        self.labels = np.array(labels, dtype=np.float32)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        item = {k: torch.tensor(v[i]) for k, v in self.enc.items()}
        item["labels"] = torch.tensor(self.labels[i])
        return item


def compute_metrics(eval_pred):
    """
    검증 기준: K모델은 '질문 트리거'이므로 재현율(Recall)을 우선한다.
    라벨 정의: 1 = 누락(positive), 0 = 포함.
      - '누락을 놓침'(FN) = 실제 1을 0으로 예측 → 되묻지 못함 → 치명적.
      - '헛물음'(FP) = 실제 0을 1로 예측 → 불필요한 질문 → 가벼움.
    따라서 주 지표는 Recall/F2, Precision은 감시(하한 관리)용.
    """
    logits, labels = eval_pred
    probs = 1 / (1 + np.exp(-logits))          # sigmoid
    preds = (probs >= 0.5).astype(int)
    labels = labels.astype(int)

    per_recall = recall_score(labels, preds, average=None, zero_division=0)
    per_prec = precision_score(labels, preds, average=None, zero_division=0)
    per_f1 = f1_score(labels, preds, average=None, zero_division=0)
    per_f2 = fbeta_score(labels, preds, beta=2, average=None, zero_division=0)

    out = {}
    # 요소별 주 지표: Recall, F2 (+ 참고용 Precision, F1)
    for i, e in enumerate(ELEMENTS):
        out[f"recall_{e}"] = float(per_recall[i])   # 주: 누락을 얼마나 안 놓쳤나
        out[f"f2_{e}"] = float(per_f2[i])           # 주: 재현율 가중 F
        out[f"precision_{e}"] = float(per_prec[i])  # 감시
        out[f"f1_{e}"] = float(per_f1[i])           # 참고

    # 종합 지표
    out["macro_recall"] = float(recall_score(labels, preds, average="macro", zero_division=0))
    out["macro_f2"] = float(fbeta_score(labels, preds, beta=2, average="macro", zero_division=0))
    out["macro_precision"] = float(precision_score(labels, preds, average="macro", zero_division=0))
    out["macro_f1"] = float(f1_score(labels, preds, average="macro", zero_division=0))
    out["min_precision"] = float(per_prec.min())    # 감시: 질문 폭탄 방지 하한

    # 질문 트리거 관점 직접 집계: 놓친 누락 수(FN), 헛물음 수(FP)
    mcm = multilabel_confusion_matrix(labels, preds)  # 요소별 [[TN,FP],[FN,TP]]
    total_fn = int(sum(m[1, 0] for m in mcm))         # 실제 누락인데 못 잡음
    total_fp = int(sum(m[0, 1] for m in mcm))         # 안 빠졌는데 빠졌다 함
    total_actual_miss = int(labels.sum())             # 실제 누락 총 개수
    out["missed_misses_FN"] = total_fn                # 낮을수록 좋음(치명적 오류)
    out["false_alarms_FP"] = total_fp                 # 낮을수록 좋음(가벼운 오류)
    # 실제 누락 중 몇 %를 놓쳤나 (질문 트리거 실패율)
    out["miss_catch_rate"] = float(1 - total_fn / total_actual_miss) if total_actual_miss else 0.0
    return out


def main(a):
    seed_all()
    df = pd.read_csv(a.data)
    X = df["text"].values
    Y = df[ELEMENTS].values

    # 동일 split (seed 고정) → 두 모델이 완전히 같은 train/val/test를 본다
    X_tr, X_tmp, Y_tr, Y_tmp = train_test_split(X, Y, test_size=0.3, random_state=SEED)
    X_val, X_te, Y_val, Y_te = train_test_split(X_tmp, Y_tmp, test_size=0.5, random_state=SEED)

    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForSequenceClassification.from_pretrained(
        a.model, num_labels=len(ELEMENTS),
        problem_type="multi_label_classification",
    )

    ds_tr = MLDataset(X_tr, Y_tr, tok, a.max_len)
    ds_val = MLDataset(X_val, Y_val, tok, a.max_len)
    ds_te = MLDataset(X_te, Y_te, tok, a.max_len)

    args = TrainingArguments(
        output_dir=f"outputs/{a.tag}",
        num_train_epochs=a.epochs,
        per_device_train_batch_size=a.batch,
        per_device_eval_batch_size=a.batch,
        learning_rate=a.lr,
        weight_decay=0.01,
        warmup_ratio=0.1,
        eval_strategy="epoch",
        save_strategy="no",
        logging_steps=20,
        seed=SEED,
        report_to="none",
        fp16=torch.cuda.is_available(),
    )

    trainer = Trainer(
        model=model, args=args,
        train_dataset=ds_tr, eval_dataset=ds_val,
        compute_metrics=compute_metrics,
    )
    trainer.train()

    test_metrics = trainer.evaluate(ds_te, metric_key_prefix="test")
    test_metrics = {k.replace("test_", ""): v for k, v in test_metrics.items()
                    if k.startswith("test_")}
    test_metrics["model"] = a.model
    test_metrics["tag"] = a.tag

    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/{a.tag}_metrics.json", "w", encoding="utf-8") as f:
        json.dump(test_metrics, f, ensure_ascii=False, indent=2)

    print(f"\n=== [{a.tag}] TEST (질문 트리거 기준: Recall/F2 우선) ===")
    print(f"Macro Recall: {test_metrics['macro_recall']:.4f}  "
          f"Macro F2: {test_metrics['macro_f2']:.4f}  "
          f"(참고 Macro F1: {test_metrics['macro_f1']:.4f})")
    print(f"놓친 누락 FN: {test_metrics['missed_misses_FN']}건  "
          f"헛물음 FP: {test_metrics['false_alarms_FP']}건  "
          f"누락 포착률: {test_metrics['miss_catch_rate']:.4f}  "
          f"최저 Precision: {test_metrics['min_precision']:.4f}")
    print(f"  {'요소':10s} {'Recall':>8} {'F2':>8} {'Prec':>8} {'F1':>8}")
    for e in ELEMENTS:
        print(f"  {e:10s} "
              f"{test_metrics['recall_'+e]:>8.4f} "
              f"{test_metrics['f2_'+e]:>8.4f} "
              f"{test_metrics['precision_'+e]:>8.4f} "
              f"{test_metrics['f1_'+e]:>8.4f}")
    return test_metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--data", default="data/synth.csv")
    # ↓ 두 모델 공통 하이퍼파라미터 (여기만 고정하면 동일 조건 보장)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max_len", type=int, default=128)
    main(ap.parse_args())
