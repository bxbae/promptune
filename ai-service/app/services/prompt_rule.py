"""Phase 2-B Prompt Rule.

V6 진단 결과와 사용자 Preference를 받아
최종 프롬프트를 생성하지 않고 적용할 개선 전략만 결정한다.

이 모듈은 LLM, RAG, Web Search를 호출하지 않는 deterministic rule이다.
"""

from app.schemas.models import ELEMENTS, PromptRuleRequest, PromptRuleResponse


ROLE_HINTS = {
    "report": "업무 보고서 작성 전문가",
    "report_internal": "사내 보고 문서 작성 전문가",
}


def apply_prompt_rule(request: PromptRuleRequest) -> PromptRuleResponse:
    """V6 진단 + Preference를 Prompt Rule 전략으로 변환한다."""

    missing_elements = [
        element
        for element in ELEMENTS
        if request.missing.get(element) == 1
    ]

    # fast는 전략을 최소화하고, keep은 원문 구조 변경을 최소화한다.
    # 따라서 첫 MVP에서는 accurate + improve 조합에서만 적극 전략을 허용한다.
    allow_active_improvement = (
        request.preference.speed == "accurate"
        and request.preference.preserve == "improve"
    )

    role_hint = ROLE_HINTS.get(request.task_type)
    use_role = allow_active_improvement and role_hint is not None

    return PromptRuleResponse(
        missing_elements=missing_elements,
        use_role=use_role,
        role_hint=role_hint if use_role else None,
        decompose_task=False,
        use_positive_instruction=allow_active_improvement,
        use_few_shot=False,
    )