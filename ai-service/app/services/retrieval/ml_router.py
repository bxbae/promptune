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


def classify_ml_retrieval_route(query: str) -> str:
    if _is_restricted(query):
        return "not_rag_or_restricted"

    if _is_explicit_internal_rag(query):
        return "internal_rag"

    return _ROUTER.predict(query)
