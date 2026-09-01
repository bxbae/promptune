from __future__ import annotations

import re

from app.services.documents.document_composer import (
    _fallback_content,
    compose_document,
)
from app.services.documents.document_planner import (
    _fallback_plan,
    build_document_plan,
)
from app.services.documents.docx_renderer import render_docx
from app.services.documents.docx_to_pdf import render_pdf_from_docx
from app.services.documents.layout_planner import apply_layout_plan


def _safe_filename(title: str) -> str:
    value = re.sub(
        r'[\\/:*?"<>|]+',
        "_",
        str(title or "").strip(),
    )

    return value or "document"


def _is_instruction_only_request(content: str) -> bool:
    """
    실제 문서에 채울 사실은 없고
    '보고서 만들어줘 / 빈 양식 만들어줘' 같은 생성 지시만 있는 요청인지 판단한다.

    이런 요청은 HCX Planner/Composer를 두 번 돌리지 않고
    deterministic fallback + renderer를 사용한다.
    """
    source = str(content or "").strip()

    if not source:
        return True

    # Backend의 enrichDocumentRequest()가 붙이는 규칙은
    # 실제 사용자 자료가 아니므로 판단에서 제외한다.
    user_part = source.split(
        "[문서 생성 규칙]",
        1,
    )[0].strip()

    value = user_part.lower()

    # 문서 생성 요청이어야 한다.
    has_document = bool(re.search(
        r"(업무\s*보고서|주간\s*보고서|월간\s*보고서|"
        r"보고서|회의록|계획서|제안서|시말서|경위서|"
        r"사유서|소명서|공지문|안내문|문서|양식|템플릿)",
        value,
    ))

    has_create = bool(re.search(
        r"(만들어|생성해|작성해|써줘|제작해|구성해)",
        value,
    ))

    if not (has_document and has_create):
        return False

    # 문서 종류/생성 지시와 흔한 빈 양식 표현을 제거한 뒤
    # 실제 사실성 내용이 남는지 확인한다.
    residual = value

    patterns = [
        r"업무\s*보고서",
        r"주간\s*보고서",
        r"월간\s*보고서",
        r"보고서",
        r"회의록",
        r"계획서",
        r"제안서",
        r"시말서",
        r"경위서",
        r"사유서",
        r"소명서",
        r"공지문",
        r"안내문",
        r"문서",
        r"양식",
        r"템플릿",
        r"파일",
        r"형식",
        r"만들어\s*줘?",
        r"생성해\s*줘?",
        r"작성해\s*줘?",
        r"써\s*줘",
        r"제작해\s*줘?",
        r"구성해\s*줘?",
        r"내용이\s*부족한\s*부분은",
        r"정보가\s*부족하면",
        r"정보가\s*부족해도",
        r"빈\s*입력란",
        r"빈칸",
        r"작성용\s*placeholder",
        r"placeholder",
        r"형태로",
        r"바로",
    ]

    for pattern in patterns:
        residual = re.sub(
            pattern,
            " ",
            residual,
            flags=re.IGNORECASE,
        )

    residual = re.sub(
        r"[^0-9a-z가-힣]+",
        "",
        residual,
        flags=re.IGNORECASE,
    )

    # 의미 있는 사용자 자료가 거의 남지 않으면
    # 구조만 필요한 요청으로 본다.
    return len(residual) <= 5


def generate_smart_document(
    title: str,
    content: str,
    output_format: str,
) -> tuple[bytes, str, str]:
    fmt = output_format.strip().lower()

    if fmt not in {"docx", "pdf"}:
        raise ValueError(
            "Smart Document Generator는 현재 docx, pdf를 지원합니다."
        )

    request = (
        f"문서 제목: {title.strip()}\n\n"
        f"사용자 요청 및 원본 자료:\n"
        f"{content.strip()}"
    )

    if _is_instruction_only_request(content):
        # "보고서 만들어줘"처럼 실제 채울 사실이 없는 요청은
        # HCX 2회 추론을 건너뛰고 기존 fallback 구조를 사용한다.
        plan = _fallback_plan(request)

        if title.strip():
            plan.title = title.strip()

        composed = _fallback_content(
            plan,
            content.strip(),
        )
    else:
        # 실제 사용자 자료가 있으면 기존 Smart Document 경로 유지.
        plan = build_document_plan(request)

        if title.strip():
            plan.title = title.strip()

        composed = compose_document(
            plan,
            content.strip(),
        )

    if not composed.title.strip():
        composed.title = plan.title

    result = apply_layout_plan(
        plan,
        composed,
    )

    safe_title = _safe_filename(
        result.title or plan.title or title
    )

    if fmt == "docx":
        data = render_docx(result)

        return (
            data,
            f"{safe_title}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    data = render_pdf_from_docx(result)

    return (
        data,
        f"{safe_title}.pdf",
        "application/pdf",
    )
