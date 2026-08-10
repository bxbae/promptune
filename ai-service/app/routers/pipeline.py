"""AI 서비스 라우터 — 각 파이프라인 단계를 엔드포인트로 노출."""
from fastapi import APIRouter
from app.schemas.models import (
    DiagnoseRequest, DiagnoseResponse,
    SuggestRequest, SuggestResponse,
    SafetyRequest, SafetyResponse,
    RetrieveRequest, RetrieveResponse,
    GenerateRequest, GenerateResponse,
    ValidateRequest, ValidateResponse,
)
from app.services import diagnose_mock, pipeline_mock

router = APIRouter()


@router.post("/diagnose", response_model=DiagnoseResponse, tags=["5.통합진단"])
def diagnose(req: DiagnoseRequest):
    """8요소 누락 + 오탈자 + 업무유형 판정 (승득 담당, KcELECTRA 자리)."""
    return diagnose_mock.diagnose(req)


@router.post("/suggest", response_model=SuggestResponse, tags=["7.추천생성"])
def suggest(req: SuggestRequest):
    return pipeline_mock.suggest(req)


@router.post("/safety-check", response_model=SafetyResponse, tags=["8.안전검사"])
def safety_check(req: SafetyRequest):
    return pipeline_mock.safety_check(req)


@router.post("/retrieve", response_model=RetrieveResponse, tags=["13.내부검색"])
def retrieve(req: RetrieveRequest):
    return pipeline_mock.retrieve(req)


@router.post("/generate", response_model=GenerateResponse, tags=["14.답변생성"])
def generate(req: GenerateRequest):
    return pipeline_mock.generate(req)


@router.post("/validate", response_model=ValidateResponse, tags=["15.최종검증"])
def validate(req: ValidateRequest):
    return pipeline_mock.validate(req)
