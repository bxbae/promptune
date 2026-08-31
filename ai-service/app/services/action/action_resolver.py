from __future__ import annotations

from app.services.action.action_classifier import classify_action
from app.services.action.action_types import ActionPlan, ActionType


_ROUTE_BY_ACTION = {
    ActionType.CHAT: "no_retrieval",
    ActionType.MEMORY_WRITE: "no_retrieval",
    ActionType.MEMORY_READ: "no_retrieval",
    ActionType.USER_CONTEXT: "user_context",
    ActionType.TEXT_TRANSFORM: "no_retrieval",
    ActionType.INTERNAL_DOC: "internal_rag",
    ActionType.WEB_FACT: "external_or_realtime",
    ActionType.MIXED_RESEARCH: "external_or_realtime",
}

_SOURCES_BY_ACTION = {
    ActionType.CHAT: (),
    ActionType.MEMORY_WRITE: (),
    ActionType.MEMORY_READ: ("MEMORY",),
    ActionType.USER_CONTEXT: ("USER_CONTEXT",),
    ActionType.TEXT_TRANSFORM: (),
    ActionType.INTERNAL_DOC: ("INTERNAL",),
    ActionType.WEB_FACT: ("WEB",),
    ActionType.MIXED_RESEARCH: ("INTERNAL", "WEB"),
}

_RETRIEVAL_ACTIONS = {
    ActionType.USER_CONTEXT,
    ActionType.INTERNAL_DOC,
    ActionType.WEB_FACT,
    ActionType.MIXED_RESEARCH,
}

# 8개 클래스의 random baseline은 약 0.125.
# 현재 소규모 데이터셋에서는 정답 Top-1도 0.25~0.50 범위가 많으므로
# 절대 확률 0.40을 요구하면 올바른 예측을 대부분 버리게 된다.
_MIN_ACTION_CONFIDENCE = 0.25


def resolve_action(query: str) -> ActionPlan:
    predicted, confidence = classify_action(query)

    try:
        action = ActionType(predicted)
    except ValueError:
        return ActionPlan(
            action=ActionType.CHAT,
            confidence=0.0,
            retrieval_required=False,
            sources=(),
            retrieval_route="no_retrieval",
            reason="unknown_action_safe_fallback",
        )

    # 충분한 의미 신호가 있는 경우 Action 결과를 그대로 사용한다.
    if confidence >= _MIN_ACTION_CONFIDENCE:
        return ActionPlan(
            action=action,
            confidence=confidence,
            retrieval_required=action in _RETRIEVAL_ACTIONS,
            sources=_SOURCES_BY_ACTION[action],
            retrieval_route=_ROUTE_BY_ACTION[action],
            reason="action_classifier",
        )

    # 중요한 정책:
    # classifier가 확신하지 못한다고 해서 자동으로 Web 검색하지 않는다.
    #
    # 실제 Web/Internal의 강한 deterministic signal은 orchestrator의
    # 기존 retrieval rule이 별도로 확인할 수 있게 빈 route를 반환한다.
    return ActionPlan(
        action=action,
        confidence=confidence,
        retrieval_required=False,
        sources=(),
        retrieval_route="",
        reason="low_confidence_needs_strong_signal",
    )
