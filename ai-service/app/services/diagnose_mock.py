"""
5번 통합 진단 (mock) — 승득님 새 라벨링 기준 반영.

★ 새 기준 (2026-08 개정):
  판정은 "문장에 요소가 없냐"가 아니라 "요청 수행에 보완이 필요하냐"로 한다.
  → 요소가 문장에 없어도, 그 작업에 불필요하면 0 (충분).
  예) "번역 좀"에서 Context는 번역 작업에 굳이 필요 없으므로 0일 수 있음.

# TODO(승득): 이 규칙 mock을 학습한 KcELECTRA 멀티라벨 분류로 교체.
#   - 입력/출력 형식(DiagnoseResponse)은 그대로 유지.
#   - 학습 데이터 정답도 새 기준("보완 필요")으로 라벨링돼야 함 (병환: 데이터 담당).
#   - 학습 harness는 ml/ko_vs_kc/ 참고.
"""
from app.schemas.models import DiagnoseRequest, DiagnoseResponse, Typo, ELEMENTS

# 1) 요소가 명시적으로 있는지 (있으면 충분=0)
_PRESENT_HINTS = {
    "TASK": ["요약", "번역", "작성", "정리", "만들", "써", "리뷰", "다듬", "설명", "안내"],
    "AUDIENCE": ["님께", "님한테", "대상", "고객", "임원", "팀장", "학부모", "신입", "개발팀", "투자자", "사용자", "담당자"],
    "CONTEXT": ["관련", "상황", "지난", "이번", "건과", "출시", "장애", "불만", "갱신", "접수"],
    "FORMAT": ["표", "목록", "불릿", "마크다운", "문단", "줄로", "항목", "메일", "문구"],
    "TONE": ["정중", "친근", "따뜻", "캐주얼", "전문적", "존댓말", "간결", "부드럽"],
    "LENGTH": ["자", "줄", "문단", "이내", "내외", "짧게", "핵심만", "개"],
    "CONSTRAINT": ["빼고", "말고", "없이", "꼭", "제외", "포함", "반드시"],
    "EXAMPLE": ["샘플", "예시", "처럼", "템플릿", "기반", "그때", "지난번", "양식"],
}

# 2) 새 기준 핵심: 이 작업엔 없어도 불필요한 요소 (없어도 0)
_OPTIONAL_BY_TASK = {
    "번역": ["CONTEXT", "EXAMPLE"],
    "요약": ["EXAMPLE"],
    "다듬": ["FORMAT", "EXAMPLE", "LENGTH"],
}

_TASK_TYPE_HINTS = {
    "application": ["신청", "휴가", "경비", "구매"],
    "report_internal": ["내규", "규정", "정책 보고"],
    "notice_internal": ["정책 공지", "내부 공지"],
    "report": ["보고서", "주간보고", "실적", "피치"],
    "notice": ["공지", "안내문", "이벤트"],
    "support": ["사과", "고객", "응대", "불만"],
    "email": ["메일", "이메일"],
}
_TYPO_DICT = {"요약해조": "요약해줘", "부착해요": "부탁해요", "해줄레": "해줄래"}


def _detect_task_type(text: str) -> str:
    for ttype, hints in _TASK_TYPE_HINTS.items():
        if any(h in text for h in hints):
            return ttype
    return "email"


def _optional_elements(text: str) -> set:
    opt = set()
    for kw, elements in _OPTIONAL_BY_TASK.items():
        if kw in text:
            opt.update(elements)
    return opt


def diagnose(req: DiagnoseRequest) -> DiagnoseResponse:
    text = req.text
    optional = _optional_elements(text)   # 새 기준: 이 작업엔 불필요한 요소
    missing = {}
    for el in ELEMENTS:
        present = any(hint in text for hint in _PRESENT_HINTS[el])
        if present:
            missing[el] = 0          # 명시됨 → 충분
        elif el in optional:
            missing[el] = 0          # ★ 새 기준: 없지만 이 작업엔 불필요 → 충분
        else:
            missing[el] = 1          # 없고 필요함 → 보완 필요
    typos = [Typo(span=k, suggest=v) for k, v in _TYPO_DICT.items() if k in text]
    task_type = _detect_task_type(text)
    needs_internal = task_type.endswith("_internal") or task_type == "application"
    return DiagnoseResponse(missing=missing, task_type=task_type, typos=typos, needs_internal_docs=needs_internal)
