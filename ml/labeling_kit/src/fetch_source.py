"""
원문 프롬프트 수집기. MySQL 또는 CSV에서 text를 읽어
라벨링 입력용 CSV(id,text)로 표준화.

MySQL 사용 예:
  python src/fetch_source.py --source mysql \
    --table prompts --text-col original_text --id-col id \
    --host localhost --port 3306 --db promptune --user root --password ***

CSV 사용 예 (이미 뽑아둔 파일):
  python src/fetch_source.py --source csv --in data/raw.csv --text-col text
"""
import argparse, csv, os, re, sys

# ---- 개인정보 마스킹 (학습 전 비식별화) ----
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"01[016-9][-\s]?\d{3,4}[-\s]?\d{4}")
RRN   = re.compile(r"\d{6}[-\s]?\d{7}")  # 주민번호 패턴


def mask_pii(s: str) -> str:
    s = EMAIL.sub("[EMAIL]", s)
    s = PHONE.sub("[PHONE]", s)
    s = RRN.sub("[RRN]", s)
    return s


def clean(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)      # 반복 공백 정리
    return mask_pii(s)


def from_csv(path, text_col, id_col):
    with open(path, encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            t = clean(row.get(text_col, ""))
            if not t:
                continue
            rid = row.get(id_col) if id_col and id_col in row else str(i)
            yield rid, t


def from_mysql(a):
    try:
        import pymysql
    except ImportError:
        sys.exit("pip install pymysql 필요")
    conn = pymysql.connect(host=a.host, port=a.port, user=a.user,
                           password=a.password, db=a.db, charset="utf8mb4")
    idcol = a.id_col or "id"
    with conn.cursor() as cur:
        cur.execute(f"SELECT {idcol}, {a.text_col} FROM {a.table}")
        for rid, txt in cur.fetchall():
            t = clean(txt)
            if t:
                yield str(rid), t
    conn.close()


def main(a):
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    src = from_csv(a.in_path, a.text_col, a.id_col) if a.source == "csv" else from_mysql(a)
    n = 0
    seen = set()
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "text"])
        for rid, t in src:
            if t in seen:        # 중복 원문 제거
                continue
            seen.add(t)
            w.writerow([rid, t])
            n += 1
            if a.limit and n >= a.limit:
                break
    print(f"wrote {n} unique prompts -> {a.out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["csv", "mysql"], required=True)
    ap.add_argument("--out", default="data/to_label.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--text-col", default="text")
    ap.add_argument("--id-col", default=None)
    # csv
    ap.add_argument("--in", dest="in_path", default="data/raw.csv")
    # mysql
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=3306)
    ap.add_argument("--db", default="promptune")
    ap.add_argument("--user", default="root")
    ap.add_argument("--password", default="")
    ap.add_argument("--table", default="prompts")
    main(ap.parse_args())
