from __future__ import annotations

import re
from dataclasses import dataclass, field


_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

_MAX_LENGTH_RE = re.compile(
    r"(?P<count>\d+)\s*(?:자|글자)\s*(?:이내|이하)"
)

_ITEM_COUNT_RE = re.compile(
    r"(?P<count>\d+)\s*(?:"
    r"개(?:의)?\s*(?:항목|내용|포인트)"
    r"|개\s*(?:로|으로)\s*(?:정리|작성|제시|요약)"
    r"|가지(?:의)?\s*(?:항목|내용|포인트)"
    r"|가지\s*(?:로|으로)\s*(?:정리|작성|제시|요약)"
    r")"
)

_LIST_ITEM_RE = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.)]\s+)",
    re.MULTILINE,
)

_MARKDOWN_TABLE_SEPARATOR_RE = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)


@dataclass
class RuleValidationResult:
    length_ok: bool = True
    item_count_ok: bool = True
    format_ok: bool = True
    facts_preserved: bool = True
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.length_ok
            and self.item_count_ok
            and self.format_ok
            and self.facts_preserved
        )


def _validate_length(
    original: str,
    generated: str,
    issues: list[str],
) -> bool:
    match = _MAX_LENGTH_RE.search(original)

    if match is None:
        return True

    max_length = int(match.group("count"))
    actual_length = len(generated)

    if actual_length <= max_length:
        return True

    issues.append(
        f"길이 조건 위반: 최대 {max_length}자, 실제 {actual_length}자"
    )
    return False


def _validate_item_count(
    original: str,
    generated: str,
    issues: list[str],
) -> bool:
    match = _ITEM_COUNT_RE.search(original)

    if match is None:
        return True

    expected_count = int(match.group("count"))
    actual_count = len(_LIST_ITEM_RE.findall(generated))

    if actual_count == expected_count:
        return True

    issues.append(
        f"항목 개수 조건 위반: 요청 {expected_count}개, 실제 {actual_count}개"
    )
    return False


def _table_requested(original: str) -> bool:
    return (
        "표 형식" in original
        or "표형식" in original
        or "표로" in original
    )


def _has_markdown_table(generated: str) -> bool:
    lines = [
        line.strip()
        for line in generated.splitlines()
        if line.strip()
    ]

    if len(lines) < 2:
        return False

    for index in range(1, len(lines)):
        if not _MARKDOWN_TABLE_SEPARATOR_RE.match(lines[index]):
            continue

        previous_line = lines[index - 1]

        if "|" in previous_line:
            return True

    return False


def _validate_format(
    original: str,
    generated: str,
    issues: list[str],
) -> bool:
    if not _table_requested(original):
        return True

    if _has_markdown_table(generated):
        return True

    issues.append("형식 조건 위반: 표 형식이 요청되었지만 표가 없습니다.")
    return False


def _constraint_number_spans(original: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []

    for pattern in (_MAX_LENGTH_RE, _ITEM_COUNT_RE):
        for match in pattern.finditer(original):
            number_start = match.start("count")
            number_end = match.end("count")
            spans.append((number_start, number_end))

    return spans


def _fact_numbers(original: str) -> set[str]:
    constraint_spans = _constraint_number_spans(original)
    facts: set[str] = set()

    for match in _NUMBER_RE.finditer(original):
        start, end = match.span()

        is_constraint_number = any(
            start >= span_start and end <= span_end
            for span_start, span_end in constraint_spans
        )

        if not is_constraint_number:
            facts.add(match.group())

    return facts


def _validate_fact_numbers(
    original: str,
    generated: str,
    issues: list[str],
) -> bool:
    original_numbers = _fact_numbers(original)

    if not original_numbers:
        return True

    generated_numbers = set(_NUMBER_RE.findall(generated))
    missing_numbers = original_numbers - generated_numbers

    if not missing_numbers:
        return True

    issues.append(
        "원문 숫자 누락: " + ", ".join(sorted(missing_numbers))
    )
    return False


def validate_rules(
    original: str,
    generated: str,
) -> RuleValidationResult:
    issues: list[str] = []

    length_ok = _validate_length(original, generated, issues)
    item_count_ok = _validate_item_count(original, generated, issues)
    format_ok = _validate_format(original, generated, issues)
    facts_preserved = _validate_fact_numbers(
        original,
        generated,
        issues,
    )

    return RuleValidationResult(
        length_ok=length_ok,
        item_count_ok=item_count_ok,
        format_ok=format_ok,
        facts_preserved=facts_preserved,
        issues=issues,
    )