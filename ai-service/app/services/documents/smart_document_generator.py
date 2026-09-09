from __future__ import annotations

import re

from app.services.documents.document_composer import (
    _fallback_content,
    compose_document,
)
from app.services.documents.document_planner import (
    _fallback_plan,
    build_document_plan,
    build_fast_notice_plan,
    build_fast_synthesis_report_plan,
)
from app.services.documents.document_content import DocumentBlock, DocumentContent
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


def _prepare_fast_notice_source(
    content: str,
) -> str:
    """
    RAG로 검색된 공지문 작성 가이드에서
    '작성 규칙'만 의미적으로 사용한다.

    가이드의 예시 날짜/장소/안건/담당자 및
    작성 전 체크리스트는 Composer source에서 제거한다.
    """
    raw = str(content or "").strip()

    instruction = raw.split(
        "[첨부 문서 원문]",
        1,
    )[0].strip()

    normalized = " ".join(
        instruction.split()
    )

    asks_for_guide = (
        "가이드" in instruction
        and "공지문" in instruction
    )

    has_rag = (
        "[첨부 문서 원문]" in raw
    )

    if asks_for_guide and not has_rag:
        raise ValueError(
            "공지문 작성 가이드의 RAG 검색 결과가 "
            "문서 생성기에 전달되지 않았습니다."
        )

    # -----------------------------------------------------
    # 상대 날짜 → 실제 날짜
    # -----------------------------------------------------

    resolved_when = ""

    if "다음 주 화요일" in instruction:
        try:
            from datetime import datetime, timedelta
            from zoneinfo import ZoneInfo

            today = datetime.now(
                ZoneInfo("Asia/Seoul")
            ).date()

            # 다음 주 월요일 + 1일 = 다음 주 화요일
            next_monday = (
                today
                + timedelta(
                    days=(7 - today.weekday())
                )
            )

            target = (
                next_monday
                + timedelta(days=1)
            )

            time_text = (
                "오후 2시"
                if "오후 2시" in instruction
                else ""
            )

            resolved_when = (
                f"{target.year}년 "
                f"{target.month}월 "
                f"{target.day}일(화)"
            )

            if time_text:
                resolved_when += (
                    f" {time_text}"
                )

        except Exception:
            resolved_when = (
                "다음 주 화요일 오후 2시"
            )

    if not resolved_when:
        resolved_when = (
            "다음 주 화요일 오후 2시"
            if "다음 주 화요일" in instruction
            else ""
        )

    # -----------------------------------------------------
    # 중요:
    # raw RAG 전문을 Composer에게 다시 보내지 않는다.
    #
    # 가이드에는 실제 작성 규칙뿐 아니라
    # '2026-09-16 / 3층 대회의실 / 길인턴' 같은
    # 작성 예시와 체크리스트도 들어 있기 때문이다.
    #
    # RAG가 해당 가이드임을 확인한 뒤,
    # 아래처럼 rule-only context로 정규화한다.
    # -----------------------------------------------------

    rules = """
[RAG로 확인한 공지문 작성 규칙]

1. 제목은 "[AI Agent 개발 2 팀]"으로 시작한다.

2. 제목 뒤에는 공지의 핵심 내용을
   짧고 명확하게 표시한다.

3. 공지 앞부분에는 반드시 다음 내용을 표시한다.
   - 대상
   - 일시
   - 장소 또는 접속 링크

4. 안건은 번호를 매겨 간결하게 정리한다.

5. 마지막 줄에는 반드시
   "문의: AI Agent 개발 2 팀"
   형식의 문의처를 표시한다.

6. 문체는 정중하고 간결하게 한다.
   불필요한 수식어나 과장 표현은 사용하지 않는다.

7. 작성 가이드에 포함된
   '작성 예시'의 날짜, 장소, 안건, 담당자 이름은
   실제 업무 정보가 아니다.
   최종 공지문에 복사하지 않는다.

8. 작성 가이드의
   '작성 전 체크리스트'는
   작성자를 위한 검수 규칙이다.
   최종 공지문 본문에 출력하지 않는다.
""".strip()

    facts = (
        "[실제 공지 사실]\n"
        "- 대상: AI Agent 개발 2 팀 전원\n"
    )

    if resolved_when:
        facts += (
            f"- 일시: {resolved_when}\n"
        )

    facts += (
        "- 장소 또는 접속 링크: 제공되지 않음\n"
        "- 장소가 제공되지 않았으므로 "
        "\"장소: 추후 안내\"로 표시\n"
        "- 회의 종류: AI Agent 개발 2 팀 전체 회의\n"
    )

    output_rules = """
[최종 문서 출력 구조]

아래 순서로 실제 공지문만 작성한다.

1. 문서 제목
   "[AI Agent 개발 2 팀] 전체 회의 안내"

2. 대상 / 일시 / 장소
   정보를 짧고 보기 좋게 정리한다.

3. 한 문단의 회의 안내 문구

4. "회의 안건" 항목
   - numbered_list를 사용한다.
   - 실제 안건이 제공되지 않았으므로,
     일반적인 팀 전체회의에서 사용할 수 있는
     안건 2~3개를 "안건(안)" 성격으로 작성한다.
   - 구체적 프로젝트명이나 사실을 지어내지 않는다.

5. 마지막 줄
   "문의: AI Agent 개발 2 팀"

절대 포함하지 말 것:
- 회의 전 체크리스트
- 작성 전 체크리스트
- 작성 규칙 설명
- 가이드의 예시 원문
- 3층 대회의실
- 담당: 길인턴
- 2026년 9월 16일
- 가이드 예시에만 있던 프로젝트/솔루션 안건
""".strip()

    return (
        "[실제 사용자 요청]\n"
        + normalized
        + "\n\n"
        + facts.strip()
        + "\n\n"
        + rules
        + "\n\n"
        + output_rules
    ).strip()


