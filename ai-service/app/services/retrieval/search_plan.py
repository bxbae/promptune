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


_FINANCE_MARKERS = (
    "환율",
    "주가",
    "시세",
    "가격",
    "코스피",
    "코스닥",
    "비트코인",
    "금리",
)

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
    re.compile(
        r"^(?P<subject>.+?)\s+"
        r"(?:환율|주가|시세|가격|날씨|기온|"
        r"경기\s*결과)(?:\s|$)"
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

    if entity is not None:
        return SearchPlan(
            query=text,
            intent="PROFILE",
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

    return SearchPlan(
        query=text,
        intent="GENERAL",
        entity=None,
        freshness=freshness,
    )
