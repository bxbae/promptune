import unittest

from app.services.retrieval.search_plan import (
    build_search_plan,
    is_market_value_query,
)


CASES = [
    ("침착맨이 누구야?", "PROFILE", "침착맨", "NONE"),
    ("OpenAI가 뭐 하는 회사야?", "PROFILE", "OpenAI", "NONE"),
    ("BTS가 국가에 기여한 점 알려줘", "RESEARCH", "BTS", "NONE"),
    ("BTS 최근 뉴스 알려줘", "NEWS", "BTS", "WEEK"),
    ("현재 커피 시세 알려줘", "FINANCE", "커피", "DAY"),
    ("오늘 원달러 환율 알려줘", "FINANCE", "원달러", "DAY"),
    ("오늘 서울 날씨 알려줘", "CURRENT_FACT", "서울", "DAY"),
    ("어제 LG 트윈스 경기 결과 알려줘", "CURRENT_FACT", "LG 트윈스", "NONE"),
    ("양자컴퓨팅 원리를 설명해줘", "GENERAL", None, "NONE"),
    (
        "이강인 선수에대해 알려줘. 이강인 선수는 뛰어난 드리블 능력과 패스 "
        "능력으로 주목받고 있는 젊은 축구 선수입니다. 소속 클럽과 약력을 "
        "안내해줘.",
        "PROFILE",
        None,
        "NONE",
    ),
    # 2026-09-02(1-B): 트리거 명사 바로 뒤에 조사가 붙어(공백 없이) entity
    # 추출이 깨지던 케이스들. "강남구"/"서울"을 특별 취급하는 게 아니라
    # 일반적인 한국어 조사(은/는/이/가/을/를/도) + 문장부호 경계를
    # 추가로 인식하게 한 결과다.
    ("오늘 강남구 날씨는 어때?", "CURRENT_FACT", "강남구", "DAY"),
    ("오늘 서울 강남구 날씨는 어때?", "CURRENT_FACT", "서울 강남구", "DAY"),
    ("삼성전자 주가는?", "FINANCE", "삼성전자", "NONE"),
    ("원달러 환율은?", "FINANCE", "원달러", "NONE"),
    ("아이폰 가격이 얼마야?", "FINANCE", "아이폰", "NONE"),
    # "최근"이 트리거 단어 바로 앞 subject 절에 들어가 있으면 그대로
    # entity에 포함된다 - 이건 이번 조사-경계 수정과 무관한 기존
    # _SUBJECT_PATTERNS 캡처 방식의 특성이라 그대로 관찰/고정만 한다
    # (수정 범위 밖 - routing/architecture 변경 금지).
    ("손흥민 최근 경기 결과는?", "CURRENT_FACT", "손흥민 최근", "WEEK"),
]


class SearchPlanTest(unittest.TestCase):

    def test_cases(self):
        for query, intent, entity, freshness in CASES:
            with self.subTest(query=query):
                plan = build_search_plan(query)

                self.assertEqual(plan.intent, intent)
                self.assertEqual(plan.entity, entity)
                self.assertEqual(plan.freshness, freshness)


class IsMarketValueQueryTest(unittest.TestCase):
    """
    2026-09-02(FINANCE 라우팅 후속): "주가"/"환율"/"시세" 등은 시간 표현
    없이도 그 자체로 실시간성이 강한 시장 정보라 ml_router.
    resolve_strong_retrieval_route()가 이 함수를 재사용한다. "가격"은
    일반 명사로도 흔히 쓰여서(책 가격 등) 여기 포함하지 않는다.
    """

    def test_market_value_markers_are_detected(self):
        for query in (
            "삼성전자 주가는 어때?",
            "삼성전자 주가는?",
            "원달러 환율은?",
            "원달러 환율 알려줘",
            "비트코인 시세는?",
            "코스피 지금 얼마야",
        ):
            with self.subTest(query=query):
                self.assertTrue(is_market_value_query(query))

    def test_price_alone_is_not_a_market_value_marker(self):
        # "가격"은 일반 명사로도 흔히 쓰여서(책 가격, 서비스 가격 등)
        # 이 함수의 대상이 아니다 - "아이폰 가격은?"류는 별도로
        # query_intent.is_external_price_lookup_query()가 처리한다.
        for query in (
            "아이폰 가격이 얼마야?",
            "책 가격 알려줘",
            "우리 회사 가격 정책 문서 보여줘",
        ):
            with self.subTest(query=query):
                self.assertFalse(is_market_value_query(query))

    def test_concept_or_how_to_questions_are_not_value_lookups(self):
        for query in (
            "주가란 뭐야?",
            "환율 계산 방법 알려줘",
            "코스피와 코스닥 차이는?",
            "시세라는 말의 뜻이 뭐야?",
        ):
            with self.subTest(query=query):
                self.assertFalse(is_market_value_query(query))


if __name__ == "__main__":
    unittest.main()
