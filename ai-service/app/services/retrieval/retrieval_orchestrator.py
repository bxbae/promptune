from __future__ import annotations

from app.schemas.models import (
    RetrievalExecuteRequest,
    RetrievalExecuteResponse,
    RetrieveRequest,
    WebSearchResult,
)
from app.services.retrieval.rag_retriever import retrieve
from app.services.retrieval.retrieval_router import classify_retrieval_route
from app.services.retrieval.tavily_search import search_web


def execute_retrieval(
    req: RetrievalExecuteRequest,
) -> RetrievalExecuteResponse:
    route = classify_retrieval_route(req.query)

    documents = []
    web_results: list[WebSearchResult] = []

    used_internal_rag = False
    used_web_search = False

    # 1. 내부문서 검색
    if route == "internal_rag":
        if req.owner_user_id is None:
            raise ValueError(
                "internal_rag 검색에는 owner_user_id가 필요합니다."
            )

        result = retrieve(
            RetrieveRequest(
                query=req.query,
                owner_user_id=req.owner_user_id,
                top_k=req.top_k,
            )
        )

        documents = result.documents
        used_internal_rag = bool(documents)

    # 2. 웹 / 외부·실시간 검색
    elif route in {"web_search", "external_or_realtime"}:
        results = search_web(
            req.query,
            max_results=req.top_k,
        )

        web_results = [
            WebSearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
            )
            for item in results
        ]

        used_web_search = bool(web_results)

    # 3. 웹검색 토글이 켜져 있는데 아직 웹검색을 안 했다면(= internal_rag 등으로 판단된 경우),
    #    "복합 요청"으로 보고 웹검색도 추가로 실행 (route 값 자체는 그대로 두어 원래 분류 정보 보존)
    if req.use_web_search and not used_web_search:
        results = search_web(
            req.query,
            max_results=req.top_k,
        )

        web_results = [
            WebSearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
            )
            for item in results
        ]

        used_web_search = bool(web_results)

    # user_context:
    #   현재 여기서는 MS Graph를 직접 호출하지 않고 route만 반환한다.
    #
    # no_retrieval:
    #   검색하지 않는다.
    #
    # not_rag_or_restricted:
    #   검색하지 않는다.

    return RetrievalExecuteResponse(
        route=route,
        documents=documents,
        web_results=web_results,
        used_internal_rag=used_internal_rag,
        used_web_search=used_web_search,
    )
