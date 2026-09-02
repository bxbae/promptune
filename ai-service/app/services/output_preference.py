"""이번 프롬프트에 명시적으로 언급된 출력 형식을 감지하고, 감지 안 된
필드는 사용자의 과거 습관(backend에서 전달받은 habit_output_preferences)
으로 채우는 모듈.

2026-09-02: 승득님 설계(KcELECTRA 진단 다음, HCX 추천 생성 이전 단계) 기준으로
구현. 명시적 감지가 항상 우선이고, 습관 데이터는 명시된 게 없을 때만 쓰는
폴백이다.
"""

import re

_FORMAT_PATTERNS: dict[str, tuple[str, ...]] = {
    "table": ("표로", "표 형태로", "테이블로", "표로 정리"),
    "markdown": ("마크다운으로", "마크다운 형식"),
    "checklist": ("체크리스트", "체크리스트 형식"),
    "json": ("json으로", "JSON으로", "json 형식"),
    "code_only": ("코드만",),
}

_STRUCTURE_PATTERNS: dict[str, tuple[str, ...]] = {
    "title_body_conclusion": (
        "제목/본문/결론",
        "제목-본문-결론",
        "서론 본론 결론",
        "서론-본론-결론",
    ),
}

_DETAIL_PATTERNS: dict[str, tuple[str, ...]] = {
    "concise": ("간단하게", "간략하게", "짧게", "간단히"),
    "detailed": ("자세히", "상세하게", "구체적으로", "자세하게"),
}

_LENGTH_RE = re.compile(r"(\d+)\s*(줄|문장|개)\s*(로|으로)?\s*(요약|정리)")


def detect_output_preferences(text: str) -> dict[str, str | None]:
    prefs: dict[str, str | None] = {
        "format": None,
        "length": None,
        "structure": None,
        "detail_level": None,
    }

    for key, patterns in _FORMAT_PATTERNS.items():
        if any(p in text for p in patterns):
            prefs["format"] = key
            break

    for key, patterns in _STRUCTURE_PATTERNS.items():
        if any(p in text for p in patterns):
            prefs["structure"] = key
            break

    length_match = _LENGTH_RE.search(text)
    if length_match:
        unit = "lines" if length_match.group(2) == "줄" else "items"
        prefs["length"] = f"{length_match.group(1)}_{unit}"

    for key, patterns in _DETAIL_PATTERNS.items():
        if any(p in text for p in patterns):
            prefs["detail_level"] = key
            break

    return prefs


def merge_with_habit_fallback(
    explicit: dict[str, str | None],
    habit: dict[str, str | None] | None,
) -> dict[str, str | None]:
    """명시적 감지가 우선. null인 필드만 습관 데이터로 채운다."""
    if not habit:
        return explicit

    merged = dict(explicit)
    for key in ("format", "length", "structure", "detail_level"):
        if merged.get(key) is None and habit.get(key) is not None:
            merged[key] = habit[key]
    return merged
    