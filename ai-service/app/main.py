"""
PrompTune AI Service (FastAPI).

단계 5, 7, 8, 13, 14, 15를 담당한다.
각 AI 기능은 mock과 실제 구현을 독립적으로 전환할 수 있다.
"""

import os

from fastapi import FastAPI

from app.routers import pipeline


USE_REAL_MODELS = os.getenv("USE_REAL_MODELS", "false").lower() == "true"

USE_REAL_DIAGNOSIS = (
    os.getenv(
        "USE_REAL_DIAGNOSIS",
        str(USE_REAL_MODELS),
    ).lower()
    == "true"
)

USE_REAL_SPELLCHECK = os.getenv("USE_REAL_SPELLCHECK", "false").lower() == "true"


USE_REAL_SUGGESTION = pipeline.USE_REAL_SUGGESTION

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


@app.get("/mock-status")
def mock_status():
    if USE_REAL_DIAGNOSIS:
        if USE_REAL_SPELLCHECK:
            stage5_status = "real(KcELECTRA + Bareun + Rule)"
        else:
            stage5_status = "real(KcELECTRA + Rule)"
    else:
        stage5_status = "mock"

    stage7_status = (
        "real(HyperCLOVA X SEED 1.5B reranker)"
        if USE_REAL_SUGGESTION
        else "mock(템플릿)"
    )

    return {
        "use_real_models": USE_REAL_MODELS,
        "use_real_diagnosis": USE_REAL_DIAGNOSIS,
        "use_real_spellcheck": USE_REAL_SPELLCHECK,
        "use_real_suggestion": USE_REAL_SUGGESTION,
        "stages": {
            "5_diagnose": stage5_status,
            "7_suggest": stage7_status,
            "8_safety": "real(규칙)",
            "13_retrieve": "mock(샘플)",
            "14_generate": "mock(템플릿)",
            "15_validate": "mock(규칙)",
        },
    }
