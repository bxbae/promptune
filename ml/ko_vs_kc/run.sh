#!/usr/bin/env bash
# Ko vs Kc 전체 비교 파이프라인 (동일 데이터·동일 하이퍼파라미터)
set -e
cd "$(dirname "$0")"

echo "[1/5] 합성 데이터 생성"
python src/gen_data.py --n "${N:-1500}" --out data/synth.csv

echo "[2/5] 규칙 기반 baseline (성능 바닥)"
python src/baseline.py --data data/synth.csv

echo "[3/5] KoELECTRA 학습·평가"
python src/train_eval.py --model monologg/koelectra-base-v3-discriminator --tag ko

echo "[4/5] KcELECTRA 학습·평가"
python src/train_eval.py --model beomi/KcELECTRA-base --tag kc

echo "[5/5] 비교표 + 1차 모델 추천"
python src/compare.py
