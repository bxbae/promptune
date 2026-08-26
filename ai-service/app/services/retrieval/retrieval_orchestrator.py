from __future__ import annotations

import os

from app.schemas.models import (
    RetrievalExecuteRequest,
    RetrievalExecuteResponse,
    RetrieveRequest,
    WebSearchResult,
)
from app.services import pipeline_mock
from app.services.retrieval.ml_router import classify_ml_retrieval_route
from app.services.retrieval.tavily_search import search_web
from app.services.retrieval.conversation_context import resolve_conversation_retrieval
from app.services.retrieval.date_resolver import resolve_relative_dates

# app/routers/pipeline.py의 USE_REAL_RETRIEVAL과 동일한 폴백 규칙.
# (거길 직접 import하면 순환참조라 동일 로직을 복제함)
USE_REAL_RETRIEVAL = (
    os.getenv(
        "USE_REAL_RETRIEVAL",
        os.getenv("USE_REAL_MODELS", "false"),
    ).lower()
    == "true"
)

# /retrieve 엔드포인트와 동일하게, real 모드일 때만 실제 BGE-M3 임베딩 모델을
# 쓰는 rag_retriever를 로드한다. 예전엔 이 플래그 체크 없이 항상 real 모델을
# 불러서, mock 모드로 설정해도 internal_rag 라우트에서 매번 BGE-M3를 로드하려다
# 메모리 부족(OOM)으로 ai-service가 죽는 문제가 있었음 (2026-08-24).
if USE_REAL_RETRIEVAL:
    from app.services.retrieval.rag_retriever import retrieve


def execute_retrieval(
    req: RetrievalExecuteRequest,
) -> RetrievalExecuteResponse:
    conversation = resolve_conversation_retrieval(
        query=req.query,
        history=req.history,
    )

    effective_query = conversation.query

    # 2026-08-26: 이 메시지에 사용자가 직접 문서를 첨부했으면(document_ids),
    # 질의 텍스트가 어떻든 무조건 internal_rag로 보낸다 - ML 라우터/대화
    # 맥락 기반 override보다도 우선한다. "DOCX 첨부하고 '이게 무슨
    # 내용이야?'"처럼 질문 자체엔 "문서"/"파일" 같은 단어가 전혀 없어서
    # ml_router._is_explicit_internal_rag()도 못 잡고 ML도 no_retrieval로
    # 잘못 보내던 사례가 있었음 - 첨부라는 명시적인 사용자 행동(UI에서
    # 파일을 붙인 것) 자체가 텍스트 패턴 매칭보다 훨씬 신뢰할 수 있는
    # internal_rag 신호라 최우선으로 둔다.
    if req.document_ids:
        route = "internal_rag"
    elif conversation.route_override is not None:
        route = conversation.route_override
    else:
        route = classify_ml_retrieval_route(effective_query)

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

        retrieve_req = RetrieveRequest(
            query=effective_query,
            owner_user_id=req.owner_user_id,
            top_k=req.top_k,
            document_ids=req.document_ids,
        )
        result = (
            retrieve(retrieve_req)
            if USE_REAL_RETRIEVAL
            else pipeline_mock.retrieve(retrieve_req)
        )

        documents = result.documents
        used_internal_rag = bool(documents)

    # 2. 웹 / 외부·실시간 검색
    elif route in {"web_search", "external_or_realtime"}:
        # 2026-08-26: "어제"/"오늘" 같은 상대 날짜 표현이 그대로 Tavily에
        # 넘어가면 검색엔진이 어느 날짜인지 특정 못 해서(예: "어제 lg 트윈스
        # 경기 결과" -> 실제로는 다른 날짜/다른 상대팀 경기 내용이 섞여
        # 들어옴) 사실과 다른 답이 나오는 문제가 있었음. 검색어에만
        # 실제 날짜를 덧붙여서 보정한다(라우팅 판단에 쓰는 effective_query
        # 자체는 안 건드림 - date_resolver.py 상단 설명 참고).
        search_query = resolve_relative_dates(effective_query)

        results = search_web(
            search_query,
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
