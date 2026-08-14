"""AI 서비스 라우터 — 각 파이프라인 단계를 엔드포인트로 노출."""

import os

from fastapi import APIRouter

from app.schemas.models import (
    DiagnoseRequest,
    DiagnoseResponse,
    SuggestRequest,
    SuggestResponse,
    SafetyRequest,
    SafetyResponse,
    RetrieveRequest,
    RetrieveResponse,
    GenerateRequest,
    GenerateResponse,
    ValidateRequest,
    ValidateResponse,
)
from app.services import diagnose_mock, pipeline_mock


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

if USE_REAL_DIAGNOSIS:
    from app.services import diagnose_real

if USE_REAL_SUGGESTION:
    from app.services import suggest_hcx

if USE_REAL_RETRIEVAL:
    from app.services.retrieval import rag_retriever


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
    return pipeline_mock.generate(req)


@router.post(
    "/validate",
    response_model=ValidateResponse,
    tags=["15.최종검증"],
)
def validate(req: ValidateRequest):
    return pipeline_mock.validate(req)


@router.post(
    "/summarize-title",
    tags=["대화 제목 요약"],
)
def summarize_title(req: dict):
    """대화의 첫 프롬프트를 짧은 제목으로 요약. 지금은 mock(앞부분 자르기)이고,
    승득님이 실제 모델(HyperCLOVA 등)로 교체 예정."""
    text = req.get("text", "")
    # TODO(승득): 실제 요약 모델 호출로 교체
    # 지금은 mock: 앞 15자만 사용 (기존 백엔드 로직이 20자였던 것보다 더 짧게,
    # "AI가 다듬은 느낌"을 흉내내기 위해 임시로 이렇게 처리)
    title = text[:15].strip()
    return {"title": title}