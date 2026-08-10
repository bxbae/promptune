"""
5번 통합 진단에서 모델과 별도로 사용하는 규칙 로직.

KcELECTRA:
- 8요소 누락 여부만 담당

Rule:
- 업무 유형(task_type)
- 오탈자(typos)
- 내부문서 필요 여부
"""

from app.schemas.models import Typo


TASK_TYPE_HINTS = {
    "application": ["신청", "휴가", "경비", "구매"],
    "report_internal": ["내규", "규정", "정책 보고"],
    "notice_internal": ["정책 공지", "내부 공지"],
    "report": ["보고서", "주간보고", "실적", "피치"],
    "notice": ["공지", "안내문", "이벤트"],
    "support": ["사과", "고객", "응대", "불만"],
    "email": ["메일", "이메일"],
}


TYPO_DICT = {
    "요약해조": "요약해줘",
    "부착해요": "부탁해요",
    "해줄레": "해줄래",
}


def detect_task_type(text: str) -> str:
    for task_type, hints in TASK_TYPE_HINTS.items():
        if any(hint in text for hint in hints):
            return task_type

    return "email"


def detect_typos(text: str) -> list[Typo]:
    return [
        Typo(span=wrong, suggest=correct)
        for wrong, correct in TYPO_DICT.items()
        if wrong in text
    ]


def needs_internal_docs(task_type: str) -> bool:
    return task_type.endswith("_internal") or task_type == "application"