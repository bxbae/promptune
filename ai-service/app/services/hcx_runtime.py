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
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.INFO)
    _handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s: %(message)s"))
    logger.addHandler(_handler)

HCX_MODEL_LOCK = threading.Lock()
HCX_LOAD_LOCK = threading.Lock()


def _resolve_hcx_device(requested: str) -> str:
    value = (requested or "auto").strip().lower()

    if value == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"

    if value.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError(
            f"HF_HCX_DEVICE={value} but CUDA is not available"
        )

    if value not in {"cpu", "cuda", "cuda:0"} and not value.startswith("cuda:"):
        raise RuntimeError(f"지원하지 않는 HF_HCX_DEVICE 값입니다: {value}")

    return value


def _resolve_hcx_dtype(device: str, requested: str):
    value = (requested or "auto").strip().lower()

    if value == "auto":
        return torch.float16 if device.startswith("cuda") else torch.float32

    aliases = {
        "float32": torch.float32,
        "fp32": torch.float32,
        "float16": torch.float16,
        "fp16": torch.float16,
        "bfloat16": torch.bfloat16,
        "bf16": torch.bfloat16,
    }

    if value not in aliases:
        raise RuntimeError(f"지원하지 않는 HF_HCX_DTYPE 값입니다: {value}")

    dtype = aliases[value]
    if not device.startswith("cuda") and dtype != torch.float32:
        logger.warning(
            "Non-CUDA HCX runtime requested dtype=%s; falling back to float32",
            value,
        )
        return torch.float32

    return dtype


def hcx_runtime_config() -> dict[str, str]:
    requested_device = os.getenv("HF_HCX_DEVICE", "auto")
    device = _resolve_hcx_device(requested_device)
    dtype = _resolve_hcx_dtype(
        device,
        os.getenv("HF_HCX_DTYPE", "auto"),
    )
    return {
        "requested_device": requested_device,
        "device": device,
        "dtype": str(dtype).replace("torch.", ""),
    }


class HcxBusyError(RuntimeError):
    """HCX 모델이 다른 요청을 처리 중이라 제한시간 안에 락을 얻지 못했을 때."""


@contextmanager
def hcx_lock(timeout: float | None = None):
    """
    HCX_MODEL_LOCK을 무한정 blocking으로 기다리지 않고, timeout 안에 못 얻으면
    HcxBusyError를 던진다.
    """
    if timeout is None:
        timeout = float(os.getenv("HCX_LOCK_TIMEOUT_SECONDS", "120"))

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
def _load_hcx_runtime_cached():
    model_name = os.getenv(
        "HF_HCX_MODEL",
        "naver-hyperclovax/HyperCLOVAX-SEED-Vision-Instruct-3B",
    )

    token = os.getenv("HF_TOKEN")
    config = hcx_runtime_config()
    device = config["device"]
    dtype = _resolve_hcx_dtype(device, os.getenv("HF_HCX_DTYPE", "auto"))

    load_start = time.monotonic()

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        token=token,
        trust_remote_code=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        token=token,
        trust_remote_code=True,
        torch_dtype=dtype,
        low_cpu_mem_usage=False,
    )

    model.to(device)
    model.eval()

    load_elapsed = time.monotonic() - load_start

    logger.info(
        "Loaded shared HCX model=%s device=%s dtype=%s load_seconds=%.2f",
        model_name,
        device,
        str(dtype).replace("torch.", ""),
        load_elapsed,
    )

    return tokenizer, model, device

def load_hcx_runtime():
    """Return the single shared HCX runtime without duplicate first-load races."""
    with HCX_LOAD_LOCK:
        return _load_hcx_runtime_cached()
