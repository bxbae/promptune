from __future__ import annotations

import re
from urllib.parse import urlparse


_TOKEN_RE = re.compile(
    r"[가-힣A-Za-z0-9]+"
)

_STOPWORDS = {
    "알려줘",
    "알려",
    "설명해줘",
    "설명",
    "검색해줘",
    "검색",
    "찾아줘",
    "찾아봐",
    "대해",
    "대한",
    "관련",
    "최근",
    "최신",
    "현재",
    "오늘",
    "지금",
    "뉴스",
    "소식",
}

# 2026-09-02(1-B): "강남구 날씨는 어때?"의 토큰이 {"날씨는", ...}로 조사가
# 붙은 채로 만들어져서, 실제 검색 결과 본문의 "날씨"와 문자열이 안 맞아
# lexical overlap 보너스가 무력화되던 문제. conversation_memory.py의
# _extract_keywords()가 이미 쓰는 것과 같은 "흔한 조사 suffix 제거"만
# 최소로 적용한다 - 형태소 분석기를 새로 붙이지 않고, 남는 글자 수가
# 2자 이상일 때만 벗겨서 단어 자체가 뭉개지지 않게 한다.
_TOKEN_PARTICLE_SUFFIXES = (
    "으로부터",
    "에서부터",
    "이라고",
    "라고",
    "에서",
    "에게",
    "한테",
    "으로",
    "부터",
    "까지",
    "이나",
    "는",
    "은",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "로",
    "도",
    "만",
)


def _strip_trailing_particle(token: str) -> str:
    for suffix in _TOKEN_PARTICLE_SUFFIXES:
        if (
            token.endswith(suffix)
            and len(token) - len(suffix) >= 2
        ):
            return token[: -len(suffix)]

    return token


def _normalize(text: str) -> str:
    return re.sub(
        r"\s+",
        "",
        str(text or "").lower(),
    )


def _domain(url: str) -> str:
    try:
        return (
            urlparse(url)
            .netloc
            .lower()
            .removeprefix("www.")
        )
    except Exception:
        return ""


def _query_tokens(query: str) -> set[str]:
    tokens: set[str] = set()

    for raw in _TOKEN_RE.findall(str(query or "")):
        token = raw.lower()

        if len(token) < 2 or token in _STOPWORDS:
            continue

        stripped = _strip_trailing_particle(token)

        tokens.add(
            stripped
            if len(stripped) >= 2
            else token
        )

    return tokens


def _authority_bonus(
    url: str,
    intent: str,
) -> float:
    domain = _domain(url)
    intent = str(intent or "").upper()

    if not domain:
        return 0.0

    if intent == "PROFILE":
        if (
            "wikipedia.org" in domain
            or "namu.wiki" in domain
        ):
            return 0.15

    if intent == "RESEARCH":
        if (
            domain.endswith(".go.kr")
            or ".go.kr" in domain
            or domain.endswith(".gov")
            or ".gov." in domain
            or domain.endswith(".ac.kr")
            or ".ac.kr" in domain
            or domain.endswith(".edu")
            or ".edu." in domain
            or domain.endswith(".re.kr")
            or ".re.kr" in domain
        ):
            return 0.18

    return 0.0


def _contains_entity(
    item: dict,
    entity: str | None,
) -> bool:
    if not entity:
        return True

    normalized_entity = _normalize(entity)

    if not normalized_entity:
        return True

    haystack = _normalize(
        " ".join([
            str(item.get("title") or ""),
            str(item.get("content") or ""),
            str(item.get("url") or ""),
        ])
    )

    return normalized_entity in haystack


# 2026-09-02(1-B, edge case 2): search_plan.py의 subject 캡처 특성상
# entity에 "손흥민 최근"처럼 시간 modifier가 섞여 들어올 수 있다. 이런
# generic modifier 단어 하나만 일치해도 gate를 통과시키면 "최근 미국
# 증시 전망"처럼 완전히 무관한 결과까지 새어 들어간다 - 새 dependency나
# 큰 사전 없이, search_plan.py가 이미 쓰는 것과 같은 범위의 아주 작은
# 시간 표현 집합만 여기서 별도로 둔다(모듈 간 private import는 피한다).
_GENERIC_MODIFIER_TOKENS = {
    "오늘", "어제", "그제", "그저께", "내일", "모레",
    "지금", "현재", "최근", "최신", "요즘", "방금",
}


