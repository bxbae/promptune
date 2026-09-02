from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from app.services.retrieval.query_intent import (
    extract_external_entity_subject,
)


SearchIntent = Literal[
    "PROFILE",
    "RESEARCH",
    "NEWS",
    "FINANCE",
    "CURRENT_FACT",
    "GENERAL",
]

Freshness = Literal[
    "NONE",
    "DAY",
    "WEEK",
]


@dataclass(frozen=True)
class SearchPlan:
    query: str
    intent: SearchIntent
    entity: str | None
    freshness: Freshness


# 2026-09-02(1-A 후속): "환율"/"주가"/"시세"/"코스피"/"코스닥"/"비트코인"/
# "금리"는 시간 표현(오늘/지금 등) 없이도 그 자체로 "지금 이 순간의
# 시장 가치"를 뜻한다 - "책 가격"/"서비스 가격"처럼 시간과 무관하게
# 쓰이는 일반 명사 "가격"과는 성격이 다르다. ml_router.
# resolve_strong_retrieval_route()가 이 부분집합만 재사용해서 "가격"을
# 전역 실시간 키워드로 넣지 않고도(범용 명사라 오탐 위험이 큼) 시장
# 정보 질의를 결정적으로 web route로 보낼 수 있게 한다 - 두 파일에
# 키워드 목록을 따로 만들지 않기 위한 분리다.
#
# 2026-09-02(범위 축소): "비트코인"/"금리"는 "비트코인 작동 원리
# 설명해줘"/"금리 인상이 경제에 미치는 영향 설명해줘"처럼 개념/분석
# 질문에도 흔히 쓰여서, strong routing(무조건 web으로 확정)용으로는
# 너무 넓었다. "값 조회" 의미가 뚜렷한 좁은 부분집합만 strong route에
# 쓰고, build_search_plan()의 FINANCE intent 분류(검색 topic 선택에만
# 쓰임 - 잘못 걸려도 routing을 강제하지 않아 위험이 훨씬 작음)는 기존
# 8개 범위 그대로 유지한다. 두 책임의 범위가 다르다.
_STRONG_MARKET_VALUE_MARKERS = (
    "환율",
    "주가",
    "시세",
    "코스피",
    "코스닥",
)

_MARKET_VALUE_MARKERS = _STRONG_MARKET_VALUE_MARKERS + (
    "비트코인",
    "금리",
)

_FINANCE_MARKERS = _MARKET_VALUE_MARKERS + ("가격",)

# 2026-09-02(구조화): "환율"/"주가"/"시세"/"코스피"/"코스닥"이 문장 어디에
# 있든 단순 포함(any(marker in text))만으로 True였던 이전 방식은
# "주가란 뭐야?"/"환율 계산 방법 알려줘"/"코스피와 코스닥 차이는?"/
# "시세라는 말의 뜻이 뭐야?"처럼 marker는 있지만 실제로는 개념/방법을
# 묻는 질문까지 strong route(무조건 web 확정)로 잘못 보냈다. 개념 질문을
# 하나하나 blacklist로 열거하는 대신, marker 뒤에 실제 "지금 이 값이
# 얼마인지" 조회하는 문장 형태(조사 + 선택적 시간표현 + 조회형 종결 또는
# 문장 끝)가 오는지만 구조적으로 확인한다 - "주가란"/"환율 계산 방법"/
# "코스피와"/"시세라는"처럼 marker 뒤에 다른 말이 끼면 이 형태에 안
# 걸려서 자연히 걸러진다.
_MARKET_VALUE_QUERY_RE = re.compile(
    r"(?:환율|주가|시세|코스피|코스닥)"
    r"(?:은|는|이|가)?\s*"
    r"(?:지금|오늘|현재)?\s*"
    r"(?:알려줘|알려주세요|알려|말해줘|보여줘|찾아줘|"
    r"어때(?:요)?|"
    r"얼마야|얼마예요|얼마에요|얼마인가요|얼마)?"
    r"\s*[?!.]*\s*$",
    re.IGNORECASE,
)


def is_market_value_query(query: str) -> bool:
    """
    "환율"/"주가"/"시세"/"코스피"/"코스닥" 뒤에 실제 값 조회 형태(조사 +
    선택적 시간표현 + 조회형 종결/문장 끝)가 오는 질의만 True다(strong
    routing 전용). "주가란 뭐야?"/"환율 계산 방법 알려줘"처럼 marker만
    있고 개념/방법을 묻는 질문은 False다. "비트코인"/"금리"/"가격"은
    개념/분석 질문에도 흔히 쓰여서 애초에 이 marker 목록에 없다 - FINANCE
    intent 분류(build_search_plan)에는 그대로 남아 있다.
    """
    text = str(query or "").strip()
    return bool(_MARKET_VALUE_QUERY_RE.search(text))


_CURRENT_FACT_MARKERS = (
    "날씨",
    "기온",
    "경기 결과",
    "경기결과",
    "승패",
    "스코어",
    "우승",
)

_NEWS_MARKERS = (
    "뉴스",
    "소식",
    "속보",
    "이슈",
)

_RECENT_MARKERS = (
    "최근",
    "최신",
    "요즘",
)

_TODAY_MARKERS = (
    "오늘",
    "지금",
    "현재",
    "방금",
)


