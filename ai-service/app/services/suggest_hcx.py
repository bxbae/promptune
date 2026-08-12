from __future__ import annotations

import logging
import os
import re
import threading
from functools import lru_cache

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.schemas.models import (
    SuggestRequest,
    SuggestResponse,
    Suggestion,
)
from app.services.candidate_bank import (
    ELEMENTS,
    get_candidates,
)


logger = logging.getLogger(__name__)

_MODEL_LOCK = threading.Lock()


ELEMENT_DESCRIPTIONS: dict[str, str] = {
    "TASK": "AI가 무엇을 대상으로 어떤 작업을 수행해야 하는지 지정하는 조건",
    "AUDIENCE": "결과물을 누가 읽거나 검토할지 지정하는 조건",
    "CONTEXT": "업무의 배경, 상황, 목적 또는 전제를 알려 주는 조건",
    "FORMAT": "결과물을 표, 목록, 문단 등 어떤 형태로 작성할지 지정하는 조건",
    "TONE": "결과물의 말투나 문체를 지정하는 조건",
    "LENGTH": "결과물의 분량이나 길이를 지정하는 조건",
    "CONSTRAINT": "반드시 지키거나 제외해야 하는 내용상의 규칙을 지정하는 조건",
    "EXAMPLE": "원하는 결과의 형태나 내용을 참고할 수 있는 예시를 지정하는 조건",
}


@lru_cache(maxsize=1)
def _load_runtime():
    model_name = os.getenv(
        "HF_HCX_MODEL",
        "naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B",
    )

    token = os.getenv("HF_TOKEN")
    device = os.getenv("HF_HCX_DEVICE", "cpu").strip().lower()

    if not token:
        raise RuntimeError(
            "HF_TOKEN is required when real suggestion mode is enabled"
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
        "Loaded HCX reranker model=%s device=%s",
        model_name,
        device,
    )

    return tokenizer, model, device


def _build_prompt(
    text: str,
    context: str | None,
    element: str,
    candidates: list[str],
) -> str:
    if len(candidates) != 3:
        raise ValueError(
            "HCX reranker requires exactly 3 candidates"
        )

    description = ELEMENT_DESCRIPTIONS[element]

    context_text = (
    context.strip()
    if context and context.strip()
    else "별도 업무 맥락 없음"
)

    return (
        f"사용자 원문: {text}\n"
        f"업무 맥락: {context_text}\n"
        f"보완할 요소: {element}\n"
        f"요소 의미: {description}\n\n"
        f"아래 후보는 모두 {element} 요소를 보완하는 문구다.\n"
        "사용자 원문과 업무 문맥에 가장 자연스럽고 유용한 "
        "후보 하나를 선택해.\n\n"
        f"A. {candidates[0]}\n"
        f"B. {candidates[1]}\n"
        f"C. {candidates[2]}\n\n"
        "설명하지 말고 A, B, C 중 하나의 글자만 출력해."
    )


def _parse_choice(
    raw: str,
    candidates: list[str],
) -> int:
    text = raw.strip()

    match = re.match(
        r'^\s*["\'`\(\[]*\s*([ABC])(?:\s|[.\):,\-\]]|번|$)',
        text.upper(),
    )

    if match:
        return {
            "A": 0,
            "B": 1,
            "C": 2,
        }[match.group(1)]

    for index, candidate in enumerate(candidates):
        if text == candidate:
            return index

    raise RuntimeError(
        f"Unable to parse HCX reranker output: {raw!r}"
    )


def _rerank(
    text: str,
    context: str | None,
    element: str,
    candidates: list[str],
) -> int:
    tokenizer, model, device = _load_runtime()

    prompt = _build_prompt(
        text=text,
        context=context,
        element=element,
        candidates=candidates,
    )

    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )

    inputs = inputs.to(device)

    with _MODEL_LOCK:
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=4,
                do_sample=False,
                eos_token_id=tokenizer.eos_token_id,
                stop_strings=[
                    "<|endofturn|>",
                    "<|stop|>",
                ],
                tokenizer=tokenizer,
            )

    generated = outputs[0][
        inputs["input_ids"].shape[-1]:
    ]

    raw = tokenizer.decode(
        generated,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    ).strip()

    choice = _parse_choice(
        raw=raw,
        candidates=candidates,
    )

    logger.info(
        "HCX rerank element=%s raw=%r choice=%s",
        element,
        raw,
        ("A", "B", "C")[choice],
    )

    return choice


def _normalize_target_elements(
    target_elements: list[str],
) -> list[str]:
    normalized: list[str] = []

    for raw in target_elements:
        element = raw.strip().upper()

        if element not in ELEMENTS:
            raise ValueError(
                f"Unsupported target element: {raw}"
            )

        if element not in normalized:
            normalized.append(element)

    if len(normalized) > 3:
        raise ValueError(
            "target_elements supports at most 3 elements"
        )

    return normalized


def suggest(
    req: SuggestRequest,
) -> SuggestResponse:
    target_elements = _normalize_target_elements(
        req.target_elements
    )

    suggestions: list[Suggestion] = []

    context = (
        req.context.strip()
        if req.context and req.context.strip()
        else None
    )

    for element in target_elements:
        candidates = get_candidates(
            element=element,
            text=req.text,
            context=context,
            limit=3,
        )

        selected_index = _rerank(
            text=req.text,
            context=context,
            element=element,
            candidates=candidates,
        )

        primary = candidates[selected_index]

        alternatives = [
            candidate
            for index, candidate in enumerate(candidates)
            if index != selected_index
        ]

        suggestions.append(
            Suggestion(
                element=element,
                primary=primary,
                alternatives=alternatives[:2],
            )
        )

    return SuggestResponse(
        suggestions=suggestions
    )