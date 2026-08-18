import os
from tavily import TavilyClient

def search_web(query, max_results=5):
    if not query.strip():
        raise ValueError("검색어가 비어 있습니다.")

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY가 없습니다.")

    client = TavilyClient(api_key=api_key)

    response = client.search(
        query=query.strip(),
        search_depth="basic",
        max_results=max_results,
        include_answer=False,
        include_raw_content=False,
    )

    return response.get("results", [])
