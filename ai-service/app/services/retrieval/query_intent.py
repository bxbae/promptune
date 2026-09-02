from __future__ import annotations

import re


_FIRST_PERSON_RE = re.compile(
    r"(?<![가-힣])(?:나|내|저|제)(?:는|가|를|의|\s)"
)

_WHO_RE = re.compile(
    r"^\s*(?P<subject>.+?)(?:은|는|이|가)?\s+"
    r"누구(?:야|예요|에요|인가요|인지|지)?\s*[?!.]*\s*$",
    re.IGNORECASE,
)

_WHAT_RE = re.compile(
    r"^\s*(?P<subject>.+?)(?:은|는|이|가)?\s+"
    r"(?:뭐|무엇)(?:야|예요|에요|인가요|인지|지)?\s*[?!.]*\s*$",
    re.IGNORECASE,
)

_KIND_RE = re.compile(
    r"^\s*(?P<subject>.+?)(?:은|는|이|가)?\s+"
    r"(?:뭐|무엇)\s*하는\s*"
    r"(?:사람|회사|기업|팀|그룹|서비스|제품|조직)"
    r"(?:이야|야|예요|에요|인가요)?\s*[?!.]*\s*$",
    re.IGNORECASE,
)


_PROFILE_LOOKUP_RE = re.compile(
    r"^\s*(?P<subject>.+?)(?:은|는|이|가|의)?\s+"
    r"(?:이력서|프로필|경력|약력|학력|소속)"
    r"(?:을|를|은|는|이|가|도)?\s*"
    r"(?:알려줘|알려주세요|알려|정리해줘|정리해|"
    r"보여줘|설명해줘|소개해줘|찾아줘)?"
    r"\s*[?!.]*\s*$",
    re.IGNORECASE,
)


# 2026-09-02: "손흥민 나이 알려줘", "아이유 생일이 언제야", "삼성전자 주소
# 알려줘", "이재용 키가 몇이야", "BTS 소속사 어디야" 처럼 "OO는 누구야"류가
# 아니라 구체적 속성을 묻는 질문은 위 패턴 어디에도 안 걸려서 검색 자체가
# 누락되던 문제(1-A)를 고친다. "이력서/프로필/경력/약력/학력/소속"은 이미
# _PROFILE_LOOKUP_RE가 다루므로 여기서는 중복 추가하지 않고, 실제 재현된
# 5개 속성명만 최소로 추가한다. 물음의 어미가 "알려줘"류/"언제야"류/
# "몇이야"류/"어디야"류로 서로 달라서 종결 표현을 여러 갈래로 둔다.
_ATTRIBUTE_LOOKUP_RE = re.compile(
    r"^\s*(?P<subject>.+?)(?:은|는|이|가|의)?\s+"
    r"(?:나이|생일|키|주소|소속사)"
    r"(?:을|를|은|는|이|가|도)?\s*"
    r"(?:알려줘|알려주세요|알려|말해줘|보여줘|찾아줘|"
    r"언제야|언제예요|언제에요|언제인가요|언제지|"
    r"몇\s*살이야|몇\s*살이에요|몇\s*이야|몇\s*이에요|몇\s*인가요|"
    r"어디야|어디예요|어디에요|어디인가요|어디지)?"
    r"\s*[?!.]*\s*$",
    re.IGNORECASE,
)


_DEICTIC_SUBJECTS = {
    "그 사람",
    "그분",
    "그 회사",
    "그 팀",
    "그 그룹",
    "그 프로젝트",
    "그 문서",
    "그 파일",
    "이 문서",
    "이 파일",
    # "우리 회사 주소 알려줘"처럼 회사 자기참조 표현이 subject로 잡히는 걸
    # 막는다 - "나"/"내"/"저"/"제"의 _FIRST_PERSON_RE와 같은 역할이지만
    # "우리"/"저희"는 그 정규식 대상이 아니라서 별도로 둔다.
    "우리 회사",
    "우리회사",
    "저희 회사",
    "저희회사",
}


def extract_external_entity_subject(query: str) -> str | None:
    text = re.sub(r"\s+", " ", str(query or "").strip())

    if not text:
        return None

    if _FIRST_PERSON_RE.search(text):
        return None

    for pattern in (
        _WHO_RE,
        _WHAT_RE,
        _KIND_RE,
        _PROFILE_LOOKUP_RE,
        _ATTRIBUTE_LOOKUP_RE,
    ):
        match = pattern.match(text)

        if not match:
            continue

        subject = match.group("subject").strip(" ,.!?")

        if subject in _DEICTIC_SUBJECTS:
            return None

        if len(subject) < 2 or len(subject) > 80:
            return None

        return subject

    return None


def is_external_entity_lookup_query(query: str) -> bool:
    return extract_external_entity_subject(query) is not None


# 2026-09-02: "내 나이 알려줘"/"제 생일 알려줘"/"내 소속 알려줘"가
# resolve_strong_retrieval_route()에서는 정확히 걸러지는데(None), 그 뒤에
# 실행되는 ActionClassifier(action_train.json 학습)가 이 문장들을 독자적으로
# WEB_FACT로 오분류(confidence 0.29~0.31)해서 최종 route가
# external_or_realtime(Tavily 웹검색)으로 나가는 회귀가 실제 재현됨.
# action_resolver가 ActionClassifier를 타기 전에 먼저 걸러 쓸 수 있게,
# 위 _PROFILE_LOOKUP_RE/_ATTRIBUTE_LOOKUP_RE의 명사 목록을 재사용한
# public helper로 노출한다("이름"만 이 guard 전용으로 추가 - 외부 entity
# 재현 사례(1-A)에는 없었지만 자기참조 재현 사례엔 필요함).
_SELF_ATTRIBUTE_NOUNS = (
    "이력서", "프로필 이름", "프로필", "경력", "약력", "학력", "소속",
    "나이", "생일", "키", "주소", "소속사",
    "이름",
)

_SELF_ATTRIBUTE_QUERY_RE = re.compile(
    r"^\s*(?P<subject>나|내|저|제)(?:는|가|를|의)?\s+"
    rf"(?:{'|'.join(_SELF_ATTRIBUTE_NOUNS)})"
    r"(?:을|를|은|는|이|가|도)?\s*"
    r"(?:알려줘|알려주세요|알려|말해줘|보여줘|찾아줘|"
    r"정리해줘|정리해|설명해줘|소개해줘|"
    r"언제야|언제예요|언제에요|언제인가요|언제지|"
    r"몇\s*살이야|몇\s*살이에요|몇\s*이야|몇\s*이에요|몇\s*인가요|"
    r"어디야|어디예요|어디에요|어디인가요|어디지|"
    r"뭐야|뭐예요|뭐에요|무엇인가요)?"
    r"\s*[?!.]*\s*$",
    re.IGNORECASE,
)


def is_self_referential_attribute_query(query: str) -> bool:
    """
    "내 나이 알려줘"처럼 명확한 1인칭 자기참조(나/내/저/제) + 개인
    속성/프로필 질의인지 판정한다. "손흥민 나이 알려줘"(외부 entity)나
    "우리 회사 주소 알려줘"(회사 자기참조, 이 함수의 대상 아님)는
    subject가 나/내/저/제로 고정돼 있어 매치되지 않는다.
    """
    text = re.sub(r"\s+", " ", str(query or "").strip())

    if not text:
        return False

    return bool(_SELF_ATTRIBUTE_QUERY_RE.match(text))
