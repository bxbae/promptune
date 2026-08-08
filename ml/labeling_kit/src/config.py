"""공통 설정: 8요소 정의, LLM 라벨링 프롬프트, 스키마."""

ELEMENTS = ["TASK", "AUDIENCE", "CONTEXT", "FORMAT", "TONE", "LENGTH", "CONSTRAINT", "EXAMPLE"]

ELEMENT_DESC = {
    "TASK":       "할 작업/동작 (요약·작성·번역 등)",
    "AUDIENCE":   "대상 독자·수신자",
    "CONTEXT":    "배경·상황 정보",
    "FORMAT":     "출력 형식 (표·목록·이메일 등)",
    "TONE":       "어조·말투",
    "LENGTH":     "분량 (글자수·줄수·문단수)",
    "CONSTRAINT": "제약·조건 (하지 말 것/반드시 포함할 것)",
    "EXAMPLE":    "예시·참고자료",
}

# 라벨 규약: 포함=0, 누락=1, 애매하면 누락(1)으로 통일 (라벨러 간 일관성 확보)
LABELING_GUIDE = "명시적으로 포함되면 0, 없거나 애매하면 1."


def build_prompt(text: str) -> str:
    """LLM에 넘길 라벨링 프롬프트. JSON만 반환하도록 강제."""
    lines = "\n".join(f"  - {e}: {ELEMENT_DESC[e]}" for e in ELEMENTS)
    keys = ", ".join(f'"{e}":0' for e in ELEMENTS)
    return f"""다음 사용자 프롬프트에서 8개 요소 각각이 명시적으로 포함됐는지 판정해.
규칙: {LABELING_GUIDE}
요소:
{lines}

프롬프트: "{text}"

설명 없이 JSON 한 줄만 출력. 예: {{{keys}}}"""