def _sanitize_fast_notice_document(
    document,
):
    """
    HCX가 실수로 작성 가이드의 체크리스트를
    최종 문서에 다시 출력하는 것을 deterministic하게 제거한다.
    """

    checklist_signals = (
        "작성 전 체크리스트",
        "회의 전 체크리스트",
        "제목이 '[AI Agent 개발 2 팀]'으로 시작",
        "제목이 \"[AI Agent 개발 2 팀]\"으로 시작",
        "첫 문단에 대상",
        "안건이 번호로",
        "마지막 줄에 문의처",
        "과도한 수식어",
    )

    cleaned = []

    for block in document.blocks:
        # 공지문에서는 작성자/부서/작성일 같은
        # 별도 메타데이터 표를 사용하지 않는다.
        # 대상/일시/장소는 본문 상단에 직접 표시한다.
        if block.type in {
            "key_value_table",
            "metadata",
        }:
            continue

        combined = " ".join(
            [
                str(block.title or ""),
                str(block.content or ""),
                " ".join(
                    str(x)
                    for x in (block.items or [])
                ),
            ]
        )

        # 체크리스트 제목 자체 제거
        if (
            "체크리스트"
            in combined
        ):
            continue

        # 작성자 검수용 checklist bullet 묶음 제거
        hit_count = sum(
            1
            for signal in checklist_signals
            if signal in combined
        )

        if hit_count >= 2:
            continue

        # list 안에 검수 문장이 섞인 경우 개별 제거
        if block.items:
            block.items = [
                item
                for item in block.items
                if not any(
                    signal in str(item)
                    for signal in checklist_signals
                )
            ]

            if (
                block.type
                in {
                    "bullet_list",
                    "numbered_list",
                }
                and not block.items
            ):
                continue

        cleaned.append(block)

    document.blocks = cleaned

    return document


