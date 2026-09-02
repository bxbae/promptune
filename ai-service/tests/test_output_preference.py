from app.services.output_preference import (
    detect_output_preferences,
    merge_with_habit_fallback,
)


def test_detect_output_preferences_table():
    result = detect_output_preferences("이거 표로 정리해줘")
    assert result["format"] == "table"


def test_detect_output_preferences_none():
    result = detect_output_preferences("이거 정리해줘")
    assert result["format"] is None
    assert result["length"] is None
    assert result["structure"] is None
    assert result["detail_level"] is None


def test_detect_output_preferences_length():
    result = detect_output_preferences("5줄로 요약해줘")
    assert result["length"] == "5_lines"


def test_detect_output_preferences_detail_level():
    assert detect_output_preferences("간단하게 알려줘")["detail_level"] == "concise"
    assert detect_output_preferences("자세히 설명해줘")["detail_level"] == "detailed"


def test_merge_prefers_explicit_over_habit():
    explicit = {"format": "table", "length": None, "structure": None, "detail_level": None}
    habit = {"format": "markdown", "length": None, "structure": None, "detail_level": "concise"}
    merged = merge_with_habit_fallback(explicit, habit)
    assert merged["format"] == "table"          # 명시값이 이김
    assert merged["detail_level"] == "concise"   # 명시 없으면 습관값


def test_merge_with_no_habit_data():
    explicit = {"format": None, "length": None, "structure": None, "detail_level": None}
    merged = merge_with_habit_fallback(explicit, None)
    assert merged == explicit
    