from __future__ import annotations

import json
import logging
import re

import torch

from app.schemas.models import (
    ELEMENTS,
    SuggestRequest,
    SuggestResponse,
    Suggestion,
)
from app.services.diagnose_real import predict_missing
from app.services.hcx_runtime import (
    HCX_MODEL_LOCK,
    load_hcx_runtime,
)
from app.services.validation.semantic_validator import (
    calculate_similarities,
)


logger = logging.getLogger(__name__)

MAX_GENERATED_CANDIDATES = 5
MAX_EXPOSED_CANDIDATES = 3

# Suggest용 grounding 기준.
# 최종 응답 Validator의 DEFAULT_SEMANTIC_THRESHOLD(0.65)와 목적이 다르므로
# 별도 상수로 관리한다.
#
# 현재 값은 A/B 실측 결과를 기반으로 한 MVP 후보값이며,
# 다양한 업무 문장으로 추가 검증 후 재보정할 수 있다.
SUGGEST_GROUNDING_MIN_SCORE = 0.70
SUGGEST_GROUNDING_RELATIVE_MARGIN = 0.12


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
    return load_hcx_runtime()


def _finish_sentence(value: str) -> str:
    text = value.strip()

    if not text:
        return text

    if text[-1] in ".!?。！？":
        return text

    return f"{text}."


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


def _normalize_generated_candidate(
    value: str,
) -> str:
    text = value.strip()

    text = re.sub(
        r"^\s*(?:[-*•]|\d+[.)]|[ABCabc][.)])\s*",
        "",
        text,
    ).strip()

    if not text:
        return ""

    # placeholder는 실제 추천 문구가 아니므로 제거한다.
    if re.search(r"\[[^\]]+\]", text):
        return ""

    # "정보를 입력하세요" 같은 메타 지시도 사용자에게 노출하지 않는다.
    meta_phrases = (
        "정보를 입력",
        "내용을 입력",
        "정보를 추가",
        "내용을 추가",
        "추가 정보를",
        "구체적인 정보를",
        "보완해 주세요",
        "보완해주세요",
        # 실제 HCX 런타임에서 확인된 메타/지시형 출력
        "찾아보세요",
        "선택하세요",
        "제안받으세요",
        "제안 받아",
        "제공해 주세요",
        "제공해주세요",
        "작성해 보세요",
        "작성해보세요",
        "고려해 보세요",
        "고려해보세요",
    )

    if any(phrase in text for phrase in meta_phrases):
        return ""

    return _finish_sentence(text)


