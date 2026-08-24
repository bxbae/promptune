"""AI 서비스 라우터 — 각 파이프라인 단계를 엔드포인트로 노출."""

import os

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from app.services.validation.validator import validate_response
from app.schemas.models import (
    DiagnoseRequest,
    DiagnoseResponse,
    SuggestRequest,
    SuggestResponse,
    SafetyRequest,
    SafetyResponse,
    RetrievalRouteRequest,
    RetrievalRouteResponse,
    RetrievalExecuteRequest,
    RetrievalExecuteResponse,
    RetrieveRequest,
    RetrieveResponse,
    GenerateRequest,
    GenerateResponse,
    ValidateRequest,
    ValidateResponse,
    SummarizeTitleRequest,
    SummarizeTitleResponse,
    PromptRuleRequest,
    PromptRuleResponse,
    ImprovePromptRequest,
    ImprovePromptResponse,
)
from app.services import diagnose_mock, pipeline_mock, prompt_rule
from app.services.retrieval.ml_router import classify_ml_retrieval_route
from app.services.retrieval.retrieval_orchestrator import execute_retrieval
from app.services.retrieval import document_indexer

USE_REAL_TITLE_SUMMARY = (
    os.getenv(
        "USE_REAL_TITLE_SUMMARY",
        os.getenv("USE_REAL_MODELS", "false"),
    ).lower()
    == "true"
)

if USE_REAL_TITLE_SUMMARY:
    from app.services import summarize_hcx

USE_REAL_DIAGNOSIS = (
    os.getenv(
        "USE_REAL_DIAGNOSIS",
        os.getenv("USE_REAL_MODELS", "false"),
    ).lower()
    == "true"
)

USE_REAL_SUGGESTION = (
    os.getenv(
        "USE_REAL_SUGGESTION",
        os.getenv("USE_REAL_MODELS", "false"),
    ).lower()
    == "true"
)


USE_REAL_RETRIEVAL = (
    os.getenv(
        "USE_REAL_RETRIEVAL",
        os.getenv("USE_REAL_MODELS", "false"),
    ).lower()
    == "true"
)

USE_REAL_GENERATION = (
    os.getenv(
        "USE_REAL_GENERATION",
        os.getenv("USE_REAL_MODELS", "false"),
    ).lower()
    == "true"
)

USE_REAL_IMPROVEMENT = (
    os.getenv(
        "USE_REAL_IMPROVEMENT",
        os.getenv("USE_REAL_MODELS", "false"),
    ).lower()
    == "true"
)

if USE_REAL_GENERATION:
    from app.services import generate_hcx


if USE_REAL_DIAGNOSIS:
    from app.services import diagnose_real

if USE_REAL_SUGGESTION:
    from app.services import suggest_hcx

if USE_REAL_RETRIEVAL:
    from app.services.retrieval import rag_retriever

if USE_REAL_IMPROVEMENT:
    from app.services import improve_hcx


router = APIRouter()


@router.post(
    "/diagnose",
    response_model=DiagnoseResponse,
    tags=["5.통합진단"],
)
def diagnose(req: DiagnoseRequest):
    """8요소 누락 + 오탈자 + 업무유형 판정."""

    if USE_REAL_DIAGNOSIS:
        return diagnose_real.diagnose(req)

    return diagnose_mock.diagnose(req)

@router.post(
    "/prompt-rule",
    response_model=PromptRuleResponse,
    tags=["Prompt Rule"],
)
def apply_prompt_rule(req: PromptRuleRequest):
    """V6 진단 결과와 사용자 Preference를 개선 전략으로 변환."""
    return prompt_rule.apply_prompt_rule(req)

@router.post(
    "/improve-prompt",
    response_model=ImprovePromptResponse,
    tags=["Prompt Improvement"],
)
def improve_prompt(req: ImprovePromptRequest):
    """Phase 2-C: Prompt Rule을 반영해 개선 프롬프트를 생성."""
    if USE_REAL_IMPROVEMENT:
        return improve_hcx.improve(req)

    return pipeline_mock.improve_prompt(req)

