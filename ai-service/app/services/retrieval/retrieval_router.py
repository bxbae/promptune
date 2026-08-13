from __future__ import annotations


def classify_retrieval_route(query: str) -> str:
    text = query.strip().lower()

    restricted_keywords = [
        "개인 휴대폰",
        "개인 전화번호",
        "휴대폰 번호",
        "주민등록번호",
        "비밀번호",
    ]

    if any(keyword in text for keyword in restricted_keywords):
        return "not_rag_or_restricted"

    user_context_keywords = [
        "내 캘린더",
        "내 일정",
        "내 메일",
        "내 이메일",
        "내 회의",
    ]

    if any(keyword in text for keyword in user_context_keywords):
        return "user_context"

    web_search_keywords = [
        "최신 뉴스",
        "최근 뉴스",
        "뉴스 알려줘",
    ]

    if any(keyword in text for keyword in web_search_keywords):
        return "web_search"

    realtime_keywords = [
        "날씨",
        "주가",
        "환율",
        "현재 가격",
        "실시간",
    ]

    if any(keyword in text for keyword in realtime_keywords):
        return "external_or_realtime"

    return "internal_rag"
