"""
바른(Bareun) 맞춤법 검사 API 연동.

역할:
- 사용자 프롬프트의 맞춤법/띄어쓰기/표준어/오탈자 등을 검사
- 바른 API의 revisedBlocks를 PrompTune의 Typo(span, suggest) 형식으로 변환

주의:
- API Key는 코드에 직접 작성하지 않는다.
- BAREUN_API_KEY 환경변수에서 읽는다.
"""

import json
import logging
import os
from urllib import error, request

from app.schemas.models import Typo


logger = logging.getLogger(__name__)

DEFAULT_BAREUN_API_URL = "https://api.bareun.ai"
CORRECT_ERROR_PATH = "/bareun.RevisionService/CorrectError"


def _extract_typos(response_data: dict) -> list[Typo]:
    """
    바른 API revisedBlocks를 PrompTune Typo 형식으로 변환한다.

    정책:
    - 단순 구두점 교정은 제외한다.
    - helpId가 Merged이고 nested가 있으면 부모 결과 대신
      더 세밀한 nested 결과를 사용한다.
    """
    results: list[Typo] = []
    seen: set[tuple[str, str]] = set()

    blocks = response_data.get(
        "revisedBlocks",
        response_data.get("revised_blocks", []),
    )

    def add_block(block: dict) -> None:
        revisions = block.get("revisions", [])
        nested = block.get("nested") or []

        # Merged 블록은 여러 교정을 뭉친 결과이므로
        # 세부 nested 결과가 있으면 nested를 사용한다.
        is_merged = any(
            revision.get("helpId") == "Merged"
            for revision in revisions
        )

        if is_merged and nested:
            for child in nested:
                add_block(child)
            return

        # 단순 문장부호 교정 제외
        if revisions and all(
            revision.get("helpId") == "구두점"
            for revision in revisions
        ):
            return

        origin = block.get("origin") or {}

        span = str(origin.get("content", "")).strip()
        suggest = str(block.get("revised", "")).strip()

        if not span or not suggest:
            return

        if span == suggest:
            return

        key = (span, suggest)

        if key in seen:
            return

        seen.add(key)

        results.append(
            Typo(
                span=span,
                suggest=suggest,
            )
        )

    for block in blocks:
        add_block(block)

    return results


def check_spelling(text: str) -> list[Typo]:
    """
    바른 API를 호출해 맞춤법 검사 결과를 반환한다.

    Returns:
        list[Typo]

    Raises:
        RuntimeError:
            API Key 누락, HTTP 오류, 네트워크 오류,
            JSON 파싱 오류 등이 발생한 경우
    """
    if not text.strip():
        return []

    api_key = os.getenv("BAREUN_API_KEY", "").strip()
    base_url = os.getenv(
        "BAREUN_API_URL",
        DEFAULT_BAREUN_API_URL,
    ).strip()

    if not api_key:
        raise RuntimeError(
            "BAREUN_API_KEY 환경변수가 설정되어 있지 않습니다."
        )

    url = (
        base_url.rstrip("/")
        + CORRECT_ERROR_PATH
    )

    payload = {
        "document": {
            "content": text,
            "language": "ko-KR",
        },
        "encoding_type": "UTF32",
    }

    body = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    req = request.Request(
        url=url,
        data=body,
        method="POST",
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
        },
    )

    try:
        with request.urlopen(
            req,
            timeout=5,
        ) as response:
            response_body = response.read().decode("utf-8")

    except error.HTTPError as exc:
        error_body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        logger.error(
            "Bareun API HTTP error: status=%s body=%s",
            exc.code,
            error_body[:500],
        )

        raise RuntimeError(
            f"Bareun API 호출 실패: HTTP {exc.code}"
        ) from exc

    except error.URLError as exc:
        logger.error(
            "Bareun API network error: %s",
            exc.reason,
        )

        raise RuntimeError(
            "Bareun API 네트워크 연결에 실패했습니다."
        ) from exc

    try:
        response_data = json.loads(response_body)

    except json.JSONDecodeError as exc:
        logger.error(
            "Bareun API invalid JSON response: %s",
            response_body[:500],
        )

        raise RuntimeError(
            "Bareun API 응답을 JSON으로 해석할 수 없습니다."
        ) from exc

    return _extract_typos(response_data)

def merge_spellcheck_results(
    text: str,
    rule_typos: list[Typo],
    bareun_typos: list[Typo],
) -> list[Typo]:
    """
    Rule + Bareun 결과 병합.

    원칙:
    1. Rule은 고신뢰 오타 교정으로 우선한다.
    2. Bareun의 더 넓은 교정 결과 안에 Rule 대상이 포함되어 있고,
       Bareun suggestion에도 Rule 원문이 그대로 남아 있다면
       두 교정을 하나로 합친다.
    3. Bareun과 Rule이 충돌하면 Rule을 사용한다.
    """

    del text  # 현재 병합에서는 직접 사용하지 않음

    results: list[Typo] = []
    seen: set[tuple[str, str]] = set()

    # 긴 Rule부터 처리
    sorted_rules = sorted(
        rule_typos,
        key=lambda typo: len(typo.span),
        reverse=True,
    )

    covered_rule_indexes: set[int] = set()

    # 1. Bareun 결과를 먼저 살펴보면서
    #    Rule과 안전하게 결합 가능한 경우 결합
    for bareun in bareun_typos:
        suggest = bareun.suggest

        conflicting = False
        applied_rule_indexes: list[int] = []

        for index, rule in enumerate(sorted_rules):

            # Bareun 범위 안에 Rule 범위가 포함된 경우
            if rule.span in bareun.span:

                # Bareun suggestion 안에도 원래 오타가 남아 있으면
                # Rule 교정을 추가 적용할 수 있다.
                if rule.span in suggest:
                    suggest = suggest.replace(
                        rule.span,
                        rule.suggest,
                        1,
                    )
                    applied_rule_indexes.append(index)

                else:
                    # Bareun이 같은 영역을 다른 방식으로 바꿨다면
                    # Rule과 충돌하므로 Bareun 결과를 버린다.
                    conflicting = True
                    break

            # Bareun이 Rule 범위 내부에 있는 경우
            elif bareun.span in rule.span:
                conflicting = True
                break

        if conflicting:
            continue

        key = (bareun.span, suggest)

        if key in seen:
            continue

        results.append(
            Typo(
                span=bareun.span,
                suggest=suggest,
            )
        )

        seen.add(key)
        covered_rule_indexes.update(applied_rule_indexes)

    # 2. Bareun 결과에 이미 흡수되지 않은 Rule만 추가
    for index, rule in enumerate(sorted_rules):

        if index in covered_rule_indexes:
            continue

        key = (rule.span, rule.suggest)

        if key in seen:
            continue

        results.append(rule)
        seen.add(key)

    return results

def check_spelling_hybrid(text: str) -> list[Typo]:
    from app.services.diagnose_rules import detect_typos

    rule_typos = detect_typos(text)

    try:
        bareun_typos = check_spelling(text)
    except RuntimeError:
        # 바른 장애 / API Key 문제 발생 시
        # 5번 전체를 죽이지 않고 Rule만 반환
        return rule_typos

    return merge_spellcheck_results(
        text=text,
        rule_typos=rule_typos,
        bareun_typos=bareun_typos,
    )