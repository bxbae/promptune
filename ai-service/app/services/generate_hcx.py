from __future__ import annotations

import logging

import torch

from app.schemas.models import GenerateRequest, GenerateResponse
from app.services.hcx_runtime import HCX_MODEL_LOCK, load_hcx_runtime


logger = logging.getLogger(__name__)


def _build_internal_context(req: GenerateRequest) -> str:
    if not req.documents:
        return "없음"

    parts: list[str] = []

    for index, doc in enumerate(req.documents, start=1):
        content = doc.content.strip()

        # MVP 단계에서 과도하게 긴 context가 들어가는 것을 방지
        if len(content) > 1500:
            content = content[:1500]

        parts.append(
            f"[내부 문서 {index}]\n"
            f"제목: {doc.title}\n"
            f"내용: {content}"
        )

    return "\n\n".join(parts)


def _build_web_context(web_results: list[dict]) -> str:
    if not web_results:
        return "없음"

    parts: list[str] = []

    for index, item in enumerate(web_results, start=1):
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        content = str(item.get("content", "")).strip()

        if len(content) > 1200:
            content = content[:1200]

        parts.append(
            f"[웹 검색 결과 {index}]\n"
            f"제목: {title}\n"
            f"URL: {url}\n"
            f"내용: {content}"
        )
    return "\n\n".join(parts)


def _build_prompt(
    req: GenerateRequest,
    web_results: list[dict],
) -> str:
    internal_context = _build_internal_context(req)
    web_context = _build_web_context(web_results)

    return (
        "너는 업무용 AI 어시스턴트다.\n"
        "사용자의 요청과 제공된 참고자료를 바탕으로 "
        "정확하고 자연스러운 최종 답변을 작성해.\n\n"
        "규칙:\n"
        "1. 참고자료에 없는 사실을 임의로 만들어내지 마.\n"
        "2. 내부 문서가 있으면 해당 내용을 우선적으로 활용해.\n"
        "3. 웹 검색 결과가 있으면 최신 정보의 근거로 활용해.\n"
        "4. 참고자료가 부족하면 확실하지 않은 내용을 단정하지 마.\n"
        "5. 최종 답변만 출력하고 분석 과정은 출력하지 마.\n\n"
        f"[업무 유형]\n{req.task_type}\n\n"
        f"[사용자 요청]\n{req.prompt}\n\n"
        f"[내부 문서]\n{internal_context}\n\n"
        f"[웹 검색 결과]\n{web_context}\n\n"
        "[최종 답변]"
    )

def generate(
    req: GenerateRequest,
    web_results=None,
    used_web_search: bool = False,
) -> GenerateResponse:
    web_results = web_results or []

    tokenizer, model, device = load_hcx_runtime()

    prompt = _build_prompt(req=req, web_results=web_results)

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

    with HCX_MODEL_LOCK:
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=768,
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

    result = tokenizer.decode(
        generated,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    ).strip()

    logger.info(
        "HCX final generation task_type=%s web=%s documents=%d",
        req.task_type,
        used_web_search,
        len(req.documents),
    )

    return GenerateResponse(
        result=result,
        used_web_search=used_web_search,
    )
