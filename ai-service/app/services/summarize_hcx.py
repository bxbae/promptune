from __future__ import annotations

import logging
import os
from functools import lru_cache

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.schemas.models import SummarizeTitleRequest, SummarizeTitleResponse


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_runtime():
    # suggest_hcx.py와 동일한 모델을 재사용합니다 (이미 로드된 모델이 있다면
    # 캐시 공유 여부는 실제 서버 구조 보시고 판단해주세요 — 별도 프로세스면
    # 어차피 각자 로드됩니다).
    model_name = os.getenv(
        "HF_HCX_MODEL",
        "naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B",
    )

    token = os.getenv("HF_TOKEN")
    device = os.getenv("HF_HCX_DEVICE", "cpu").strip().lower()

    if not token:
        raise RuntimeError(
            "HF_TOKEN is required when real title summary mode is enabled"
        )

    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("HF_HCX_DEVICE=cuda but CUDA is not available")

    tokenizer = AutoTokenizer.from_pretrained(model_name, token=token)
    model = AutoModelForCausalLM.from_pretrained(model_name, token=token)
    model.to(device)
    model.eval()

    logger.info("Loaded HCX title-summary model=%s device=%s", model_name, device)

    return tokenizer, model, device


def _build_prompt(text: str) -> str:
    return (
        f"다음 문장을 대화 목록에 표시할 15자 이내의 짧은 제목으로 요약해줘.\n"
        f"설명 없이 제목만 출력해.\n\n"
        f"문장: {text}\n\n"
        f"제목:"
    )


def summarize_title(req: SummarizeTitleRequest) -> SummarizeTitleResponse:
    tokenizer, model, device = _load_runtime()

    prompt = _build_prompt(req.text)

    messages = [{"role": "user", "content": prompt}]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    inputs = inputs.to(device)

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=20,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            stop_strings=["<|endofturn|>", "<|stop|>"],
            tokenizer=tokenizer,
        )

    generated = outputs[0][inputs["input_ids"].shape[-1]:]

    title = tokenizer.decode(
        generated, skip_special_tokens=True, clean_up_tokenization_spaces=False
    ).strip()

    # 혹시 모델이 너무 길게 답하면 안전하게 잘라줌
    if len(title) > 30:
        title = title[:30]

    logger.info("Title summary input=%r output=%r", req.text, title)

    return SummarizeTitleResponse(title=title)