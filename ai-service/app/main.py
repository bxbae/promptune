"""
PrompTune AI Service (FastAPI).

단계 5, 7, 8, 13, 14, 15를 담당한다.
각 AI 기능은 mock과 실제 구현을 독립적으로 전환할 수 있다.
"""

import os

from fastapi import FastAPI

from app.routers import pipeline


USE_REAL_MODELS = (
    os.getenv("USE_REAL_MODELS", "false").lower() == "true"
)

USE_REAL_DIAGNOSIS = (
    os.getenv(
        "USE_REAL_DIAGNOSIS",
        str(USE_REAL_MODELS),
    ).lower()
    == "true"
)


app = FastAPI(
    title="PrompTune AI Service",
    description="8요소 진단·추천·생성·검증 AI Service",
    version="0.2.0",
)

app.include_router(
    pipeline.router,
    prefix="/api/ai",
)


@app.get("/health", tags=["시스템"])
def health():
    return {
        "status": "ok",
    }


@app.get("/mock-status", tags=["시스템"])
def mock_status():
    """현재 각 파이프라인 단계의 mock/real 상태."""

    return {
        "use_real_models": USE_REAL_MODELS,
        "use_real_diagnosis": USE_REAL_DIAGNOSIS,
        "stages": {
            "5_diagnose": (
                "real(KcELECTRA)"
                if USE_REAL_DIAGNOSIS
                else "mock(규칙)"
            ),
            "7_suggest": "mock(템플릿)",
            "8_safety": "real(규칙)",
            "13_retrieve": "mock(샘플)",
            "14_generate": "mock(템플릿)",
            "15_validate": "mock(규칙)",
        },
    }