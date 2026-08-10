# KoELECTRA vs KcELECTRA — 8요소 누락 탐지 비교

PrompTune 파이프라인의 "8요소 누락·모호성 분류" 단계에 쓸 1차 모델을
**동일 조건**으로 비교해서 고르기 위한 학습·평가 harness (학습용).

## 태스크 정의
- **멀티라벨 8요소 이진분류**: 한 프롬프트에서 각 요소가 누락(1)인지 포함(0)인지.
- 요소: `TASK, AUDIENCE, CONTEXT, FORMAT, TONE, LENGTH, CONSTRAINT, EXAMPLE`
- 실제 파이프라인이 필요로 하는 게 "무엇이 빠졌나"이고 여러 요소가 동시에
  빠질 수 있으므로 멀티라벨이 맞음. 3값(정상/누락/모호)은 라벨 경계가
  주관적이라 학습용 비교엔 노이즈만 늘어 제외.

## 검증 기준 (K모델 = 질문 트리거 용도)
K모델의 출력은 "사용자에게 되물을지"를 결정한다. 누락을 **놓치면(FN)**
불완전한 프롬프트가 생성되어 치명적이고, **헛물으면(FP)** 질문이 하나 늘 뿐이다.
따라서 정밀도·재현율을 동등하게 보는 F1이 아니라 **재현율(Recall) 우선**으로 평가한다.
자세한 근거는 `K모델_검증기준.md` 참조.

- **주 지표**: 요소별 **Recall**, **Macro F2** (재현율 2배 가중)
- **감시 지표**: Precision, `min_precision` (질문 폭탄 방지 하한)
- **질문 트리거 직접 집계**: `missed_misses_FN`(놓친 누락), `false_alarms_FP`(헛물음),
  `miss_catch_rate`(누락 포착률)
- **참고**: Macro F1 (기존 균형 지표)
- baseline은 **Macro F2** 기준으로 floor를 정하고, 신경망이 이를 초과해야 통과.
- 1차는 누락(missing)만. 모호(vague)는 2단계 확장 과제.

## 공정성 보장
- 두 모델 **동일 데이터 · 동일 train/val/test split (seed=42)**
- **동일 하이퍼파라미터** (`train_eval.py`의 argparse 기본값 한 곳에서 관리)
- baseline은 규칙 기반 성능 바닥. 합성 데이터에 우회 표현(패러프레이즈)을 섞어
  규칙이 자명하게 100% 맞히지 못하도록 함 → Macro F1 ≈ 0.85 수준의 현실적 floor.

## 실행
```bash
pip install -r requirements.txt

# 전체 한 번에 (데이터 → baseline → Ko → Kc → 비교)
bash run.sh
# 데이터 양 조절: N=3000 bash run.sh

# 또는 개별 실행
python src/gen_data.py --n 1500 --out data/synth.csv
python src/baseline.py
python src/train_eval.py --model monologg/koelectra-base-v3-discriminator --tag ko
python src/train_eval.py --model beomi/KcELECTRA-base --tag kc
python src/compare.py
```

## 하이퍼파라미터 바꾸기
`src/train_eval.py`의 argparse 기본값만 수정하면 두 모델에 동일 적용됨:
`--epochs 4 --batch 16 --lr 2e-5 --max_len 128`

## 결과물
- `outputs/{ko,kc,baseline}_metrics.json`
- `compare.py`가 비교표 + 1차 모델 추천 출력

## 주의 (학습용 한계)
- 합성 데이터라 실제 사용자 프롬프트 분포와 다름. 실서비스 판단 전
  실제 수집 데이터로 재평가 권장.
- CPU에서도 돌아가지만 느림. GPU 권장 (`fp16` 자동 활성).
- Kc는 댓글·구어체 코퍼스 기반이라 오타·구어체가 많은 입력에서 유리할 가능성.
  실제로 element별 F1에서 확인할 것.
