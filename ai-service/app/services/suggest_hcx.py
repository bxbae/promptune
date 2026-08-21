from __future__ import annotations

import logging
import re

import torch

from app.schemas.models import (
    SuggestRequest,
    SuggestResponse,
    Suggestion,
)
from app.services.candidate_bank import (
    ELEMENTS,
    get_candidates,
)
from app.services.diagnose_real import predict_missing
from app.services.hcx_runtime import (
    HCX_MODEL_LOCK,
    load_hcx_runtime,
)


logger = logging.getLogger(__name__)


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


def _load_runtime():
    """
    하위 호환용 래퍼.

    Promptune의 HCX 기능들이 같은 모델 인스턴스와 락을 공유하도록
    실제 로딩은 hcx_runtime.load_hcx_runtime()에 위임한다.
    """
    return load_hcx_runtime()


def _finish_sentence(value: str) -> str:
    text = value.strip()
    if not text:
        return text
    if text[-1] in ".!?。！？":
        return text
    return f"{text}."


def _make_apply_ready_candidate(
    element: str,
    candidate: str,
) -> str:
    """
    candidate_bank의 짧은 조각을 사용자가 클릭했을 때 바로 원문 뒤에
    붙여도 의미가 완결되는 문장으로 바꾼다.

    특히 CONTEXT 후보의 기존 ``...라는 배경을 반영해서`` 표현은
    '배경을 넣으라'는 메타 지시에 가까워 KcELECTRA 재진단에서
    CONTEXT를 실제로 채운 것으로 인식하지 못할 수 있다.
    사용자가 후보를 직접 선택한 시점에는 그 선택을 사용자의 명시적
    확인으로 보고, 실제 배경/목적을 진술하는 형태로 바꾼다.
    """
    text = candidate.strip()
    if not text:
        return text

    if element == "CONTEXT":
        suffix = "라는 배경을 반영해서"
        if text.endswith(suffix):
            subject = text[: -len(suffix)].strip()
            if subject.endswith("자료"):
                return _finish_sentence(f"{subject}로 사용할 예정이야")
            return _finish_sentence(f"업무 배경은 {subject}이야")

    if element == "AUDIENCE" and text.endswith("대상으로"):
        return _finish_sentence(f"{text} 작성해줘")

    if element == "CONSTRAINT":
        if text.endswith("하지 말고"):
            return _finish_sentence(f"{text[:-1]}아줘")
        if text.endswith("제외하고"):
            return _finish_sentence(f"{text[:-2]}해줘")

    # FORMAT/TONE/LENGTH/EXAMPLE/일부 CONSTRAINT 후보는
    # "...해서" 형태이므로 클릭 후 바로 적용 가능한 지시문으로 바꾼다.
    if text.endswith("해서"):
        return _finish_sentence(f"{text[:-2]}해줘")

    return _finish_sentence(text)


def _prepare_candidates(
    element: str,
    candidates: list[str],
) -> list[str]:
    prepared: list[str] = []

    for candidate in candidates:
        normalized = _make_apply_ready_candidate(
            element=element,
            candidate=candidate,
        )
        if normalized and normalized not in prepared:
            prepared.append(normalized)

    if len(prepared) != 3:
        raise ValueError(
            "HCX reranker requires exactly 3 unique candidates "
            f"after normalization; element={element} count={len(prepared)}"
        )

    return prepared


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
        "아래 후보는 사용자가 직접 클릭해 원문 뒤에 추가할 선택지다.\n"
        f"각 후보는 {element} 요소를 실제로 보완할 수 있는 완결된 문장이다.\n"
        "사용자 원문과 제공된 업무 맥락에 가장 자연스럽고 유용한 "
        "후보 하나를 선택해.\n"
        "원문이나 업무 맥락에 근거가 없는 사람, 날짜, 숫자, 회사 정보 등 "
        "새로운 사실을 추측해서 우선하지 마.\n"
        "별도 업무 맥락이 없다면 가장 일반적이고 부담이 적은 후보를 선택해.\n\n"
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

    with HCX_MODEL_LOCK:
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



def _merge_prompt_with_candidate(text: str, candidate: str) -> str:
    base = text.strip()
    addition = candidate.strip()

    if base and base[-1] not in ".!?。！？":
        base = f"{base}."

    return f"{base} {addition}".strip()


def _candidate_is_diagnosis_safe(
    *,
    element: str,
    baseline: dict[str, int],
    after: dict[str, int],
) -> bool:
    if baseline.get(element) != 1:
        return False
    if after.get(element) != 0:
        return False

    for other in ELEMENTS:
        if baseline.get(other) == 0 and after.get(other) == 1:
            return False

    return True


def _validated_candidates_in_hcx_order(
    *,
    text: str,
    element: str,
    candidates: list[str],
    selected_index: int,
    baseline: dict[str, int],
) -> list[str]:
    order = [
        selected_index,
        *[i for i in range(len(candidates)) if i != selected_index],
    ]

    valid: list[str] = []

    for index in order:
        candidate = candidates[index]
        merged = _merge_prompt_with_candidate(text, candidate)

        try:
            after = predict_missing(merged)
        except Exception:
            logger.exception(
                "KcELECTRA suggestion validation failed "
                "element=%s candidate=%r",
                element,
                candidate,
            )
            continue

        if _candidate_is_diagnosis_safe(
            element=element,
            baseline=baseline,
            after=after,
        ):
            valid.append(candidate)
        else:
            logger.info(
                "Suggestion candidate rejected by diagnosis guard "
                "element=%s candidate=%r baseline=%s after=%s",
                element,
                candidate,
                baseline,
                after,
            )

    return valid


def suggest(
    req: SuggestRequest,
) -> SuggestResponse:
    target_elements = _normalize_target_elements(
        req.target_elements
    )

    suggestions: list[Suggestion] = []

    baseline_missing = predict_missing(req.text)

    context = (
        req.context.strip()
        if req.context and req.context.strip()
        else None
    )

    for element in target_elements:
        raw_candidates = get_candidates(
            element=element,
            text=req.text,
            context=context,
            limit=3,
        )

        candidates = _prepare_candidates(
            element=element,
            candidates=raw_candidates,
        )

        try:
            selected_index = _rerank(
                text=req.text,
                context=context,
                element=element,
                candidates=candidates,
            )
        except Exception:
            # 추천 기능 하나의 HCX rerank 실패가 /api/analyze 전체를 500으로
            # 만들지 않도록 deterministic fallback으로 첫 후보를 사용한다.
            logger.exception(
                "HCX suggestion rerank failed; using first candidate "
                "element=%s",
                element,
            )
            selected_index = 0

        valid_candidates = _validated_candidates_in_hcx_order(
            text=req.text,
            element=element,
            candidates=candidates,
            selected_index=selected_index,
            baseline=baseline_missing,
        )

        if not valid_candidates:
            logger.warning(
                "No diagnosis-safe suggestion candidate "
                "element=%s text=%r",
                element,
                req.text,
            )
            continue

        primary = valid_candidates[0]
        alternatives = valid_candidates[1:3]

        suggestions.append(
            Suggestion(
                element=element,
                primary=primary,
                alternatives=alternatives,
            )
        )

    return SuggestResponse(
        suggestions=suggestions
    )