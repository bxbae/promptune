from __future__ import annotations

from app.schemas.models import (
    RetrievalExecuteRequest,
    RetrievalExecuteResponse,
    RetrieveRequest,
    WebSearchResult,
)
from app.services.retrieval.rag_retriever import retrieve
from app.services.retrieval.ml_router import classify_ml_retrieval_route
from app.services.retrieval.tavily_search import search_web
from app.services.retrieval.conversation_context import resolve_conversation_retrieval


def execute_retrieval(
    req: RetrievalExecuteRequest,
) -> RetrievalExecuteResponse:
    conversation = resolve_conversation_retrieval(
        query=req.query,
        history=req.history,
    )

    effective_query = conversation.query

    route = (
        conversation.route_override
        if conversation.route_override is not None
        else classify_ml_retrieval_route(effective_query)
    )

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
                query=effective_query,
                owner_user_id=req.owner_user_id,
                top_k=req.top_k,
            )
        )

        documents = result.documents
        used_internal_rag = bool(documents)

    # 2. 웹 / 외부·실시간 검색
    elif route in {"web_search", "external_or_realtime"}:
        results = search_web(
            effective_query,
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
