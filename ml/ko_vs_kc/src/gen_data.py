"""
8요소 누락 탐지용 합성 데이터 생성기 (멀티라벨).

8요소 (prompt engineering 관점의 핵심 구성요소):
  0 TASK     무엇을 해야 하는지 (동작/작업)
  1 AUDIENCE 대상 독자/수신자
  2 CONTEXT  배경/상황 정보
  3 FORMAT   출력 형식 (이메일/표/목록 등)
  4 TONE     어조 (정중/캐주얼/공식)
  5 LENGTH   분량 (글자/문단/줄 수)
  6 CONSTRAINT 제약/조건 (하지 말 것, 반드시 포함할 것)
  7 EXAMPLE  예시/참고자료

각 샘플: 한국어 프롬프트 문장 + 8차원 라벨(1=누락, 0=포함).
구어체·오타를 섞어 Kc의 강점이 드러날 여지를 준다.
"""
import csv, random, argparse, os

random.seed(42)

# ---- 요소별 표현 조각 (포함될 때 문장에 들어가는 구절) ----
TASK = [
    "회의록 요약해줘", "이메일 초안 써줘", "코드 리뷰해줘", "보고서 작성해줘",
    "번역해줘", "제품 설명 만들어줘", "일정 정리해줘", "블로그 글 써줘",
    "사과문 작성해줘", "공지사항 만들어줘",
]
AUDIENCE = [
    "팀장님께", "고객사 담당자에게", "신입사원 대상으로", "학부모님께",
    "임원진 보고용으로", "일반 사용자에게", "개발팀한테", "투자자 대상으로",
]
CONTEXT = [
    "어제 있었던 장애 관련해서", "이번 분기 실적을 바탕으로", "지난주 미팅 내용 기준으로",
    "신규 기능 출시 상황에서", "계약 갱신 건과 관련해서", "고객 불만이 접수된 상황인데",
]
FORMAT = [
    "표 형식으로", "불릿 목록으로", "이메일 형식으로", "마크다운으로",
    "3문단 구성으로", "번호 매긴 리스트로",
]
TONE = [
    "정중한 어조로", "친근하게", "공식적인 톤으로", "간결하고 단호하게",
    "따뜻한 느낌으로", "전문적으로",
]
LENGTH = [
    "300자 이내로", "5줄 정도로", "한 문단으로", "500자 내외로",
    "3~4줄로 짧게", "10개 항목으로",
]
CONSTRAINT = [
    "전문용어는 빼고", "숫자는 반드시 포함해서", "부정적 표현 없이",
    "존댓말로만", "회사명은 언급하지 말고", "핵심만 추려서",
]
EXAMPLE = [
    "지난번 공지처럼", "첨부한 샘플 참고해서", "아래 예시 형식대로",
    "기존 템플릿 기반으로", "이전 보고서 스타일로",
]

POOLS = [TASK, AUDIENCE, CONTEXT, FORMAT, TONE, LENGTH, CONSTRAINT, EXAMPLE]
NAMES = ["TASK","AUDIENCE","CONTEXT","FORMAT","TONE","LENGTH","CONSTRAINT","EXAMPLE"]

# 구어체 꼬리말 / 오타 주입으로 자연스러운 노이즈 추가
FILLERS = ["", " 좀", " 부탁해요", " 해줄래?", "!!", " ㅜㅜ", " ㄱㄱ", "..."]
TYPO_MAP = {"해줘": "해조", "해줄래": "해줄레", "부탁": "부착", "정중": "정즁", "리뷰": "리부"}

# 요소를 '포함'하되 키워드 사전에 안 걸리는 우회 표현(패러프레이즈).
# baseline이 규칙만으로 완벽히 못 맞히게 해서, 신경망이 넘어야 할 현실적 floor를 만든다.
PARAPHRASE = {
    0: ["이거 좀 만져줘", "손 좀 봐줘", "처리 좀"],                    # TASK
    1: ["윗분들이 볼 거야", "받는 사람 생각해서", "그쪽에 보낼 거라"],   # AUDIENCE
    2: ["요즘 돌아가는 상황 알지?", "그 일 있잖아", "전에 얘기한 거"],   # CONTEXT
    3: ["보기 좋게 정리해서", "깔끔한 모양으로", "읽기 편하게"],        # FORMAT
    4: ["느낌 살려서", "분위기 맞춰서", "말투 신경 써서"],            # TONE
    5: ["너무 길지 않게", "적당한 분량으로", "간단히"],               # LENGTH
    6: ["이건 꼭 지켜줘", "이 부분 조심해서", "빼먹지 말고"],          # CONSTRAINT
    7: ["전에 했던 거 있잖아", "그때 그거처럼", "샘플 있어"],          # EXAMPLE
}


def maybe_typo(s, p=0.15):
    if random.random() < p:
        for k, v in TYPO_MAP.items():
            if k in s and random.random() < 0.5:
                s = s.replace(k, v, 1)
    return s


def make_sample():
    # 각 요소를 확률적으로 포함(0) 또는 누락(1). TASK는 대부분 포함시켜 현실성 유지.
    present = []
    labels = []
    for i in range(8):
        keep_prob = 0.75 if i == 0 else 0.5
        if random.random() < keep_prob:
            # 30% 확률로 키워드 사전에 안 걸리는 우회 표현 사용 → baseline 난이도↑
            if random.random() < 0.3:
                present.append(random.choice(PARAPHRASE[i]))
            else:
                present.append(random.choice(POOLS[i]))
            labels.append(0)  # 포함
        else:
            labels.append(1)  # 누락
    if not present:  # 전부 누락이면 최소 TASK 하나 넣음
        present.append(random.choice(TASK)); labels[0] = 0
    random.shuffle(present)
    text = " ".join(present) + random.choice(FILLERS)
    text = maybe_typo(text)
    return text, labels


def main(n, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text"] + NAMES)
        for _ in range(n):
            t, labs = make_sample()
            w.writerow([t] + labs)
    print(f"wrote {n} rows -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--out", default="data/synth.csv")
    a = ap.parse_args()
    main(a.n, a.out)
