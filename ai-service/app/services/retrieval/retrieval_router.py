from __future__ import annotations


def classify_retrieval_route(query: str) -> str:
    text = query.strip().lower()

    # 1. 검색 금지 / 민감정보
    restricted_keywords = [
        "개인 휴대폰",
        "개인 전화번호",
        "휴대폰 번호",
        "주민등록번호",
        "비밀번호",
    ]

    if any(keyword in text for keyword in restricted_keywords):
        return "not_rag_or_restricted"

    # 2. 사용자 개인 컨텍스트 - Microsoft Graph
    user_context_keywords = [
        "내 캘린더",
        "내 일정",
        "내 메일",
        "내 이메일",
        "내 회의",
    ]

    if any(keyword in text for keyword in user_context_keywords):
        return "user_context"

    # 3. 명시적 웹 검색
    web_search_keywords = [
        "최신 뉴스",
        "최근 뉴스",
        "뉴스 알려줘",
    ]

    if any(keyword in text for keyword in web_search_keywords):
        return "web_search"

    # 4. 실시간 / 외부 정보
    realtime_keywords = [
        "날씨",
        "주가",
        "환율",
        "현재 가격",
        "실시간",
    ]

    if any(keyword in text for keyword in realtime_keywords):
        return "external_or_realtime"

    # 5. 내부문서가 필요 없는 순수 생성/수정 요청
    no_retrieval_keywords = [
        "써줘",
        "써 줘",
        "작성해줘",
        "작성해 줘",
        "다듬어줘",
        "다듬어 줘",
        "고쳐줘",
        "고쳐 줘",
        "바꿔줘",
        "바꿔 줘",
        "요약해줘",
        "요약해 줘",
        "번역해줘",
        "번역해 줘",
        "정중하게 바꿔",
        "자연스럽게 바꿔",
    ]

    if any(keyword in text for keyword in no_retrieval_keywords):
        return "no_retrieval"

    # 6. 그 외 업무성 질문은 내부문서를 우선 검색
    return "internal_rag"
