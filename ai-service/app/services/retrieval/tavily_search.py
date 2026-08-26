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


def _trusted_domains() -> list[str]:
    raw = os.getenv("TAVILY_TRUSTED_DOMAINS")
    if raw is None:
        # 환경변수 자체가 없으면(.env.production에 아직 안 넣었으면) 기본값 사용
        return _DEFAULT_TRUSTED_DOMAINS
    # 환경변수를 일부러 빈 값/공백으로 설정하면 도메인 제한 없이 검색
    # (TAVILY_TRUSTED_DOMAINS= 처럼 값 없이 등록한 경우)
    domains = [d.strip() for d in raw.split(",") if d.strip()]
    return domains


def search_web(query, max_results=5):
    if not query.strip():
        raise ValueError("검색어가 비어 있습니다.")

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY가 없습니다.")

    client = TavilyClient(api_key=api_key)

    search_kwargs = dict(
        query=query.strip(),
        search_depth="basic",
        # 2026-08-26: 스포츠 경기 결과처럼 시간에 민감한 질의에서 "프리뷰/예측"
        # 기사가 "결과" 기사보다 검색어와 더 유사하다는 이유로 상위에 올라와,
        # 실제 스코어가 없는 기사를 근거로 모델이 결과를 잘못 답하는 사례가
        # 확인됨(예: 경기 전 프리뷰 기사가 상위 노출). topic="news"는 최신
        # 뉴스/발행일 기준으로 결과를 우선하도록 Tavily에 알려줘서, 예측성
        # 기사보다 실제 보도(결과) 기사가 뽑힐 확률을 높인다.
        topic="news",
        max_results=max_results,
        include_answer=False,
        include_raw_content=False,
    )

    trusted_domains = _trusted_domains()
    if trusted_domains:
        search_kwargs["include_domains"] = trusted_domains

    response = client.search(**search_kwargs)

    return response.get("results", [])
