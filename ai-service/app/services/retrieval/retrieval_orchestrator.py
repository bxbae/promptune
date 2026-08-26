from __future__ import annotations

import os
import re

from app.schemas.models import (
    RetrievalExecuteRequest,
    RetrievalExecuteResponse,
    RetrieveRequest,
    WebSearchResult,
)
from app.services import pipeline_mock
from app.services.retrieval.ml_router import classify_ml_retrieval_route
from app.services.retrieval.tavily_search import is_recency_query, search_web
from app.services.retrieval.conversation_context import resolve_conversation_retrieval
from app.services.retrieval.date_resolver import resolve_relative_dates
from app.services.retrieval.search_query_cleanup import build_search_query

# app/routers/pipeline.py의 USE_REAL_RETRIEVAL과 동일한 폴백 규칙.
# (거길 직접 import하면 순환참조라 동일 로직을 복제함)
USE_REAL_RETRIEVAL = (
    os.getenv(
        "USE_REAL_RETRIEVAL",
        os.getenv("USE_REAL_MODELS", "false"),
    ).lower()
    == "true"
)

from app.services.retrieval.rag_retriever import (
    retrieve,
    retrieve_document_overview,
)


_OVERVIEW_MARKERS = (
    "무슨 내용",
    "어떤 내용",
    "내용이야",
    "내용 알려",
    "전체 내용",
    "전체내용",
    "전체 요약",
    "전체요약",
    "문서 요약",
    "파일 요약",
    "요약해줘",
    "요약해 줘",
    "읽어줘",
    "읽어 줘",
    "핵심 내용",
    "핵심내용",
    "각 항목",
    "각항목",
    "전체 항목",
    "항목들",
    "구성 항목",
    "목차",
)


_DOCUMENT_TRANSFORM_MARKERS = (
    "보고서로 만들어",
    "문서로 만들어",
    "파일로 만들어",
    "pdf로 만들어",
    "워드로 만들어",
    "word로 만들어",
    "docx로 만들어",
    "양식으로 만들어",
    "템플릿으로 만들어",
)


def _is_document_transform_query(query: str) -> bool:
    text = str(query or "").strip().lower()
    return any(
        marker in text
        for marker in _DOCUMENT_TRANSFORM_MARKERS
    )


def _is_document_overview_query(query: str) -> bool:
    text = str(query or "").strip().lower()
    return any(marker in text for marker in _OVERVIEW_MARKERS)


def _clean_document_followup_query(query: str) -> str:
    """특정 document_id가 확정된 뒤에는 지시대명사 노이즈를 최소화한다."""
    text = str(query or "").strip()

    replacements = (
        "거기서",
        "그 문서에서",
        "그 파일에서",
        "해당 문서에서",
        "해당 파일에서",
        "그 문서",
        "그 파일",
        "그 이력서",
        "그 보고서",
        "아까 문서",
        "아까 파일",
        "전에 올린 문서",
        "전에 올린 파일",
    )

    for marker in replacements:
        text = text.replace(marker, " ")

    text = re.sub(r"\s+", " ", text).strip()
    return text or query


