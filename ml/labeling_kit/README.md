# 8요소 라벨링 도구 세트

실제 수집 프롬프트를 8요소 멀티라벨(누락 0/1)로 라벨링해서
`ko_vs_kc` harness의 학습 데이터(gold.csv)를 만드는 파이프라인.

## 흐름
```
MySQL/CSV 원문
  └ fetch_source.py    → to_label.csv   (PII 마스킹·중복제거)
      └ prelabel.py    → prelabeled.csv (LLM 사전 라벨링 A)
          └ make_review.py → review_A.csv (+GUIDE) 사람 검수
              └ (검수자가 *_final 칸 입력)
                  └ kappa_finalize.py → gold.csv (+ kappa 리포트)
                        → ko_vs_kc/src/train_eval.py --data gold.csv
```

## 8요소
TASK, AUDIENCE, CONTEXT, FORMAT, TONE, LENGTH, CONSTRAINT, EXAMPLE
라벨 규약: **명시 포함=0, 없거나 애매=1** (일관성 위해 "애매=누락"으로 통일)

## 실행

### 1) 원문 수집
```bash
# CSV에서
python src/fetch_source.py --source csv --in data/raw.csv --text-col text

# MySQL에서 (PrompTune 로그 테이블 등)
python src/fetch_source.py --source mysql \
  --host localhost --db promptune --user root --password '***' \
  --table prompts --text-col original_text --id-col id --limit 2000
```
자동으로 이메일/전화/주민번호 마스킹 + 중복 원문 제거.

### 2) LLM 사전 라벨링
```bash
# Claude
ANTHROPIC_API_KEY=... python src/prelabel.py --backend claude --model claude-sonnet-4-6

# HyperCLOVA X
CLOVA_HOST=... CLOVA_API_KEY=... python src/prelabel.py --backend clova --model HCX-003

# API 없이 규칙 초벌 (오프라인)
python src/prelabel.py --backend rule
```

### 3) 검수 시트 생성
```bash
python src/make_review.py --in data/prelabeled.csv --out data/review_A.csv
```
`review_A.csv`의 `*_final` 칸에 0/1 입력 (비우면 LLM값 채택).
`review_A_GUIDE.txt`에 요소 설명·규칙 있음.
**2명 이상 검수 권장** → review_A.csv, review_B.csv 각각 작성.

### 4) 일치도 측정 + gold 확정
```bash
# 단일 검수본
python src/kappa_finalize.py --reviews data/review_A.csv --gold data/gold.csv

# 2명 검수본 (요소별 Cohen's kappa 출력 + 다수결 gold)
python src/kappa_finalize.py --reviews data/review_A.csv data/review_B.csv --gold data/gold.csv
```

## kappa 해석
| kappa | 의미 |
|-------|------|
| <0.40 | 라벨 기준 모호 → **가이드 재정의 필요** |
| 0.40~0.60 | moderate |
| 0.60~0.80 | substantial |
| >0.80 | almost perfect |

요소별로 kappa가 낮으면 그 요소의 정의가 라벨러마다 다르게 해석된다는 뜻.
LENGTH·CONSTRAINT처럼 경계가 애매한 요소에서 자주 발생 → GUIDE에 예시 추가.

## 이어서
```bash
# gold.csv를 ko_vs_kc harness로
cp data/gold.csv ../ko_vs_kc/data/gold.csv
cd ../ko_vs_kc
python src/baseline.py --data data/gold.csv
python src/train_eval.py --model monologg/koelectra-base-v3-discriminator --tag ko --data data/gold.csv
python src/train_eval.py --model beomi/KcELECTRA-base --tag kc --data data/gold.csv
python src/compare.py
```

## 주의
- LLM 사전 라벨은 **초안**일 뿐. 사람 검수 없이 gold로 쓰면 LLM 편향이 학습에 전이됨.
- 요소별 양성(누락) 샘플이 너무 적으면 F1 불안정 → 요소당 수백 개 이상 확보 권장.
- gold 다수결에서 동률은 보수적으로 누락(1) 처리.
