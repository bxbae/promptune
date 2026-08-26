import os
from tavily import TavilyClient

def search_web(query, max_results=5):
    if not query.strip():
        raise ValueError("검색어가 비어 있습니다.")

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY가 없습니다.")

    client = TavilyClient(api_key=api_key)

    # 2026-08-26: 스포츠 경기 결과처럼 시간에 민감한 질의에서 "프리뷰/예측"
    # 기사가 "결과" 기사보다 검색어와 더 유사하다는 이유로 상위에 올라와,
    # 실제 스코어가 없는 기사를 근거로 모델이 결과를 잘못 답하는 사례가
    # 확인됨(예: 경기 전 프리뷰 기사가 상위 노출). topic="news"는 최신
    # 뉴스/발행일 기준으로 결과를 우선하도록 Tavily에 알려줘서, 예측성
    # 기사보다 실제 보도(결과) 기사가 뽑힐 확률을 높인다.
    response = client.search(
        query=query.strip(),
        search_depth="basic",
        topic="news",
        max_results=max_results,
        include_answer=False,
        include_raw_content=False,
    )

    return response.get("results", [])