# 2026-09-02(1-B): CURRENT_FACT(날씨/시세/경기 결과 등)에 PROFILE과 같은
# _contains_entity() exact-string hard filter를 그대로 쓰면 안 된다 -
# entity="서울 강남구"인데 정상 기사가 "강남구 오늘 기온"처럼 "서울"과
# "강남구"를 붙여서 안 쓰는 경우가 흔해서, 정상 evidence까지 통째로
# 제거될 위험이 있다(실제 검토 결과 - PROFILE의 hard filter는 그대로
# 두고 별도 helper로 분리).
#
# 그래서 entity를 단어 단위로 쪼개서 "그중 하나라도 있으면 완전히
# 무관하지는 않다"고 보는, 훨씬 관대한 게이트만 둔다. 목적은 최적의
# evidence를 고르는 게 아니라 Northern California weather/Geneva Watch
# 행사처럼 주제/지역이 질문과 아예 무관한 결과만 걸러내는 것이고, 실제
# 우선순위(예: "서울 대기환경정보"보다 실제 날씨 기사를 우선하는 것)는
# 아래 _score_result()의 lexical overlap 점수에 맡긴다.
#
# (edge case 1) "대한민국의"처럼 entity 토큰에 조사가 붙어 있으면
# 결과 문서의 "대한민국"과 문자열이 안 맞아 정상 evidence가 제거될 수
# 있다 - _query_tokens()와 동일한 _strip_trailing_particle()을 그대로
# 재사용해 정규화한다.
def _entity_tokens(entity: str | None) -> set[str]:
    tokens: set[str] = set()

    for raw in _TOKEN_RE.findall(str(entity or "")):
        token = raw.lower()

        if len(token) < 2:
            continue

        stripped = _strip_trailing_particle(token)
        normalized = stripped if len(stripped) >= 2 else token

        if normalized in _GENERIC_MODIFIER_TOKENS:
            continue

        tokens.add(normalized)

    return tokens


def _matches_any_entity_token(
    item: dict,
    entity: str | None,
) -> bool:
    tokens = _entity_tokens(entity)

    if not tokens:
        return True

    haystack = _normalize(
        " ".join([
            str(item.get("title") or ""),
            str(item.get("content") or ""),
            str(item.get("url") or ""),
        ])
    )

    return any(
        _normalize(token) in haystack
        for token in tokens
    )


def _score_result(
    item: dict,
    *,
    query: str,
    intent: str,
    entity: str | None,
) -> float:
    tavily_score = float(
        item.get("score") or 0.0
    )

    title = str(
        item.get("title") or ""
    )
    content = str(
        item.get("content") or ""
    )
    combined = f"{title} {content}"

    final_score = tavily_score

    if entity:
        normalized_entity = _normalize(entity)
        normalized_result = _normalize(combined)

        if (
            normalized_entity
            and normalized_entity
            in normalized_result
        ):
            final_score += 0.20
        else:
            final_score -= 0.08

    tokens = _query_tokens(query)

    if tokens:
        lowered = combined.lower()
        matched = sum(
            1
            for token in tokens
            if token in lowered
        )

        final_score += min(
            matched * 0.03,
            0.15,
        )

    final_score += _authority_bonus(
        str(item.get("url") or ""),
        intent,
    )

    return final_score


def select_web_evidence(
    results: list[dict],
    *,
    query: str,
    intent: str,
    entity: str | None,
    limit: int = 3,
) -> list[dict]:
    if limit <= 0:
        return []

    unique = []
    seen_urls = set()
    seen_titles = set()

    for item in results:
        url_key = _normalize(
            item.get("url", "")
        )
        title_key = _normalize(
            item.get("title", "")
        )

        if (
            url_key
            and url_key in seen_urls
        ):
            continue

        if (
            title_key
            and title_key in seen_titles
        ):
            continue

        if url_key:
            seen_urls.add(url_key)

        if title_key:
            seen_titles.add(title_key)

        unique.append(item)

    # PROFILE 질의는 대상 인물/조직이 틀린 evidence를 사용할 수 없다.
    #
    # 예:
    #   query="손흥민 이력서 알려줘", entity="손흥민"
    #   홍명보/김연경/정몽규 문서는 Tavily score가 높더라도 제거한다.
    #
    # GENERAL/RESEARCH는 간접적으로 관련된 문서가 유효할 수 있으므로
    # hard filtering을 적용하지 않는다.
    if intent == "PROFILE" and entity:
        unique = [
            item
            for item in unique
            if _contains_entity(item, entity)
        ]

    # CURRENT_FACT는 PROFILE만큼 엄격한 exact-string 매치를 요구하지
    # 않는다 - entity 단어 중 하나도 안 나오는, 질문 주제/지역과
    # 완전히 무관한 결과만 제거한다.
    if intent == "CURRENT_FACT" and entity:
        unique = [
            item
            for item in unique
            if _matches_any_entity_token(item, entity)
        ]

    ranked = sorted(
        unique,
        key=lambda item: _score_result(
            item,
            query=query,
            intent=intent,
            entity=entity,
        ),
        reverse=True,
    )

    return ranked[:limit]
