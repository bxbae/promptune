from __future__ import annotations

from typing import Final


ELEMENTS: Final[tuple[str, ...]] = (
    "TASK",
    "AUDIENCE",
    "CONTEXT",
    "FORMAT",
    "TONE",
    "LENGTH",
    "CONSTRAINT",
    "EXAMPLE",
)


_CANDIDATE_BANK: Final[dict[str, tuple[str, ...]]] = {
    "TASK": (
        "핵심 내용을 요약해줘",
        "오류와 개선점을 검토해줘",
        "주요 결정사항과 후속 조치를 정리해줘",
        "핵심 쟁점을 정리해줘",
        "실행해야 할 항목을 정리해줘",
    ),
    "AUDIENCE": (
        "임원진을 대상으로",
        "실무 담당자를 대상으로",
        "처음 사용하는 고객을 대상으로",
        "내부 팀원을 대상으로",
        "외부 협력사를 대상으로",
    ),
    "CONTEXT": (
        "의사결정을 위한 자료라는 배경을 반영해서",
        "내부 공유용 자료라는 배경을 반영해서",
        "고객 안내용 자료라는 배경을 반영해서",
        "내부 공유와 후속 업무 진행을 위한 목적으로 사용할 거야.",
        "업무 검토를 위한 자료라는 배경을 반영해서",
    ),
    "FORMAT": (
        "표 형식으로 정리해서",
        "불릿 목록으로 정리해서",
        "제목과 소제목이 있는 마크다운 구조로 작성해서",
        "비교 표 형식으로 정리해서",
        "질문과 답변 형식으로 정리해서",
    ),
    "TONE": (
        "정중하고 친절한 어조로 작성해서",
        "전문적이고 객관적인 어조로 작성해서",
        "간결하고 명확한 어조로 작성해서",
        "격식 있고 공손한 어조로 작성해서",
        "친근하지만 전문적인 어조로 작성해서",
    ),
    "LENGTH": (
        "3문장 이내로 작성해서",
        "5문장 이내로 작성해서",
        "200자 이내로 작성해서",
        "1페이지 이내로 작성해서",
        "핵심 내용만 간단히 작성해서",
    ),
    "CONSTRAINT": (
        "확인되지 않은 내용은 추정하지 말고",
        "원문의 수치와 고유명사는 변경하지 말고",
        "개인정보는 포함하지 말고",
        "중복 내용은 제외하고",
        "제공된 정보 범위 안에서만 작성해서",
    ),
    "EXAMPLE": (
        "완성형 문장 예시 1개를 포함해서",
        "입력과 출력 예시를 한 쌍 포함해서",
        "실제 업무 상황을 가정한 예시를 포함해서",
        "좋은 예와 나쁜 예를 각각 1개씩 포함해서",
        "구체적인 결과 예시 1개를 함께 제시해서",
    ),
}


def _move_to_front(
    candidates: list[str],
    preferred: str | None,
) -> list[str]:
    if not preferred or preferred not in candidates:
        return candidates

    return [
        preferred,
        *[candidate for candidate in candidates if candidate != preferred],
    ]


def get_candidates(
    element: str,
    text: str,
    context: str | None = None,
    limit: int = 3,
) -> list[str]:
    key = element.strip().upper()

    if key not in _CANDIDATE_BANK:
        raise ValueError(f"Unsupported element: {element}")

    if limit < 1:
        raise ValueError("limit must be at least 1")

    candidates = list(_CANDIDATE_BANK[key])

    normalized = " ".join(
        part
        for part in (
            text,
            context or "",
        )
        if part
    ).lower()

    preferred: str | None = None

    if key == "TASK":
        if "회의" in normalized:
            preferred = "주요 결정사항과 후속 조치를 정리해줘"
        elif any(word in normalized for word in ("검토", "오류", "문제")):
            preferred = "오류와 개선점을 검토해줘"
        elif any(word in normalized for word in ("자료", "문서", "내용")):
            preferred = "핵심 내용을 요약해줘"

    elif key == "AUDIENCE":
        if any(word in normalized for word in ("고객", "사용자", "서비스", "제품")):
            preferred = "처음 사용하는 고객을 대상으로"
        elif any(word in normalized for word in ("전략", "기획", "보고서", "경영")):
            preferred = "임원진을 대상으로"
        elif any(word in normalized for word in ("팀", "회의", "프로젝트")):
            preferred = "내부 팀원을 대상으로"

    elif key == "CONTEXT":
        if any(word in normalized for word in ("시장", "전략", "기획", "보고서")):
            preferred = "의사결정을 위한 자료라는 배경을 반영해서"
        elif any(word in normalized for word in ("고객", "안내", "서비스")):
            preferred = "고객 안내용 자료라는 배경을 반영해서"
        elif any(word in normalized for word in ("회의", "회고")):
            preferred = "내부 공유와 후속 업무 진행을 위한 목적으로 사용할 거야."

    elif key == "FORMAT":
        if any(word in normalized for word in ("비교", "경쟁사", "가격", "기능")):
            preferred = "비교 표 형식으로 정리해서"
        elif any(word in normalized for word in ("회의", "결정", "할 일")):
            preferred = "불릿 목록으로 정리해서"
        elif any(word in normalized for word in ("보고서", "실적", "현황")):
            preferred = "표 형식으로 정리해서"

    elif key == "TONE":
        if any(word in normalized for word in ("사과", "장애", "고객")):
            preferred = "정중하고 친절한 어조로 작성해서"
        elif any(word in normalized for word in ("거래처", "공문", "계약")):
            preferred = "격식 있고 공손한 어조로 작성해서"
        elif any(word in normalized for word in ("팀", "공지")):
            preferred = "친근하지만 전문적인 어조로 작성해서"

    elif key == "LENGTH":
        if any(word in normalized for word in ("메신저", "문구", "알림")):
            preferred = "200자 이내로 작성해서"
        elif any(word in normalized for word in ("요약", "회의")):
            preferred = "5문장 이내로 작성해서"
        elif "보고서" in normalized:
            preferred = "1페이지 이내로 작성해서"

    elif key == "CONSTRAINT":
        if any(word in normalized for word in ("고객", "개인정보", "데이터")):
            preferred = "개인정보는 포함하지 말고"
        elif any(word in normalized for word in ("계약", "수치", "원문")):
            preferred = "원문의 수치와 고유명사는 변경하지 말고"
        elif any(word in normalized for word in ("시장", "전망", "예측")):
            preferred = "확인되지 않은 내용은 추정하지 말고"

    elif key == "EXAMPLE":
        if any(word in normalized for word in ("프로젝트", "기술", "api")):
            preferred = "입력과 출력 예시를 한 쌍 포함해서"
        elif any(word in normalized for word in ("메일", "고객", "답변")):
            preferred = "완성형 문장 예시 1개를 포함해서"

    candidates = _move_to_front(
        candidates,
        preferred,
    )

    return candidates[:limit]
