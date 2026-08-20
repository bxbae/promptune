from __future__ import annotations

from dataclasses import dataclass, field

from app.services.validation.rule_validator import validate_rules
from app.services.validation.semantic_validator import validate_semantic


DEFAULT_SEMANTIC_THRESHOLD = 0.65


@dataclass
class FinalValidationResult:
    passed: bool
    rule_ok: bool
    semantic_ok: bool
    semantic_score: float
    facts_preserved: bool
    issues: list[str] = field(default_factory=list)


def validate_response(
    original: str,
    generated: str,
    semantic_threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
) -> FinalValidationResult:
    rule_result = validate_rules(
        original=original,
        generated=generated,
    )

    semantic_result = validate_semantic(
        original=original,
        generated=generated,
        threshold=semantic_threshold,
    )

    rule_ok = rule_result.passed
    semantic_ok = semantic_result.semantic_ok

    issues = [
        *rule_result.issues,
        *semantic_result.issues,
    ]

    passed = rule_ok and semantic_ok

    return FinalValidationResult(
        passed=passed,
        rule_ok=rule_ok,
        semantic_ok=semantic_ok,
        semantic_score=semantic_result.score,
        facts_preserved=rule_result.facts_preserved,
        issues=issues,
)