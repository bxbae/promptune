"""
5번 통합 진단 (mock).

판정 기준:
문장에 요소가 단순히 존재하는지가 아니라,
해당 요청을 수행하는 데 추가 보완이 필요한지를 판단한다.

실제 KcELECTRA가 연결되더라도 mock은 삭제하지 않는다.
USE_REAL_DIAGNOSIS=false 환경에서는 이 구현을 사용한다.
"""

from app.schemas.models import DiagnoseRequest, DiagnoseResponse, ELEMENTS
from app.services.diagnose_rules import (
    detect_task_type,
    detect_typos,
    needs_internal_docs,
)


# 요소가 명시적으로 존재하는지 확인하는 mock용 힌트
_PRESENT_HINTS = {
    "TASK": [
        "요약",
        "번역",
        "작성",
        "정리",
        "만들",
        "써",
        "리뷰",
        "다듬",
        "설명",
        "안내",
    ],
    "AUDIENCE": [
        "님께",
        "님한테",
        "대상",
        "고객",
        "임원",
        "팀장",
        "학부모",
        "신입",
        "개발팀",
        "투자자",
        "사용자",
        "담당자",
    ],
    "CONTEXT": [
        "관련",
        "상황",
        "지난",
        "이번",
        "건과",
        "출시",
        "장애",
        "불만",
        "갱신",
        "접수",
    ],
    "FORMAT": [
        "표",
        "목록",
        "불릿",
        "마크다운",
        "문단",
        "줄로",
        "항목",
        "메일",
        "문구",
    ],
    "TONE": [
        "정중",
        "친근",
        "따뜻",
        "캐주얼",
        "전문적",
        "존댓말",
        "간결",
        "부드럽",
    ],
    "LENGTH": [
        "자",
        "줄",
        "문단",
        "이내",
        "내외",
        "짧게",
        "핵심만",
        "개",
    ],
    "CONSTRAINT": [
        "빼고",
        "말고",
        "없이",
        "꼭",
        "제외",
        "포함",
        "반드시",
    ],
    "EXAMPLE": [
        "샘플",
        "예시",
        "처럼",
        "템플릿",
        "기반",
        "그때",
        "지난번",
        "양식",
    ],
}


# 해당 작업에서는 명시되지 않아도 보완이 필요하지 않을 수 있는 요소
_OPTIONAL_BY_TASK = {
    "번역": ["CONTEXT", "EXAMPLE"],
    "요약": ["EXAMPLE"],
    "다듬": ["FORMAT", "EXAMPLE", "LENGTH"],
}


def _optional_elements(text: str) -> set[str]:
    optional: set[str] = set()

    for keyword, elements in _OPTIONAL_BY_TASK.items():
        if keyword in text:
            optional.update(elements)

    return optional


def diagnose(req: DiagnoseRequest) -> DiagnoseResponse:
    text = req.text

    optional = _optional_elements(text)
    missing: dict[str, int] = {}

    for element in ELEMENTS:
        present = any(
            hint in text
            for hint in _PRESENT_HINTS[element]
        )

        if present:
            missing[element] = 0
        elif element in optional:
            missing[element] = 0
        else:
            missing[element] = 1

    # KcELECTRA가 담당하지 않는 부분은 공통 Rule Engine 사용
    task_type = detect_task_type(text)
    typos = detect_typos(text)
    needs_internal = needs_internal_docs(task_type)

    return DiagnoseResponse(
        missing=missing,
        task_type=task_type,
        typos=typos,
        needs_internal_docs=needs_internal,
    )