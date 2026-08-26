from __future__ import annotations

import re


"""
2026-08-26: "이강인 축구선수에대해 알려줘 지금 소속팀과 프로필 부탁해. 요약해줘.
나에게. 최근 이슈와 관련해. 3문단으로. 친근하게. 숫자는 꼭 포함해서" 같은 질의를
그대로 Tavily 검색어로 보내면, 실제 검색에 필요 없는 어조/분량/대상/제약 지시문
(AUDIENCE/TONE/LENGTH/FORMAT/CONSTRAINT/EXAMPLE - 7번 추천문구 기능의
pipeline_mock._TEMPLATES와 동일한 8요소 어휘)까지 검색어에 섞여 들어가서,
Tavily가 엉뚱한 결과(예: 무관한 하키/축구 프리뷰 기사, 정치 기사)를 상위로
올리는 사례가 확인됨 - "침착맨이라는 유튜버를 간략하게 요약해줘. 나에게. 최근
이슈와 관련해. 3문단으로. 친근하게. 전문용어는 빼고" 검색 결과가 침착맨과 전혀
무관한 정치 기사 1건뿐이었던 것도 같은 원인으로 보임.

이 8요소 지시문은 최종 답변 생성(generate_hcx.py)에는 반드시 필요하지만(존댓말
수위, 분량, 어조 등을 실제로 반영해야 함), "검색"에는 오히려 잡음이다 - 그래서
검색어 생성에서만 걸러내고, generate()에 넘기는 finalPrompt 원문은 절대
건드리지 않는다.

PrompTune UI가 요소를 붙일 때 각 요소를 마침표(.)로 구분된 독립 절로 붙이는
패턴이 관찰됨(예시 4개 전부 동일 패턴) - 그래서 절 단위로 쪼갠 뒤, "그 절
전체가 알려진 8요소 상투구인가"만 판정한다. 실제 검색 대상(TASK)은 항상 첫
절에 포함되어 있었고, 이후 절들이 상투구였다 - 하지만 순서에 기대지 않고
모든 절에 대해 상투구 여부만 판단해서, 상투구가 아닌 절은 위치와 무관하게
검색어에 남긴다(과하게 잘라내는 것을 방지).
"""

# pipeline_mock._TEMPLATES(추천문구 7번 기능)의 실제 문구 + 채팅에서 관찰된
# 변형(예: "나에게"는 TEMPLATES에는 없지만 AUDIENCE 자리에 실제로 쓰임).
_STOCK_PHRASES = {
    # AUDIENCE
    "팀장님께", "담당자에게", "고객님께", "나에게", "저에게", "저희에게",
    "우리 팀에게", "동료에게",
    # TONE
    "정중한 어조로", "친근하게", "전문적으로", "정중하게", "캐주얼하게",
    "격식있게", "부드럽게",
    # FORMAT (숫자 포함형은 아래 정규식으로 별도 처리)
    "표로 정리해서", "불릿 목록으로", "표로", "목록으로",
    # LENGTH
    "간결하게", "간단하게", "자세하게", "상세하게",
    # CONTEXT
    "지난 회의 관련해서", "이번 분기 상황에서", "최근 이슈와 관련해",
    # CONSTRAINT
    "전문용어는 빼고", "숫자는 꼭 포함해서", "회사명은 언급하지 말고",
    # EXAMPLE
    "지난번 양식처럼", "첨부 샘플 참고해서", "기존 템플릿 기반으로",
    # TASK - 다른 절에 이미 실제 요청이 있고, 이 절이 그냥 중복되는 동사만
    # 담고 있을 때만 걸러진다(절 전체가 이 동사뿐이어야 함 - 아래 로직 참고).
    "요약해줘", "요약해 줘", "작성해줘", "작성해 줘", "정리해줘", "정리해 줘",
}

# "3문단으로", "5줄로", "300자 이내로", "3~4줄로" 처럼 숫자+단위로 된 FORMAT/
# LENGTH 상투구는 값이 매번 달라서 고정 문자열 집합으로 못 잡으므로 정규식으로.
_NUMERIC_FORMAT_RE = re.compile(
    r"^\d+(?:~\d+)?\s*"
    r"(?:문단|문장|줄|개|가지|자|단어|페이지|포인트|배|위|점)"
    r"\s*(?:이내로|이내|으로|로)?$"
)


def _is_stock_clause(clause: str) -> bool:
    normalized = clause.strip().strip(",").strip()

    if not normalized:
        return True

    if normalized in _STOCK_PHRASES:
        return True

    if _NUMERIC_FORMAT_RE.match(normalized):
        return True

    return False


def build_search_query(query: str) -> str:
    """
    Tavily 등 외부 검색에 보낼 질의에서, 답변 스타일 지시문(8요소 상투구)만
    제거한 버전을 만든다. 생성(generate)에 쓰는 원문은 그대로 두고, 검색에만
    이 함수의 결과를 쓴다.
    """
    original = query.strip()

    if not original:
        return original

    clauses = [c for c in re.split(r"[.](?!\d)", original)]

    kept = [c.strip().strip(",").strip() for c in clauses]
    kept = [c for c in kept if c and not _is_stock_clause(c)]

    cleaned = " ".join(kept).strip()

    # 전부 상투구로 판정돼 텅 비면(예: 질의 자체가 짧은 스타일 지시문 하나뿐인
    # 경우) 원문 그대로 쓴다 - 검색어가 아예 없어지는 것보다는 잡음이 섞이더라도
    # 검색이 되는 편이 낫다.
    return cleaned if cleaned else original
