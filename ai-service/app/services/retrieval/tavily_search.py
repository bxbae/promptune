import os
from tavily import TavilyClient

# 2026-08-26: "침착맨 몇살이야?" 같은 질의에서 관련성 약한 결과(예: 은퇴 준비
# 나이를 다루는 완전히 무관한 영문 기사)가 섞여 들어와 HCX가 근거 없는
# 생년월일을 지어내는 사례가 확인됨. Tavily의 include_domains로 신뢰할 수
# 있는 뉴스 도메인만 검색되게 제한하면, 검색 폭(topic="news") 안에서도
# 출처 품질을 통제할 수 있음. 팀이 코드 배포 없이 도메인 목록을 조정할 수
# 있도록 환경변수로 뺐고, 값이 없으면 네이버뉴스 기본값을 씀(요청대로
# "네이버 뉴스로 한정").
_DEFAULT_TRUSTED_DOMAINS = ["news.naver.com"]

# 2026-08-26: 위 도메인 제한을 배포한 직후 "오늘 삼성 주가"에 실제와 전혀
# 다른 가격(약 90,000원, 실제로는 261,500원)을 자신 있게 답하는 회귀가
# 확인됨. news.naver.com은 시세 숫자가 실시간으로 박혀 있는 페이지가 아니라
# 일반 보도 기사 위주라, 도메인을 여기로만 좁히면 정작 "오늘 종가가 몇
# 원인지" 같은 구체적 숫자를 담은 자료를 못 찾고 HCX가 숫자를 지어내는
# 쪽으로 후퇴함(반대로 예전엔 Reuters/CNBC 등 시세를 직접 인용하는 기사가
# 걸려서 정확했음). 시세류 질의는 Tavily의 전용 topic="finance"를 쓰고,
# 이 경우엔 news.naver.com 제한도 적용하지 않는다 - 신뢰 도메인 제한의
# 원래 목적(무관한 기사 혼입 방지)과 별개로 애초에 topic="finance"
# 자체가 금융 데이터 소스로 좁혀 나오므로 추가 제한이 오히려 결과 자체를
# 0건으로 만들 위험이 큼.
_FINANCE_MARKERS = [
    "주가", "주식", "환율", "시세", "지수", "코스피", "코스닥",
    "비트코인", "종가", "시가총액", "증시",
]


def _is_finance_query(query: str) -> bool:
    text = query.lower()
    return any(marker in text for marker in _FINANCE_MARKERS)


def _trusted_domains() -> list[str]:
    raw = os.getenv("TAVILY_TRUSTED_DOMAINS")
    if raw is None:
        # 환경변수 자체가 없으면(.env.production에 아직 안 넣었으면) 기본값 사용
        return _DEFAULT_TRUSTED_DOMAINS
    # 환경변수를 일부러 빈 값/공백으로 설정하면 도메인 제한 없이 검색
    # (TAVILY_TRUSTED_DOMAINS= 처럼 값 없이 등록한 경우)
    domains = [d.strip() for d in raw.split(",") if d.strip()]
    return domains


def _run_search(client, query, max_results, topic, include_domains):
    search_kwargs = dict(
        query=query,
        search_depth="basic",
        topic=topic,
        max_results=max_results,
        include_answer=False,
        include_raw_content=False,
    )

    if include_domains:
        search_kwargs["include_domains"] = include_domains

    response = client.search(**search_kwargs)

    return response.get("results", [])


def search_web(query, max_results=5):
    if not query.strip():
        raise ValueError("검색어가 비어 있습니다.")

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY가 없습니다.")

    client = TavilyClient(api_key=api_key)
    query = query.strip()

    if _is_finance_query(query):
        return _run_search(
            client, query, max_results,
            topic="finance",
            include_domains=None,
        )

    # 2026-08-25(원 커밋): 스포츠 경기 결과처럼 시간에 민감한 질의에서
    # "프리뷰/예측" 기사가 "결과" 기사보다 검색어와 더 유사하다는 이유로
    # 상위에 올라와, 실제 스코어가 없는 기사를 근거로 모델이 결과를 잘못
    # 답하는 사례가 확인됨(예: 경기 전 프리뷰 기사가 상위 노출). topic="news"는
    # 최신 뉴스/발행일 기준으로 결과를 우선하도록 Tavily에 알려줘서, 예측성
    # 기사보다 실제 보도(결과) 기사가 뽑힐 확률을 높인다.
    trusted_domains = _trusted_domains()

    results = _run_search(
        client, query, max_results,
        topic="news",
        include_domains=trusted_domains,
    )

    # 2026-08-26: "LG 트윈스 단장님의 이름과 약력을 안내해줘" 같은 질의에서
    # news.naver.com 하나로 제한한 결과가 0건이 되면서, 웹 검색 결과가
    # 아예 없는 채로 생성이 진행돼 HCX가 "제공할 수 없습니다"로 답변을
    # 회피하는 사례가 확인됨. 신뢰 도메인 제한의 목적(무관한 기사 혼입
    # 방지)은 결과가 여러 개 있을 때 그중 나쁜 걸 거르는 것이지, 결과
    # 자체를 아예 없애려는 게 아니므로 - 제한된 검색이 0건이면 제한 없이
    # 한 번 더 시도한다.
    if not results and trusted_domains:
        results = _run_search(
            client, query, max_results,
            topic="news",
            include_domains=None,
        )

    return results