@router.post(
    "/suggest",
    response_model=SuggestResponse,
    tags=["7.추천생성"],
)
def suggest(req: SuggestRequest):
    if USE_REAL_SUGGESTION:
        return suggest_hcx.suggest(req)

    return pipeline_mock.suggest(req)


@router.post(
    "/safety-check",
    response_model=SafetyResponse,
    tags=["8.안전검사"],
)
def safety_check(req: SafetyRequest):
    return pipeline_mock.safety_check(req)



@router.post(
    "/retrieval-route",
    response_model=RetrievalRouteResponse,
    tags=["12.Retrieval Route"],
)
def retrieval_route(req: RetrievalRouteRequest):
    return RetrievalRouteResponse(
        route=classify_ml_retrieval_route(req.query)
    )



@router.post(
    "/retrieval-execute",
    response_model=RetrievalExecuteResponse,
    tags=["12.Retrieval Execute"],
)
def retrieval_execute(req: RetrievalExecuteRequest):
    try:
        return execute_retrieval(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"[Retrieval] execute failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Retrieval 실행 중 오류가 발생했습니다.",
        ) from exc


@router.post(
    "/retrieve",
    response_model=RetrieveResponse,
    tags=["13.내부검색"],
)
def retrieve(req: RetrieveRequest):
    if USE_REAL_RETRIEVAL:
        return rag_retriever.retrieve(req)

    return pipeline_mock.retrieve(req)

@router.post(
    "/generate",
    response_model=GenerateResponse,
    tags=["14.답변생성"],
)
def generate(req: GenerateRequest):
    web_results = [item.model_dump() for item in req.web_results]
    used_web_search = bool(web_results)

    if USE_REAL_GENERATION:
        return generate_hcx.generate(
            req,
            web_results=web_results,
            used_web_search=used_web_search,
        )

    return pipeline_mock.generate(
        req,
        web_results=web_results,
        used_web_search=used_web_search,
    )


@router.post(
    "/validate",
    response_model=ValidateResponse,
    tags=["15.최종 검증"],
)
def validate(req: ValidateRequest):
    # semantic_validator가 rag_retriever.get_model()(BGE-M3)을 플래그 체크 없이
    # 항상 호출해서, mock 모드(USE_REAL_MODELS=false)에서도 /api/execute마다
    # 매번 real 임베딩 모델을 로드하려다 메모리 부족(OOM)으로 ai-service가
    # 죽는 문제가 있었음 (2026-08-24). /retrieve와 동일하게 USE_REAL_RETRIEVAL로
    # 게이트해서, mock 모드에서는 이미 있는 pipeline_mock.validate()를 쓰도록 수정.
    if not USE_REAL_RETRIEVAL:
        return pipeline_mock.validate(req)

    result = validate_response(
        original=req.original,
        generated=req.generated,
    )

    return ValidateResponse(
        passed=result.passed,
        rule_ok=result.rule_ok,
        semantic_ok=result.semantic_ok,
        semantic_score=result.semantic_score,
        facts_preserved=result.facts_preserved,
        issues=result.issues,
    )


@router.post(
    "/summarize-title",
    response_model=SummarizeTitleResponse,
    tags=["대화 제목 요약"],
)
def summarize_title(req: SummarizeTitleRequest):
    """대화의 첫 프롬프트를 짧은 제목으로 요약."""
    if USE_REAL_TITLE_SUMMARY:
        return summarize_hcx.summarize_title(req)

    # mock: 앞부분 자르기 (모델 없이 빠르게 테스트할 때 사용)
    title = req.text[:15].strip()
    return SummarizeTitleResponse(title=title)

@router.post(
    "/index-document",
    tags=["13.내부검색"],
)
async def index_document(
    document_id: int = Form(...),
    owner_user_id: int = Form(...),
    file_type: str | None = Form(None),
    file: UploadFile = File(...),
):
    try:
        file_bytes = await file.read()

        result = document_indexer.index_document(
            document_id=document_id,
            owner_user_id=owner_user_id,
            file_bytes=file_bytes,
            filename=file.filename,
            file_type=file_type,
        )

        return result

    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        print(f"[INDEX] document indexing failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="문서 인덱싱에 실패했습니다.",
        ) from exc