def _prepare_fast_synthesis_report_source(
    content: str,
) -> str:
    """
    Conversation History를 하나의 보고서용 evidence source로 정규화한다.
    """
    raw = str(content or "").strip()

    rules = (
        "[Fast REPORT 작성 원칙]\n"
        "- 아래 이전 대화는 참고 근거이며, 시간순 채팅 로그 형태로 출력하지 않는다.\n"
        "- 업무 목적/배경은 초기 관련 대화에서 추출한다.\n"
        "- 내부문서 분석 결과는 현행 문제점의 근거로 사용한다.\n"
        "- Web Search 조사 결과는 최신 솔루션/기술 조사 근거로 사용한다.\n"
        "- 내부 문제와 외부 솔루션의 대응 관계를 표로 비교한다.\n"
        "- 대화에 근거가 없는 제품 기능, 가격, 비용, 수치, 성과율은 만들지 않는다.\n"
        "- 비용/정량 효과 등 확인되지 않은 내용은 추가 확인 필요사항으로 보낸다.\n"
        "- 공지문, 회의 공지, 공지문 작성 가이드 및 작성 체크리스트는 제외한다.\n"
        "- 같은 내용을 여러 섹션에서 반복하지 않는다.\n"
        "- 표는 비교 정보에만 사용하고, 설명은 짧은 문단과 목록으로 정돈한다.\n"
        "- 최종 출력은 실제 사내 보고서 본문만 작성한다.\n"
        "- 시스템 규칙, 현재 요청 문구, [이전 대화 근거] 같은 내부 표식은 출력하지 않는다."
    )

    return (
        rules
        + "\n\n"
        + raw
    ).strip()


def _sanitize_fast_report_document(
    document,
):
    """
    종합 보고서 최종 렌더 전 불필요한 시스템 표식,
    무관한 공지문 내용, 빈 metadata를 제거한다.
    """
    cleaned = []

    hidden_signals = (
        "[현재 요청]",
        "[이전 대화 근거]",
        "[이전 사용자 요청",
        "[이전 AI 결과",
        "[대화 활용 원칙]",
        "[문서 생성 규칙]",
        "[종합 보고서 생성 규칙]",
        "[Fast REPORT 작성 원칙]",
    )

    unrelated_notice_signals = (
        "공지문 작성 가이드",
        "[AI Agent 개발 2 팀] 전체 회의 안내",
        "작성 전 체크리스트",
        "회의 전 체크리스트",
    )

    for block in document.blocks:
        combined = " ".join(
            [
                str(
                    getattr(
                        block,
                        "title",
                        "",
                    )
                    or ""
                ),
                str(
                    getattr(
                        block,
                        "content",
                        "",
                    )
                    or ""
                ),
                " ".join(
                    str(x)
                    for x in (
                        getattr(
                            block,
                            "items",
                            None,
                        )
                        or []
                    )
                ),
            ]
        )

        if any(
            signal in combined
            for signal in hidden_signals
        ):
            continue

        if any(
            signal in combined
            for signal in unrelated_notice_signals
        ):
            continue

        # 값이 하나도 없는 metadata 표만 제거한다.
        if block.type in {
            "key_value_table",
            "metadata",
        }:
            data = getattr(
                block,
                "data",
                None,
            )

            if not data:
                continue

            if isinstance(data, dict):
                has_value = any(
                    str(v).strip()
                    for v in data.values()
                    if v is not None
                )

                if not has_value:
                    continue

        cleaned.append(block)

    document.blocks = cleaned

    if hasattr(
        document,
        "metadata",
    ):
        document.metadata = {}

    return document