# 2026-09-02: entity 추출(_extract_search_subject / extract_external_entity_subject)은
# 질의 전체가 "^...$" 앵커에 맞는 짧은 단일 문장일 때만 성공한다. PrompTune UI가
# CONTEXT 추천문구를 덧붙이면 질의가 여러 문장으로 늘어나 entity 추출이 항상
# 실패하고, intent=GENERAL로 잘못 분류되어 tavily_search.py의 프로필 도메인
# (위키백과/나무위키/올림픽/그래미) 라우팅이 아예 시도되지 않는다. entity 추출
# 성공 여부와 무관하게 질의 텍스트에 인물 마커가 있으면 PROFILE로 분류한다.
_PROFILE_MARKERS = (
    "프로필", "약력", "소속", "선수", "감독", "가수", "배우", "인물",
    "유튜버", "단장", "코치", "아이돌", "뮤지션",
    "정치인", "인플루언서", "크리에이터", "코미디언", "국회의원",
)

_RESEARCH_MARKERS = (
    "기여",
    "영향",
    "효과",
    "경제효과",
    "문화적 영향",
    "역할",
    "분석",
    "조사",
    "근거",
)


_TIME_PREFIX_RE = re.compile(
    r"^\s*(?:오늘|어제|그제|그저께|내일|모레|"
    r"현재|지금|최근|최신|요즘|방금)\s+"
)

_SUBJECT_PATTERNS = (
    # "BTS가 국가에 기여한 점", "AI가 고용에 미치는 영향"
    re.compile(
        r"^(?P<subject>.+?)(?:은|는|이|가)\s+"
        r".+?(?:기여|영향|효과|역할|분석|조사)"
    ),

    # "BTS 최근 뉴스", "OpenAI 최신 소식"
    re.compile(
        r"^(?P<subject>.+?)\s+"
        r"(?:최근|최신|오늘|현재)?\s*"
        r"(?:뉴스|소식|속보|이슈)(?:\s|$)"
    ),

    # "커피 시세", "원달러 환율", "서울 날씨",
    # "LG 트윈스 경기 결과"
    #
    # 2026-09-02(1-B): "강남구 날씨는 어때?"처럼 트리거 명사 바로 뒤에
    # 조사가 붙으면(공백 없이) 원래 (?:\s|$) 경계 조건을 못 만족해서
    # entity 추출 자체가 실패했다 - "강남구"/"서울" 같은 특정 지역명을
    # 하드코딩하는 게 아니라, 흔한 조사(은/는/이/가/을/를/도) + 흔한
    # 문장부호(?!.,)까지 경계로 허용해 일반적인 한국어 질문 어미를
    # 다룬다.
    re.compile(
        r"^(?P<subject>.+?)\s+"
        r"(?:환율|주가|시세|가격|날씨|기온|"
        r"경기\s*결과)"
        r"(?:은|는|이|가|을|를|도)?"
        r"(?:\s|$|[?!.,])"
    ),
)

_DEICTIC_SEARCH_SUBJECTS = {
    "그 사람",
    "그 회사",
    "그 그룹",
    "그 팀",
    "이 문서",
    "그 문서",
    "이 파일",
    "그 파일",
}


def _extract_search_subject(
    text: str,
) -> str | None:
    cleaned = _TIME_PREFIX_RE.sub(
        "",
        str(text or "").strip(),
        count=1,
    )

    for pattern in _SUBJECT_PATTERNS:
        match = pattern.search(cleaned)

        if not match:
            continue

        subject = (
            match.group("subject")
            .strip(" ,.!?")
        )

        if (
            2 <= len(subject) <= 80
            and subject
            not in _DEICTIC_SEARCH_SUBJECTS
        ):
            return subject

    return None


def _detect_freshness(text: str) -> Freshness:
    if any(marker in text for marker in _TODAY_MARKERS):
        return "DAY"

    if any(marker in text for marker in _RECENT_MARKERS):
        return "WEEK"

    return "NONE"


def build_search_plan(query: str) -> SearchPlan:
    text = str(query or "").strip()
    lowered = text.lower()

    entity = extract_external_entity_subject(text)

    if entity is None:
        entity = _extract_search_subject(text)

    freshness = _detect_freshness(lowered)

    if any(marker in lowered for marker in _FINANCE_MARKERS):
        return SearchPlan(
            query=text,
            intent="FINANCE",
            entity=entity,
            freshness=freshness,
        )

    if any(marker in lowered for marker in _CURRENT_FACT_MARKERS):
        return SearchPlan(
            query=text,
            intent="CURRENT_FACT",
            entity=entity,
            freshness=freshness,
        )

    if any(marker in lowered for marker in _NEWS_MARKERS):
        return SearchPlan(
            query=text,
            intent="NEWS",
            entity=entity,
            freshness=(
                freshness
                if freshness != "NONE"
                else "WEEK"
            ),
        )

    if any(marker in lowered for marker in _RESEARCH_MARKERS):
        return SearchPlan(
            query=text,
            intent="RESEARCH",
            entity=entity,
            freshness=freshness,
        )

    if any(marker in lowered for marker in _PROFILE_MARKERS):
        return SearchPlan(
            query=text,
            intent="PROFILE",
            entity=entity,
            freshness=freshness,
        )

    if entity is not None:
        return SearchPlan(
            query=text,
            intent="PROFILE",
            entity=entity,
            freshness=freshness,
        )

    return SearchPlan(
        query=text,
        intent="GENERAL",
        entity=None,
        freshness=freshness,
    )
