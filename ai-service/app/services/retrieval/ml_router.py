from __future__ import annotations

import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


APP = Path(__file__).resolve().parents[2]
TRAIN_PATH = APP / "data/rag/routing_train_242.json"


class MLRetrievalRouter:
    def __init__(self):
        self.model = Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char",
                    ngram_range=(2, 5),
                    min_df=1,
                    sublinear_tf=True,
                ),
            ),
            (
                "svc",
                LinearSVC(
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ])

    def fit(self, queries, labels):
        self.model.fit(queries, labels)
        return self

    def predict(self, query):
        return str(self.model.predict([query])[0])


def _is_restricted(query: str) -> bool:
    """
    타인의 고위험 개인정보 요청은 ML 판단보다 먼저 차단한다.
    일반적인 '내 프로필/내 조직정보' 요청은 여기서 차단하지 않는다.
    """
    text = query.strip().lower()

    other_person_markers = [
        "다른 직원",
        "다른 사용자",
        "다른 사람",
        "동료",
        "팀원",
        "직원들",
        "회사 사람",
    ]

    sensitive_markers = [
        "주민등록번호",
        "주민번호",
        "비밀번호",
        "카드번호",
        "결제번호",
        "계좌번호",
        "계좌 잔액",
        "은행 거래",
        "금융정보",
        "금융 내역",
        "신용정보",
        "인증 코드",
        "인증정보",
        "인증서 비밀번호",
        "신분증 번호",
        "집 주소",
    ]

    has_other_person = any(x in text for x in other_person_markers)
    has_sensitive_info = any(x in text for x in sensitive_markers)

    return has_other_person and has_sensitive_info


def _load_router() -> MLRetrievalRouter:
    rows = json.loads(TRAIN_PATH.read_text(encoding="utf-8"))

    router = MLRetrievalRouter()
    router.fit(
        [row["query"] for row in rows],
        [row["expected_route"] for row in rows],
    )

    return router


# 프로세스 시작 시 한 번만 학습한다.
_ROUTER = _load_router()


def _is_explicit_internal_rag(query: str) -> bool:
    """사용자가 내부/업로드 문서를 명시적으로 지칭하면 ML보다 우선한다."""
    text = query.strip().lower()

    internal_markers = [
        "내부 문서",
        "내부문서",
        "업로드한 문서",
        "업로드 문서",
        "업로드한 파일",
        "사내 문서",
        "회사 문서",
        "첨부 문서",
        "첨부파일",
    ]

    file_markers = [
        ".pdf",
        ".docx",
        ".doc",
        ".xlsx",
        ".xls",
        ".pptx",
        ".txt",
        ".md",
    ]

    return (
        any(marker in text for marker in internal_markers)
        or any(marker in text for marker in file_markers)
    )


def _is_likely_realtime_fact(query: str) -> bool:
    """
    2026-08-26: "어제 잠실 경기장의 날씨를 안내해주고 lg 트윈스의 승리여부를
    안내해줘." 같은 질의가 ML 라우터에서 no_retrieval로 잘못 분류되어
    웹검색이 아예 실행되지 않고, 모델이 완전히 지어낸 답("2023년 10월 5일
    현재, LG 트윈스는...")을 내놓는 사례가 확인됨.

    원인은 routing_train_242.json 학습 데이터가 날씨/환율/주가/일반 AI
    뉴스 카테고리 위주로만 구성돼 있고 스포츠 경기 결과 카테고리가 아예
    없었기 때문 - 242개 예시를 char n-gram + LinearSVC로 학습하는 구조라,
    학습 데이터에 없는 패턴은 우연히 가까운 다른 클래스로 분류돼버림.
    같은 취지로 확장 프로그램이 사용자 질문 뒤에 붙이는 톤/포맷 지시문
    ("3문단으로", "친근하게" 등) 유무에 따라서도 분류가 뒤집히는 게 확인돼,
    이런 취약한 경계에 기대지 않도록 결정적 규칙을 추가한다.

    학습 데이터를 보강하는 것과 별개로(방어적 이중 장치), _is_restricted/
    _is_explicit_internal_rag와 동일한 패턴으로 - 시간 표현(오늘/어제/지금/
    현재/최근 등)과 실시간성 사실 키워드(날씨/환율/주가/뉴스/경기 결과 등)가
    함께 있으면 ML 판단보다 먼저 검색 라우트로 보낸다.
    """
    text = query.strip().lower()

    time_markers = [
        "오늘", "어제", "그제", "그저께", "내일", "모레",
        "지금", "현재", "최근", "최신", "요즘", "방금",
    ]

    # "뉴스"/"속보"는 일부러 뺌 - 학습 데이터에 "최근/최신/요즘 OO 뉴스"류가
    # 이미 충분히 있어서(web_search) ML이 그 카테고리는 잘 맞히고 있었고,
    # 여기 넣으면 라벨만 external_or_realtime으로 바뀔 뿐 실제 동작(둘 다
    # search_web 호출)은 동일해서 불필요한 라벨 혼선만 생김.
    fact_markers = [
        "날씨", "기온", "환율", "주가", "지수", "시세", "코스피", "코스닥",
        "비트코인",
        "경기", "경기결과", "경기 결과", "승리여부", "승패", "스코어",
        "이겼", "졌나요", "우승", "결승",
    ]

    has_time = any(marker in text for marker in time_markers)
    has_fact = any(marker in text for marker in fact_markers)

    return has_time and has_fact


def classify_ml_retrieval_route(query: str) -> str:
    if _is_restricted(query):
        return "not_rag_or_restricted"

    if _is_explicit_internal_rag(query):
        return "internal_rag"

    if _is_likely_realtime_fact(query):
        return "external_or_realtime"

    return _ROUTER.predict(query)