def _parse_generated_candidates(
    raw: str,
) -> list[str]:
    """
    HCX 출력:
    {
      "candidates": [
        "...",
        "...",
        "..."
      ]
    }

    JSON code fence나 앞뒤 텍스트가 붙어도
    JSON 객체 부분까지 한 번 복구한다.
    """
    text = raw.strip()

    if not text:
        raise RuntimeError(
            "HCX suggestion output is empty"
        )

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s*```$",
            "",
            text,
        ).strip()

    payload = None

    try:
        payload = json.loads(text)

    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:
            try:
                payload = json.loads(
                    text[start : end + 1]
                )
            except json.JSONDecodeError:
                payload = None

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Unable to parse HCX generated suggestions: {raw!r}"
        )

    raw_candidates = payload.get("candidates")

    if not isinstance(raw_candidates, list):
        raise RuntimeError(
            "HCX suggestion response does not contain candidates list"
        )

    candidates: list[str] = []

    for raw_candidate in raw_candidates:
        if not isinstance(raw_candidate, str):
            continue

        candidate = _normalize_generated_candidate(
            raw_candidate
        )

        if (
            candidate
            and candidate not in candidates
        ):
            candidates.append(candidate)

        if len(candidates) == MAX_GENERATED_CANDIDATES:
            break

    if not candidates:
        raise RuntimeError(
            "HCX generated no usable suggestion candidates"
        )

    return candidates



def _build_context_generation_prompt(
    *,
    text: str,
    context: str,
) -> str:
    """
    작은 HCX 모델이 CONTEXT 보완 목적을 명확히 이해하도록
    범용 지시 대신 짧고 직접적인 전용 프롬프트를 사용한다.

    여기서 모델의 역할은 새 사실을 만드는 것이 아니라
    제공된 업무 맥락을 '원문 뒤에 붙일 수 있는 문장'으로 재표현하는 것이다.
    """
    return (
        f"사용자 원문:\n{text}\n\n"
        f"반드시 유지할 업무 맥락:\n{context}\n\n"
        "위 업무 맥락의 사실만 사용해서, "
        "사용자 원문 뒤에 바로 붙일 수 있는 업무 조건 문장 5개를 작성해.\n\n"
        "규칙:\n"
        "1. 업무 맥락의 핵심 사실과 목적을 그대로 유지해.\n"
        "2. 제공되지 않은 사실, 일정, 프로젝트, 사람, 회사, 수치, 결과를 추가하지 마.\n"
        "3. 사용자에게 질문하거나 행동을 지시하지 마.\n"
        "4. '찾아보세요', '선택하세요', '제공해 주세요', "
        "'추가하세요' 같은 메타 표현을 쓰지 마.\n"
        "5. 각 후보는 그 자체로 완결된 업무 배경/목적 문장이어야 해.\n"
        "6. 표현만 다르게 하고 핵심 의미는 바꾸지 마.\n"
        "7. 원문의 TASK를 바꾸거나 FORMAT/TONE/LENGTH 조건을 새로 만들지 마.\n"
        "8. 설명 없이 아래 JSON 형식만 출력해.\n\n"
        "{\n"
        '  "candidates": [\n'
        '    "문장 1",\n'
        '    "문장 2",\n'
        '    "문장 3",\n'
        '    "문장 4",\n'
        '    "문장 5"\n'
        "  ]\n"
        "}"
    )

def _build_generation_prompt(
    *,
    text: str,
    context: str | None,
    element: str,
) -> str:
    description = ELEMENT_DESCRIPTIONS[element]

    context_text = (
        context.strip()
        if context and context.strip()
        else "별도 업무 맥락 없음"
    )

    return (
        f"사용자 원문:\n{text}\n\n"
        f"업무 맥락:\n{context_text}\n\n"
        f"보완할 요소: {element}\n"
        f"요소 의미: {description}\n\n"

        f"사용자가 클릭하면 원문 뒤에 바로 추가할 수 있는 "
        f"추천 문구를 {MAX_GENERATED_CANDIDATES}개 생성해.\n"

        "고정된 후보를 선택하지 말고, 사용자 원문과 제공된 업무 맥락을 "
        "해석해서 이번 요청에 적합한 추천 문구를 직접 작성해.\n\n"

        "가장 중요한 원칙:\n"
        "- 추천은 제공된 정보를 재표현하거나 선택하기 쉽게 만드는 것이다.\n"
        "- 제공되지 않은 업무 상황이나 사실을 새로 만들어내는 것이 아니다.\n\n"

        "규칙:\n"
        "1. 각 후보는 원문 뒤에 바로 붙여도 자연스러운 완결된 문장이어야 해.\n"
        f"2. 각 후보는 {element} 요소를 실제로 보완해야 해.\n"
        "3. 가장 적합한 후보부터 순서대로 작성해.\n"
        "4. 후보들은 서로 의미나 표현이 충분히 달라야 해.\n"
        "5. 업무 맥락이 제공되었다면 그 맥락에 명시된 사실만 사용해.\n"
        "6. 업무 맥락을 확대 해석해서 새로운 상황을 만들어내지 마.\n"
        "7. 원문이나 업무 맥락에 없는 프로젝트, 참석자, 직급, 회사명, "
        "고객, 일정, 날짜, 금액, 수치, 의사결정 내용을 새로 만들지 마.\n"
        "8. 추천은 새로운 사실을 창작하는 문장이 아니라 제공된 맥락을 "
        "프롬프트에 추가하기 좋은 형태로 재표현한 문장이어야 해.\n"
        "9. 업무 맥락이 제공된 경우 그 맥락과 직접 연결되지 않는 후보를 만들지 마.\n"
        "10. 업무 맥락이 없으면 구체적인 사실을 단정하지 말고 "
        "일반적으로 사용자가 선택할 수 있는 표현을 제안해.\n"
        "11. '[배경 정보]', '[대상]' 같은 placeholder를 출력하지 마.\n"
        "12. '정보를 추가하세요', '구체적으로 작성하세요' 같은 "
        "메타 지시문을 출력하지 마.\n"
        "13. 이유나 설명을 출력하지 마.\n\n"

        "아래 JSON 형식만 출력해:\n"
        "{\n"
        '  "candidates": [\n'
        '    "추천 문구 1",\n'
        '    "추천 문구 2",\n'
        '    "추천 문구 3",\n'
        '    "추천 문구 4",\n'
        '    "추천 문구 5"\n'
        "  ]\n"
        "}"
    )


def _generate_candidates(
    *,
    text: str,
    context: str | None,
    element: str,
) -> list[str]:
    """
    HCX가 사용자 원문 + 업무 맥락 + 부족 요소를 보고
    추천 후보 자체를 직접 생성한다.
    """
    tokenizer, model, device = _load_runtime()

    use_context_prompt = (
        element == "CONTEXT"
        and context is not None
        and context.strip()
    )

    if use_context_prompt:
        prompt = _build_context_generation_prompt(
            text=text,
            context=context.strip(),
        )
        system_content = (
            "너는 사용자가 제공한 업무 맥락을 "
            "프롬프트에 바로 붙일 수 있는 짧은 문장으로 재표현하는 도구다. "
            "새로운 사실을 만들지 말고 제공된 맥락의 의미만 유지한다. "
            "사용자에게 질문하거나 지시하지 않는다."
        )
    else:
        prompt = _build_generation_prompt(
            text=text,
            context=context,
            element=element,
        )
        system_content = (
            "너는 업무용 프롬프트에서 부족한 조건을 보완할 "
            "선택형 추천 문구를 만드는 도구다. "
            "고정 후보를 사용하지 않고 사용자 원문과 업무 맥락을 "
            "해석하여 후보를 직접 생성한다. "
            "제공되지 않은 업무 상황이나 사실을 추측하거나 창작하지 않는다. "
            "업무 맥락이 주어졌다면 그 내용을 재표현하는 범위 안에서만 추천한다."
        )

    messages = [
        {
            "role": "system",
            "content": system_content,
        },
        {
            "role": "user",
            "content": prompt,
        },
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
                max_new_tokens=256,
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

    candidates = _parse_generated_candidates(
        raw
    )

    logger.info(
        "HCX generated suggestions element=%s count=%s raw=%r",
        element,
        len(candidates),
        raw,
    )

    return candidates


def _merge_prompt_with_candidate(
    text: str,
    candidate: str,
) -> str:
    base = text.strip()
    addition = candidate.strip()

    if base and base[-1] not in ".!?。！？":
        base = f"{base}."

    return f"{base} {addition}".strip()


def _filter_context_grounded_candidates(
    *,
    context: str,
    candidates: list[str],
) -> list[str]:
    """
    CONTEXT 후보가 제공된 업무 맥락과 지나치게 동떨어지지 않았는지
    BGE-M3 의미 유사도로 사전 필터링한다.

    BGE-M3는 사실 검증/NLI 모델이 아니므로 환각 여부를 단독 판정하지 않는다.
    최고 점수 후보와의 상대 거리 + 최소 점수만 사용해
    명백히 맥락에서 벗어난 후보를 제거한다.

    후보의 기존 순서는 유지한다.
    """
    if not context.strip():
        return candidates

    if not candidates:
        return []

    scores = calculate_similarities(
        reference=context,
        candidates=candidates,
    )

    if len(scores) != len(candidates):
        raise RuntimeError(
            "Grounding score count does not match candidate count."
        )

    best_score = max(scores)

    cutoff = max(
        SUGGEST_GROUNDING_MIN_SCORE,
        best_score - SUGGEST_GROUNDING_RELATIVE_MARGIN,
    )

    grounded_candidates: list[str] = []

    for candidate, score in zip(
        candidates,
        scores,
        strict=True,
    ):
        logger.info(
            "Suggestion grounding "
            "score=%.4f cutoff=%.4f candidate=%r",
            score,
            cutoff,
            candidate,
        )

        if score >= cutoff:
            grounded_candidates.append(candidate)

        else:
            logger.info(
                "Generated suggestion rejected by context grounding "
                "score=%.4f cutoff=%.4f candidate=%r",
                score,
                cutoff,
                candidate,
            )

    return grounded_candidates





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
        if (
            baseline.get(other) == 0
            and after.get(other) == 1
        ):
            return False

    return True


def _validate_generated_candidates(
    *,
    text: str,
    element: str,
    candidates: list[str],
    baseline: dict[str, int],
) -> list[str]:
    """
    HCX가 생성한 순서 그대로 KcELECTRA로 재진단한다.
    """
    valid: list[str] = []

    for candidate in candidates:
        merged = _merge_prompt_with_candidate(
            text,
            candidate,
        )

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
                "Generated suggestion rejected by diagnosis guard "
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

    baseline_missing = predict_missing(
        req.text
    )

    context = (
        req.context.strip()
        if req.context and req.context.strip()
        else None
    )

    for element in target_elements:
        if baseline_missing.get(element) != 1:
            continue

        # CONTEXT는 현재 요청에 대한 명시적 업무 맥락이 없으면
        # HCX가 사실을 추측해서 만들지 않도록 fail-closed 처리한다.
        # 이 경우 suggestions=[]로 반환하고 Frontend의 되묻기/직접 입력으로 보완한다.
        if element == "CONTEXT" and not context:
            logger.info(
                "Skip ungrounded CONTEXT suggestion because "
                "no explicit context was provided text=%r",
                req.text,
            )
            continue

        try:
            candidates = _generate_candidates(
                text=req.text,
                context=context,
                element=element,
            )

        except Exception:
            # HCX 동적 생성 실패 시 고정 추천으로 fallback하지 않는다.
            logger.exception(
                "HCX dynamic suggestion generation failed "
                "element=%s",
                element,
            )
            continue

        grounded_candidates = candidates

        # 업무 맥락 자체를 보완하는 CONTEXT 추천에만 BGE grounding을 적용한다.
        # FORMAT/TONE/LENGTH 같은 선택형 요소에는 context 유사도를 강제하지 않는다.
        if element == "CONTEXT" and context:
            try:
                grounded_candidates = (
                    _filter_context_grounded_candidates(
                        context=context,
                        candidates=candidates,
                    )
                )
            except Exception:
                # Grounding 검증에 실패했다고 해서 검증을 우회해
                # 미검증 후보를 노출하지 않는다.
                logger.exception(
                    "BGE-M3 suggestion grounding failed "
                    "element=%s",
                    element,
                )
                continue

        if not grounded_candidates:
            logger.warning(
                "No context-grounded generated suggestion "
                "element=%s text=%r",
                element,
                req.text,
            )
            continue

        valid_candidates = _validate_generated_candidates(
            text=req.text,
            element=element,
            candidates=grounded_candidates,
            baseline=baseline_missing,
        )

        # Grounding과 Diagnosis Guard를 모두 통과한 후보만 노출한다.
        # 안전한 후보가 없으면 고정 fallback이나 추가 재생성 없이 빈 추천으로 끝낸다.

        if not valid_candidates:
            logger.warning(
                "No diagnosis-safe generated suggestion "
                "element=%s text=%r",
                element,
                req.text,
            )
            continue

        exposed_candidates = valid_candidates[
            :MAX_EXPOSED_CANDIDATES
        ]

        suggestions.append(
            Suggestion(
                element=element,
                primary=exposed_candidates[0],
                alternatives=exposed_candidates[1:],
            )
        )

    return SuggestResponse(
        suggestions=suggestions
    )