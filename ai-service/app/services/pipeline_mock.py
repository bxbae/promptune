"""
7,8,13,14,15번 mock 서비스.
각 함수에 # TODO(담당자) 로 실제 구현 교체 지점 표시.
"""
import re
from app.schemas.models import (
    SuggestRequest, SuggestResponse, Suggestion,
    SafetyRequest, SafetyResponse,
    RetrieveRequest, RetrieveResponse, Document,
    GenerateRequest, GenerateResponse,
    ImprovePromptRequest, ImprovePromptResponse,
    ValidateRequest, ValidateResponse,
)

# ---------- 7번: 추천문구 생성 ----------
# TODO(승득): 템플릿 mock → HyperCLOVA X 호출. SuggestResponse 형식 유지.
_TEMPLATES = {
    "AUDIENCE": ("팀장님께", ["담당자에게", "고객님께"]),
    "TONE": ("정중한 어조로", ["친근하게", "전문적으로"]),
    "FORMAT": ("표로 정리해서", ["불릿 목록으로", "3문단으로"]),
    "LENGTH": ("300자 이내로", ["3~4줄로", "간결하게"]),
    "CONTEXT": ("지난 회의 관련해서", ["이번 분기 상황에서", "최근 이슈와 관련해"]),
    "CONSTRAINT": ("전문용어는 빼고", ["숫자는 꼭 포함해서", "회사명은 언급하지 말고"]),
    "EXAMPLE": ("지난번 양식처럼", ["첨부 샘플 참고해서", "기존 템플릿 기반으로"]),
    "TASK": ("요약해줘", ["작성해줘", "정리해줘"]),
}


def suggest(req: SuggestRequest) -> SuggestResponse:
    out = []
    for el in req.target_elements:
        primary, alts = _TEMPLATES.get(el, ("(추천 없음)", []))
        out.append(Suggestion(element=el, primary=primary, alternatives=alts))
    return SuggestResponse(suggestions=out)


# ---------- 8번: 추천문구 안전검사 (실제 규칙, mock 아님) ----------
# 이 단계는 규칙이라 목업도 실제로 동작한다. 교체 불필요.
_NUM_RE = re.compile(r"\d+")


def safety_check(req: SafetyRequest) -> SafetyResponse:
    # 원문의 숫자가 추천에서 바뀌거나 사라졌는지 확인
    orig_nums = set(_NUM_RE.findall(req.original))
    sugg_nums = set(_NUM_RE.findall(req.suggestion))
    # 추천이 원문에 없던 숫자를 만들어내면 위험
    invented = sugg_nums - orig_nums
    if invented:
        return SafetyResponse(safe=False, reason=f"원문에 없는 숫자 생성: {invented}")
    return SafetyResponse(safe=True, reason="")


# ---------- 13번: 내부문서 검색 (RAG) ----------
# TODO(승연): 샘플 mock → BGE-M3 임베딩 + pgvector 검색. RetrieveResponse 형식 유지.
_SAMPLE_DOCS = [
    Document(title="휴가 규정 안내", content="연차는 입사 1년 후 15일 부여되며...", score=0.91),
    Document(title="경비 처리 지침", content="경비 신청은 지출 후 7일 이내...", score=0.85),
    Document(title="보고서 작성 표준", content="사내 보고서는 요약-본문-결론 순으로...", score=0.78),
]


def retrieve(req: RetrieveRequest) -> RetrieveResponse:
    return RetrieveResponse(documents=_SAMPLE_DOCS[: req.top_k])


# ---------- 14번: 최종 답변 생성 ----------
# TODO(승득): 템플릿 mock → HyperCLOVA X.
def generate(
    req: GenerateRequest,
    web_results=None,
    used_web_search: bool = False,
) -> GenerateResponse:
    web_results = web_results or []

    doc_note = ""
    if req.documents:
        titles = ", ".join(d.title for d in req.documents)
        doc_note = f"\n\n[참고 문서: {titles}]"

    web_note = ""
    if web_results:
        lines = []

        for item in web_results:
            title = item.get("title", "")
            url = item.get("url", "")
            content = item.get("content", "")[:300]

            lines.append(
                f"- {title}\n"
                f"  URL: {url}\n"
                f"  내용: {content}"
            )

        web_note = "\n\n[웹 검색 결과]\n" + "\n".join(lines)

    result = (
        f"[{req.task_type} 결과 (mock)]\n"
        f"요청: {req.prompt}\n"
        f"→ 실제 HyperCLOVA X 연결 시 아래 검색 정보를 바탕으로 최종 답변을 생성합니다."
        f"{doc_note}"
        f"{web_note}"
    )

    return GenerateResponse(
        result=result,
        used_web_search=used_web_search,
    )

# ---------- Phase 2-C: 개선 프롬프트 생성 mock ----------
_IMPROVE_PLACEHOLDERS = {
    "TASK": "[해야 할 작업]",
    "AUDIENCE": "[대상/수신자]",
    "CONTEXT": "[배경/상황 정보]",
    "FORMAT": "[원하는 출력 형식]",
    "TONE": "[원하는 어조]",
    "LENGTH": "[원하는 길이]",
    "CONSTRAINT": "[제약 조건]",
    "EXAMPLE": "[참고 예시]",
}

def improve_prompt(req: ImprovePromptRequest) -> ImprovePromptResponse:
    """HCX 없이 API 연동을 확인하기 위한 deterministic mock."""

    parts: list[str] = []

    if req.prompt_rule.use_role and req.prompt_rule.role_hint:
        parts.append(f"역할: {req.prompt_rule.role_hint}")

    parts.append(req.text.strip())

    placeholders = [
        _IMPROVE_PLACEHOLDERS[element]
        for element in req.prompt_rule.missing_elements
        if element in _IMPROVE_PLACEHOLDERS
    ]

    if placeholders:
        parts.append(
            "추가로 필요한 정보: " + ", ".join(placeholders)
        )

    return ImprovePromptResponse(
        improved_prompt="\n".join(parts),
        used_fallback=False,
    )

# ---------- 15번: 최종 검증 ----------
# TODO(승득): 규칙 mock → KcELECTRA NLI(모순검출) + HyperCLOVA 자기검증 추가.
def validate(req: ValidateRequest) -> ValidateResponse:
    issues = []
    # 규칙: 원문 숫자가 결과에 보존됐는지 (이 부분은 실제 동작)
    orig_nums = set(_NUM_RE.findall(req.original))
    gen_nums = set(_NUM_RE.findall(req.generated))
    facts_preserved = orig_nums.issubset(gen_nums) if orig_nums else True
    if not facts_preserved:
        issues.append(f"원문 숫자 누락: {orig_nums - gen_nums}")

    # mock: 톤·모순은 실제론 KcELECTRA NLI가 판정. 지금은 통과로 가정.
    tone_ok = True
    no_contradiction = True

    passed = facts_preserved and tone_ok and no_contradiction
    return ValidateResponse(
        passed=passed, tone_ok=tone_ok,
        no_contradiction=no_contradiction,
        facts_preserved=facts_preserved, issues=issues,
    )
