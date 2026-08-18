from __future__ import annotations

import logging
import os
import threading
from functools import lru_cache

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


logger = logging.getLogger(__name__)

HCX_MODEL_LOCK = threading.Lock()


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

    logger.info(
        "Loaded shared HCX model=%s device=%s",
        model_name,
        device,
    )

    return tokenizer, model, device