def execute_retrieval(
    req: RetrievalExecuteRequest,
) -> RetrievalExecuteResponse:
    document_ids = list(
        dict.fromkeys(
            int(x)
            for x in req.document_ids
            if x is not None and int(x) > 0
        )
    )

    # Backend가 현재 첨부/이전 첨부를 실제 document_id로 확정해서 보낸 경우에는
    # 대화 텍스트를 다시 HCX로 추정할 필요가 없다. ID가 가장 강한 사실(source of truth)이다.
    if document_ids:
        route = "internal_rag"
        effective_query = _clean_document_followup_query(req.query)
    else:
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

    print(f"[Retrieval] route={route!r} effective_query={effective_query!r}")

    documents = []
    web_results: list[WebSearchResult] = []

    used_internal_rag = False
    used_web_search = False

    # 1. 내부문서 검색
    if route == "internal_rag":
        # 실제 첨부/내부문서를 요청했는데 retrieval flag가 꺼져 있으면 mock 문서로
        # 조용히 대체하면 안 된다. 사용자가 올린 파일을 못 읽은 사실을 숨기는 대신
        # 설정 오류를 즉시 드러내야 잘못된 문서 답변을 원천 차단할 수 있다.
        if not USE_REAL_RETRIEVAL:
            raise ValueError(
                "내부 문서 분석에는 USE_REAL_RETRIEVAL=true가 필요합니다."
            )

        if req.owner_user_id is None:
            raise ValueError(
                "internal_rag 검색에는 owner_user_id가 필요합니다."
            )

        if (
            document_ids
            and (
                _is_document_overview_query(req.query)
                or _is_document_transform_query(req.query)
            )
            and USE_REAL_RETRIEVAL
        ):
            # "이거 무슨 내용이야?" / 전체 요약은 semantic Top-1이 아니라
            # document chunk를 원래 순서대로 읽는다.
            result = retrieve_document_overview(
                owner_user_id=req.owner_user_id,
                document_ids=document_ids,
            )
        else:
            retrieve_req = RetrieveRequest(
                query=effective_query,
                owner_user_id=req.owner_user_id,
                top_k=req.top_k,
                document_ids=document_ids,
            )

            result = (
                retrieve(retrieve_req)
                if USE_REAL_RETRIEVAL
                else pipeline_mock.retrieve(retrieve_req)
            )

            if document_ids and not USE_REAL_RETRIEVAL:
                result.documents = [
                    doc
                    for doc in result.documents
                    if doc.document_id in document_ids
                ]

        documents = result.documents
        used_internal_rag = bool(documents)

    # 2. 웹 / 외부·실시간 검색
    elif route in {"web_search", "external_or_realtime"}:
        # 2026-08-26: "최근"/"최신" 같은 시점 표현은 search_query_cleanup.py의
        # 불용구 제거(패치 13, 예: "최근 골 소식과 관련해서" 전체를 stock
        # phrase로 지움) 이후에는 검색어에서 이미 사라져 있을 수 있다. 그래서
        # "최근 소식은 일주일 이내 기사로 한정" 판정은 정제 전 원문
        # effective_query에 대해 먼저 하고, 그 결과(time_range)만 정제된
        # 검색어와 함께 넘긴다.
        recent_only = is_recency_query(effective_query)
        time_range = "week" if recent_only else None

        search_query = resolve_relative_dates(
            build_search_query(effective_query)
        )

        # 내부 RAG top_k와 Web 검색 결과 수를 분리한다.
        # 내부문서는 4개 chunk까지 사용할 수 있지만 Web은 최대 3건만 전달한다.
        web_top_k = min(max(int(req.top_k), 1), 3)

        results = search_web(
            search_query,
            max_results=web_top_k,
            time_range=time_range,
        )

        # 2026-08-26: "이강인 소속과 프로필" 질의가 검색어 정리(패치 13) 이후
        # 오히려 손흥민/조규성처럼 완전히 무관한 인물의 결과가 섞여 들어오는
        # 회귀가 재현됐는데, search_web()이 반환한 실제 title/url을 확인할
        # 방법이 로그에 전혀 없어서(이 파일에 로깅 자체가 없었음) 매번 답변
        # 텍스트만 보고 추측해야 했다. docker logs로 바로 원인을 볼 수 있게
        # route/검색어/실제 검색 결과를 남긴다 - 동작에는 영향 없음(순수 로깅).
        print(
            f"[Retrieval] route={route!r} search_query={search_query!r} "
            f"time_range={time_range!r} "
            f"results={[(r.get('title'), r.get('url')) for r in results]}"
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

    return RetrievalExecuteResponse(
        route=route,
        documents=documents,
        web_results=web_results,
        used_internal_rag=used_internal_rag,
        used_web_search=used_web_search,
    )
