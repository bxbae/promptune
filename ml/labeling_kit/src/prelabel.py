"""
LLM 사전 라벨링. to_label.csv(id,text) → prelabeled.csv(id,text,TASK..EXAMPLE).

백엔드 3종:
  --backend claude   : Anthropic API (ANTHROPIC_API_KEY)
  --backend clova    : HyperCLOVA X (CLOVA_API_KEY, CLOVA_APIGW_KEY, CLOVA_HOST)
  --backend rule     : 오프라인 규칙 (API 없이 초벌; baseline 사전 재사용)

JSON 파싱 실패 시 해당 요소는 보수적으로 1(누락)로 채우고 need_review=1 표시.
"""
import argparse, csv, json, os, re, sys, time
from config import ELEMENTS, build_prompt

# ---------- 공통 JSON 파서 ----------
def parse_labels(raw: str):
    """LLM 출력에서 8요소 JSON을 뽑아 [0/1]*8 반환. 실패하면 None."""
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    out = []
    for e in ELEMENTS:
        v = d.get(e, 1)
        out.append(1 if int(v) == 1 else 0)
    return out


# ---------- 백엔드: Claude ----------
def label_claude(text, model):
    import urllib.request
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY 필요")
    body = json.dumps({
        "model": model,
        "max_tokens": 200,
        "messages": [{"role": "user", "content": build_prompt(text)}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"content-type": "application/json", "x-api-key": key,
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    txt = "".join(b.get("text", "") for b in d.get("content", []))
    return parse_labels(txt)


# ---------- 백엔드: HyperCLOVA X ----------
def label_clova(text, model):
    import urllib.request
    host = os.environ.get("CLOVA_HOST", "")
    key = os.environ.get("CLOVA_API_KEY", "")
    if not (host and key):
        sys.exit("CLOVA_HOST, CLOVA_API_KEY 필요")
    body = json.dumps({
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "maxTokens": 200, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(
        f"{host}/testapp/v1/chat-completions/{model}", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    txt = d.get("result", {}).get("message", {}).get("content", "")
    return parse_labels(txt)


# ---------- 백엔드: 규칙 (오프라인) ----------
RULE_CUES = {
    "TASK":     ["요약","초안","리뷰","작성","번역","설명","정리","글","사과","공지","만들","써","해줘","처리"],
    "AUDIENCE": ["님께","담당자","대상","한테","에게","보고용","고객","윗분","받는 사람"],
    "CONTEXT":  ["관련","바탕","기준","상황","건과","접수","때문","이유"],
    "FORMAT":   ["형식","목록","마크다운","문단","리스트","표","불릿","번호"],
    "TONE":     ["어조","친근","톤","단호","느낌","전문","정중","말투","분위기"],
    "LENGTH":   ["자 이내","줄","문단","자 내외","항목","길지","분량","간단","짧"],
    "CONSTRAINT":["빼고","포함","없이","존댓말","말고","추려","지켜","조심","꼭"],
    "EXAMPLE":  ["처럼","참고","예시","템플릿","스타일","샘플","전에"],
}

def label_rule(text, model=None):
    return [0 if any(c in text for c in RULE_CUES[e]) else 1 for e in ELEMENTS]


BACKENDS = {"claude": label_claude, "clova": label_clova, "rule": label_rule}


def main(a):
    fn = BACKENDS[a.backend]
    rows = list(csv.DictReader(open(a.in_path, encoding="utf-8")))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "text"] + ELEMENTS + ["need_review"])
        for i, row in enumerate(rows, 1):
            text = row["text"]
            try:
                labels = fn(text, a.model)
            except Exception as e:
                print(f"  [{i}] error: {e}", file=sys.stderr)
                labels = None
            need_review = 0
            if labels is None:            # 파싱/호출 실패 → 보수적 처리 + 검수 플래그
                labels = [1] * len(ELEMENTS)
                need_review = 1
            w.writerow([row.get("id", i), text] + labels + [need_review])
            if a.backend != "rule":
                time.sleep(a.sleep)       # rate limit 완화
            if i % 25 == 0:
                print(f"  labeled {i}/{len(rows)}")
    print(f"done -> {a.out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=list(BACKENDS), default="rule")
    ap.add_argument("--in", dest="in_path", default="data/to_label.csv")
    ap.add_argument("--out", default="data/prelabeled.csv")
    ap.add_argument("--model", default="claude-sonnet-4-6",
                    help="claude: 모델명 / clova: HCX-003 등")
    ap.add_argument("--sleep", type=float, default=0.3)
    main(ap.parse_args())
