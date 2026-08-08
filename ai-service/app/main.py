"""
PrompTune AI Service (FastAPI) — 목업.
단계 5,7,8,13,14,15을 담당. 흐름도의 "프롬프트 분석/수정 추천" + "결과 생성" 영역.

실행: uvicorn app.main:app --reload --port 8000
문서: http://localhost:8000/docs
"""
import os
from fastapi import FastAPI
from app.routers import pipeline

USE_REAL_MODELS = os.getenv("USE_REAL_MODELS", "false").lower() == "true"

app = FastAPI(
    title="PrompTune AI Service",
    description="8요소 진단·추천·생성·검증 (목업). 모델은 mock, 형식은 실제와 동일.",
    version="0.1.0-mock",
)

app.include_router(pipeline.router, prefix="/api/ai")


@app.get("/health", tags=["시스템"])
def health():
    return {"status": "ok"}


@app.get("/mock-status", tags=["시스템"])
def mock_status():
    """지금 mock인지 실제 모델인지 확인."""
    return {
        "use_real_models": USE_REAL_MODELS,
        "stages": {
            "5_diagnose": "real(KcELECTRA)" if USE_REAL_MODELS else "mock(규칙)",
            "7_suggest": "real(HyperCLOVA)" if USE_REAL_MODELS else "mock(템플릿)",
            "8_safety": "real(규칙)",   # 항상 실제
            "13_retrieve": "real(BGE-M3)" if USE_REAL_MODELS else "mock(샘플)",
            "14_generate": "real(HyperCLOVA)" if USE_REAL_MODELS else "mock(템플릿)",
            "15_validate": "real(NLI+HyperCLOVA)" if USE_REAL_MODELS else "mock(규칙)",
        },
    }
