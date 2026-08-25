from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from functools import lru_cache

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


logger = logging.getLogger(__name__)
# 2026-08-25: 벤치마크에서 "모델 로딩 시간"이 컨테이너 로그에 안 찍히는 문제
# 확인됨 — root logger에 별도 핸들러가 없으면 Python logging의
# "handler of last resort"가 WARNING 이상만 stderr로 내보내서,
# logger.info()로 남긴 load_seconds= 로그가 조용히 버려지고 있었음
# (반면 logger.exception()은 ERROR라 통과되어 보였던 것). 다른 모듈/전역
# 로깅 설정은 건드리지 않고, 이 로거에만 INFO 레벨 핸들러를 직접 달아서
# 확실히 컨테이너 로그(docker logs)에 찍히게 함.
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.INFO)
    _handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s: %(message)s"))
    logger.addHandler(_handler)

HCX_MODEL_LOCK = threading.Lock()


class HcxBusyError(RuntimeError):
    """HCX 모델이 다른 요청을 처리 중이라 제한시간 안에 락을 얻지 못했을 때."""


@contextmanager
def hcx_lock(timeout: float = 120.0):
    """
    HCX_MODEL_LOCK을 무한정 blocking으로 기다리지 않고, timeout 안에 못 얻으면
    HcxBusyError를 던진다.

    2026-08-25: 답변 생성(generate_hcx)뿐 아니라 문맥 재작성(conversation_context),
    추천(suggest_hcx), 개선(improve_hcx)까지 real HCX를 쓰는 모든 경로가 이
    락 하나를 공유한다 (CPU 인스턴스 하나에 모델을 한 벌만 올려두는 구조라
    동시 추론이 안전하지 않아서 의도적으로 직렬화함). 문제는 이전엔 무한정
    blocking이라, 동시에 여러 요청(특히 테스트 트래픽 + 실사용자)이 겹치면
    뒤로 밀린 요청이 몇 분씩 조용히 대기하다가 nginx 타임아웃(5분)에야 애매한
    504/네트워크 오류로 실패했음. 이제는 더 짧게(기본 120초) 실패해서, 호출부가
    빠르고 명확하게 "지금 바쁘다"고 응답할 수 있게 한다.
    """
    acquired = HCX_MODEL_LOCK.acquire(timeout=timeout)
    if not acquired:
        raise HcxBusyError(
            "AI 모델이 다른 요청을 처리하고 있어 제한시간 안에 시작하지 못했습니다."
        )
    try:
        yield
    finally:
        HCX_MODEL_LOCK.release()


@lru_cache(maxsize=1)
def load_hcx_runtime():
    model_name = os.getenv(
        "HF_HCX_MODEL",
        "naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B",
    )

    token = os.getenv("HF_TOKEN")
    device = os.getenv("HF_HCX_DEVICE", "cpu").strip().lower()

    if not token:
        raise RuntimeError(
            "HF_TOKEN is required when real HyperCLOVA X mode is enabled"
        )

    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            "HF_HCX_DEVICE=cuda but CUDA is not available"
        )

    # 2026-08-25: CPU vs GPU 벤치마크에서 "모델 로딩 시간"을 "생성 시간"과
    # 분리해서 보려고 명시적으로 측정/로깅. 이 함수 전체(tokenizer/model
    # from_pretrained + device로 옮기는 것까지)가 lru_cache로 최초 1회만
    # 실행되므로, 컨테이너 기동 후 첫 요청에만 이 로그가 찍힌다.
    load_start = time.monotonic()

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        token=token,
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        token=token,
    )

    model.to(device)
    model.eval()

    load_elapsed = time.monotonic() - load_start

    logger.info(
        "Loaded shared HCX model=%s device=%s load_seconds=%.2f",
        model_name,
        device,
        load_elapsed,
    )

    return tokenizer, model, device
