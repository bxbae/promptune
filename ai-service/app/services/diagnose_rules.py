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
    # 요청/명령 표현
    "요약해조": "요약해줘",
    "정리헤줘": "정리해줘",
    "작성헤줘": "작성해줘",
    "검토헤줘": "검토해줘",
    "해줄레": "해줄래",

    # 조사/어미
    "한태": "한테",
    "드림니다": "드립니다",
    "부탁드림니다": "부탁드립니다",

    # 자주 발생하는 맞춤법 오류
    "됬습니다": "됐습니다",
    "됬어요": "됐어요",
    "되요": "돼요",
    "몇일": "며칠",

    "보내주새요": "보내 주세요",
}


def detect_task_type(text: str) -> str:
    for task_type, hints in TASK_TYPE_HINTS.items():
        if any(hint in text for hint in hints):
            return task_type

    return "email"


def detect_typos(text: str) -> list[Typo]:
    found: list[Typo] = []
    matched_ranges: list[tuple[int, int]] = []

    # 긴 표현부터 검사해서
    # "부탁드림니다"와 "드림니다" 같은 중복 검출을 방지
    for wrong, correct in sorted(
        TYPO_DICT.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        start = text.find(wrong)

        while start != -1:
            end = start + len(wrong)

            overlaps = any(
                start < matched_end and end > matched_start
                for matched_start, matched_end in matched_ranges
            )

            if not overlaps:
                found.append(Typo(span=wrong, suggest=correct))
                matched_ranges.append((start, end))
                break

            start = text.find(wrong, start + 1)

    return found


def needs_internal_docs(task_type: str) -> bool:
    return task_type.endswith("_internal") or task_type == "application"