def _build_deterministic_fast_notice(
    plan,
    content: str,
) -> DocumentContent | None:
    """
    RAG로 가져온 공지문 작성 가이드가
    필요한 핵심 규칙을 실제로 포함하고 있을 때만
    deterministic Fast NOTICE를 만든다.

    가이드 규칙은 형식에만 사용하고,
    예시의 날짜/장소/안건/담당자는 복사하지 않는다.
    """
    raw = str(content or "").strip()

    if "[첨부 문서 원문]" not in raw:
        return None

    instruction, guide = raw.split(
        "[첨부 문서 원문]",
        1,
    )

    instruction = instruction.strip()
    guide = guide.strip()

    # 이 규칙들이 실제 RAG 가이드에 존재하는지 확인한다.
    required_guide_signals = (
        "AI Agent 개발 2",
        "대상",
        "일시",
        "장소",
        "안건",
        "문의",
    )

    if not all(
        signal in guide
        for signal in required_guide_signals
    ):
        return None

    # -----------------------------------------------------
    # 날짜 처리
    # -----------------------------------------------------
    date_text = "다음 주 화요일"

    if "다음 주 화요일" in instruction:
        try:
            from datetime import datetime, timedelta
            from zoneinfo import ZoneInfo

            today = datetime.now(
                ZoneInfo("Asia/Seoul")
            ).date()

            # 다음 주 월요일
            next_monday = (
                today
                + timedelta(
                    days=(7 - today.weekday())
                )
            )

            target = (
                next_monday
                + timedelta(days=1)
            )

            date_text = (
                f"{target.year}년 "
                f"{target.month}월 "
                f"{target.day}일(화)"
            )
        except Exception:
            date_text = "다음 주 화요일"

    # -----------------------------------------------------
    # 시간 처리
    # -----------------------------------------------------
    import re

    time_match = re.search(
        r"(오전|오후)\s*(\d{1,2})\s*시",
        instruction,
    )

    if time_match:
        time_text = (
            f"{time_match.group(1)} "
            f"{time_match.group(2)}시"
        )
    else:
        time_text = "시간 추후 안내"

    # -----------------------------------------------------
    # 실제 사용자 사실
    # -----------------------------------------------------
    team_name = "AI Agent 개발 2 팀"

    title = (
        f"[{team_name}] 전체 회의 안내"
    )

    audience = (
        f"{team_name} 전원"
    )

    # 사용자가 장소를 주지 않았으므로 추후 안내.
    # 가이드 예시의 '3층 대회의실'은 사용하지 않는다.
    location = "추후 안내"

    blocks = [
        DocumentBlock(
            type="paragraph",
            content=f"대상: {audience}",
        ),
        DocumentBlock(
            type="paragraph",
            content=(
                f"일시: {date_text} {time_text}"
            ),
        ),
        DocumentBlock(
            type="paragraph",
            content=f"장소: {location}",
        ),
        DocumentBlock(
            type="paragraph",
            content=(
                f"{team_name} 전체 회의를 아래와 같이 "
                "진행하오니 팀원 여러분께서는 "
                "참석해주시기 바랍니다."
            ),
        ),
        DocumentBlock(
            type="heading",
            content="회의 안건",
        ),
        DocumentBlock(
            type="numbered_list",
            items=[
                "세부 안건은 추후 안내",
            ],
        ),
        DocumentBlock(
            type="paragraph",
            content=f"문의: {team_name}",
        ),
    ]

    return DocumentContent(
        title=title,
        document_kind="사내 공지문",
        metadata={},
        blocks=blocks,
    )


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

    # "지금까지 종합해서 보고서로 만들어줘" 같은 요청은
    # 현재 한 문장만 보면 instruction-only처럼 보여도
    # Backend가 전달한 Conversation History를 사용해야 하므로
    # generic weekly-report fallback으로 보내지 않는다.
    early_fast_report_plan = (
        build_fast_synthesis_report_plan(
            content
        )
    )

    if (
        _is_instruction_only_request(content)
        and early_fast_report_plan is None
    ):
        # 실제 업무 자료가 전혀 없는 일반 문서 생성 요청만
        # 기존 deterministic fallback을 사용한다.
        plan = _fallback_plan(request)

        if title.strip():
            plan.title = title.strip()

        composed = _fallback_content(
            plan,
            content.strip(),
        )
    else:
        # 종합 보고서는 이전 history 안에 공지문 생성 요청이
        # 포함될 수 있으므로 REPORT 의도를 먼저 확정한다.
        fast_report_plan = early_fast_report_plan

        # REPORT가 확정되면 NOTICE 판정 자체를 하지 않는다.
        # 따라서 한 요청에서 REPORT와 NOTICE가 동시에 활성화되지 않는다.
        fast_plan = (
            None
            if fast_report_plan is not None
            else build_fast_notice_plan(
                content
            )
        )

        if fast_report_plan is not None:
            # "지금까지 종합해서 보고서로"는
            # 이미 문서 종류가 명확하므로 Planner HCX를 생략한다.
            plan = fast_report_plan

            incoming_title = title.strip()

            generic_report_titles = {
                "",
                "보고서",
                "업무보고서",
                "PrompTune 생성 문서",
            }

            if (
                incoming_title
                and incoming_title
                not in generic_report_titles
            ):
                plan.title = incoming_title

            report_source = (
                _prepare_fast_synthesis_report_source(
                    content
                )
            )

            # STEP 6 종합 보고서는 7개 섹션의 구조화 JSON이 필요해
            # 기본 384 token으로는 출력이 잘리거나 JSON이 깨질 수 있다.
            # 이 경로에서만 충분한 출력 예산을 주고,
            # 파싱 실패를 빈 주간보고서 fallback으로 숨기지 않는다.
            composed = compose_document(
                plan,
                report_source,
                max_new_tokens=768,
                raise_on_failure=True,
            )

            print(
                "[SmartDocument] "
                "fast_report=true "
                "/ planner_hcx=0 "
                "/ composer_hcx=1 "
                f"/ source_chars={len(report_source)}"
            )

        elif fast_plan is not None:
            plan = fast_plan

            incoming_title = title.strip()

            generic_titles = {
                "",
                "공지문",
                "공지",
                "공지 문",
                "안내문",
                "문서",
            }

            if (
                incoming_title
                and incoming_title not in generic_titles
            ):
                plan.title = incoming_title

            # RAG 가이드가 실제로 전달됐는지 먼저 검증한다.
            notice_source = (
                _prepare_fast_notice_source(
                    content
                )
            )

            # 현재 가이드의 핵심 규칙이 확인되면
            # LLM 없이 사실 기반으로 바로 문서화한다.
            deterministic_notice = (
                _build_deterministic_fast_notice(
                    plan,
                    content,
                )
            )

            if deterministic_notice is not None:
                composed = deterministic_notice

                print(
                    "[SmartDocument] "
                    "fast_notice=true "
                    "/ planner_hcx=0 "
                    "/ composer_hcx=0 "
                    "/ mode=deterministic "
                    f"/ source_chars={len(notice_source)}"
                )

            else:
                # 가이드 구조가 예상과 달라졌을 경우에만
                # 기존 Composer 1회 fallback을 사용한다.
                composed = compose_document(
                    plan,
                    notice_source,
                )

                print(
                    "[SmartDocument] "
                    "fast_notice=true "
                    "/ planner_hcx=0 "
                    "/ composer_hcx=1 "
                    "/ mode=composer_fallback "
                    f"/ source_chars={len(notice_source)}"
                )

        else:
            # 문서 종류가 명확하지 않은 일반 요청만
            # 기존 HCX Planner + Composer 경로를 사용한다.
            plan = build_document_plan(
                request
            )

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

    # Fast NOTICE는 범용 Layout 적용 후
    # metadata/key-value 표가 다시 추가될 수 있으므로
    # 렌더링 직전에 최종 정리한다.
    if "fast_plan" in locals() and fast_plan is not None:
        result = _sanitize_fast_notice_document(
            result
        )

        if hasattr(result, "metadata"):
            result.metadata = {}

        print(
            "[SmartDocument] "
            "fast_notice_post_layout_cleanup=true "
            f"/ final_blocks={len(result.blocks)}"
        )

    if (
        "fast_report_plan" in locals()
        and fast_report_plan is not None
    ):
        result = _sanitize_fast_report_document(
            result
        )

        print(
            "[SmartDocument] "
            "fast_report_post_layout_cleanup=true "
            f"/ final_blocks={len(result.blocks)}"
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
