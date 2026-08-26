import unittest

from app.services.retrieval.ml_router import classify_ml_retrieval_route


class ClassifyMlRetrievalRouteTest(unittest.TestCase):
    """
    2026-08-26: "어제 잠실 경기장의 날씨를 안내해주고 lg 트윈스의 승리여부를
    안내해줘." 가 no_retrieval로 잘못 분류돼(routing_train_242.json에
    스포츠 경기 결과 카테고리가 아예 없었음) 웹검색 없이 모델이 완전히
    지어낸 답을 내놓는 문제가 있었음. 학습 데이터 보강 + _is_likely_realtime_fact
    사전 필터로 고친 뒤, 회귀 방지용으로 이 케이스들을 고정한다.
    """

    def test_sports_result_query_routes_to_realtime_search(self):
        route = classify_ml_retrieval_route(
            "어제 잠실 경기장의 날씨를 안내해주고  lg 트윈스의 승리여부를 안내해줘."
        )
        self.assertIn(route, {"external_or_realtime", "web_search"})

    def test_sports_result_query_with_tone_suffix_still_routes_to_search(self):
        # 확장 프로그램이 사용자 질문 뒤에 톤/포맷 지시문을 붙여도(예:
        # "3문단으로", "친근하게") 라우팅이 no_retrieval로 뒤집히면 안 됨.
        query = (
            "어제 잠실 경기장의 날씨를 안내해주고  lg 트윈스의 승리여부를 안내해줘.\n"
            "추가로 필요한 정보: 고객님께, 최근 이슈와 관련해, 3문단으로, "
            "친근하게, 간결하게, 전문용어는 빼고, 기존 템플릿 기반으로"
        )
        route = classify_ml_retrieval_route(query)
        self.assertIn(route, {"external_or_realtime", "web_search"})

    def test_weather_and_stock_queries_still_route_to_realtime_search(self):
        for query in (
            "오늘 서울 날씨 알려줘",
            "지금 삼성전자 주가 얼마야",
            "오늘 원달러 환율 알려줘",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    classify_ml_retrieval_route(query), "external_or_realtime"
                )

    def test_internal_and_conversational_queries_are_unaffected(self):
        self.assertEqual(
            classify_ml_retrieval_route("회사 연차 규정 알려줘"), "internal_rag"
        )
        self.assertEqual(
            classify_ml_retrieval_route("겹치는 문장을 제거해서 자연스럽게 만들어줘"),
            "no_retrieval",
        )


if __name__ == "__main__":
    unittest.main()
