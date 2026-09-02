import unittest

from app.services.retrieval.ml_router import (
    classify_ml_retrieval_route,
    resolve_strong_retrieval_route,
    is_market_value_query,
)


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

    def test_stock_queries_route_to_realtime_search(self):
        # 2026-08-26: 이 카테고리는 원래 학습 데이터에도 있어서 이전부터
        # 잘 되고 있었음 - 회귀 방지용으로 고정.
        for query in ("지금 삼성전자 주가 알려줘", "삼성전자 주가 알려줘"):
            with self.subTest(query=query):
                self.assertEqual(
                    classify_ml_retrieval_route(query), "external_or_realtime"
                )

    def test_third_party_profile_query_routes_to_realtime_search(self):
        # 2026-08-26: "이강인 소속과 프로필을 알려줘"가 user_context로 잘못
        # 분류돼(학습 데이터의 "프로필"/"소속" 예시가 전부 "내 프로필"류라서
        # char n-gram이 "이강인 프로필"까지 같은 카테고리로 끌고 감) 웹검색을
        # 아예 안 하고, HCX가 근거 없이 완전히 지어낸 답(PSG 소속, 1996년생
        # 등 - 실제로는 아틀레티코 마드리드, 2001년생)을 내놓은 사례가
        # 재현 확인됨. 출처 링크도 당연히 안 붙었음.
        for query in (
            "이강인 소속과 프로필을 알려줘",
            "이강인 선수의 프로필을 안내해줘",
            "침착맨 프로필 알려줘",
            (
                "현제 이강인 소속과 프로필을 알려줘. 나에게. 요약해줘. "
                "최근 골 소식과 관련해서. 3문단으로. 전문적으로. "
                "숫자는 꼭 포함해서"
            ),
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    classify_ml_retrieval_route(query), "external_or_realtime"
                )

    def test_self_profile_query_still_routes_to_user_context(self):
        # 위 수정이 진짜 "내 프로필/소속" 질의까지 웹검색으로 돌려버리는
        # 회귀를 만들지 않았는지 확인 - 학습 데이터의 39개 user_context
        # 예시를 대표하는 케이스들을 고정한다.
        for query in (
            "내 소속 알려줘",
            "내 프로필의 부서 알려줘",
            "내 계정의 소속 알려줘",
            "현재 내 계정의 회사와 부서 알려줘",
            "내 회사 프로필에서 소속 팀 확인해줘",
            "제 프로필 좀 알려줘",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    classify_ml_retrieval_route(query), "user_context"
                )

    def test_external_subject_summary_query_routes_to_realtime_search(self):
        # 2026-08-26: "침착맨에대해. 요약해줘. 최근 이슈와 관련해..."가
        # no_retrieval로 잘못 분류돼(patch 19의 위키 폴백은 search_web()이
        # 아예 호출 안 되니 무용지물이었음) 웹검색 없이 HCX가 완전히 지어낸
        # 인물 정보(가짜 데뷔 연도, 없는 앨범 등)로 답한 사례가 docker logs의
        # [Retrieval] route='no_retrieval' 로그로 재현 확인됨. 원인은
        # routing_train_242.json의 no_retrieval 학습 예시(43개)가 전부 "이
        # 문장을/이 내용을 + 요약해줘"류(프롬프트에 이미 주어진 텍스트를
        # 다듬는 요청)뿐이고, "OO에 대해 요약해줘"처럼 "~에 대해" 구문으로
        # 특정 대상을 지칭하는 예시가 학습 데이터 267개 전체에 하나도 없어서
        # (직접 검증함) char n-gram 모델이 "~을 요약해줘"라는 표면적 겹침만
        # 보고 이 구문을 no_retrieval로 잘못 분류한 것으로 보임.
        for query in (
            "침착맨에대해. 요약해줘. 최근 이슈와 관련해. 9문단으로."
            "전문적으로. 숫자는 꼭 포함해서. 나에게",
            "BTS에 대해 알려줘. 최근 이슈와 관련해",
            "이순신 장군에 대해 설명해줘",
            "리센느에 대하여 소개해줘",
        ):
            with self.subTest(query=query):
                # ML이 no_retrieval/user_context로 잘못 예측한 경우는 결정적
                # 규칙이 external_or_realtime으로 보정하고, ML이 애초에
                # web_search로 (올바르게) 예측한 경우는 그대로 둔다 - 두 라벨
                # 모두 retrieval_orchestrator.py에서 동일하게 search_web()을
                # 호출하므로(route in {"web_search", "external_or_realtime"})
                # 실제 동작에는 차이가 없다.
                self.assertIn(
                    classify_ml_retrieval_route(query),
                    {"external_or_realtime", "web_search"},
                )

    def test_given_text_summary_requests_still_route_to_no_retrieval(self):
        # 회귀 방지: "이 문장을/이 내용을 요약해줘"류(실제 no_retrieval
        # 학습 예시, "~에 대해" 구문이 없음)는 여전히 no_retrieval을 유지해야
        # 한다 - 이미 프롬프트에 주어진 텍스트를 다듬는 요청이라 검색이
        # 필요 없기 때문.
        for query in (
            "이 문장을 요약해줘",
            "이 내용을 다듬어줘",
            "아래 글을 번역해줘",
            "겹치는 문장을 제거해서 자연스럽게 만들어줘",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    classify_ml_retrieval_route(query), "no_retrieval"
                )

    def test_self_referential_about_query_still_routes_to_user_context(self):
        # "내 프로필에 대해 알려줘"처럼 1인칭 자기참조 질의까지 외부 검색으로
        # 돌리면 안 된다 - _is_third_party_profile_query와 동일한 원칙.
        self.assertEqual(
            classify_ml_retrieval_route("내 프로필에 대해 알려줘"),
            "user_context",
        )

    def test_internal_topic_about_query_still_routes_to_internal_rag(self):
        # "우리 회사 정책에 대해 알려줘"처럼 내부 문서를 찾아야 하는 질의까지
        # 외부 검색으로 돌리면 안 된다.
        self.assertEqual(
            classify_ml_retrieval_route("우리 회사 정책에 대해 알려줘"),
            "internal_rag",
        )

    def test_real_estate_query_does_not_fall_back_to_internal_rag(self):
        # 2026-08-26: "요즘 뜨는 부동산 정책 알려줘"가 internal_rag로
        # 잘못 분류돼(학습 데이터에 부동산 카테고리가 아예 없었음) 사내
        # 문서에서만 찾다가 아무것도 못 찾고 끝나는 문제가 있었음 - 스포츠
        # 경기결과와 동일한 부류의 버그.
        for query in (
            "요즘 뜨는 부동산 정책 알려줘",
            "오늘 강남 아파트 시세 알려줘",
            "최근 집값 동향 알려줘",
            "현재 전세 시세 얼마야",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    classify_ml_retrieval_route(query), "external_or_realtime"
                )


class ResolveStrongRetrievalRouteTest(unittest.TestCase):
    """
    2026-08-31: PR #207(action-aware retrieval 리팩터) 이후, 실제 운영 라우팅
    경로(retrieval_orchestrator.execute_retrieval)는 classify_ml_retrieval_route가
    아니라 resolve_action(ActionClassifier) + resolve_strong_retrieval_route만
    거친다. 그런데 "OO에 대해 알려줘/소개해줘/설명해줘" 패턴을 결정적으로
    external_or_realtime으로 보내던 _is_external_subject_summary_query 규칙이
    resolve_strong_retrieval_route로 옮겨지지 않아서, ActionClassifier가 낮은
    confidence를 내는 질의(예: "고마워!"처럼 학습 데이터에 거의 없는 문구가 앞에
    붙은 경우)에서 검색이 아예 스킵되는 회귀가 발생했다. 도커 로그로 재현 확인:
    [Action] action='WEB_FACT' confidence=0.239 sources=() reason=
    'low_confidence_needs_strong_signal' routing_query='고마워! 리센느 걸그룹에
    대해 알려줘.' / [Retrieval] route='no_retrieval' - 결과적으로 HCX가 리센느
    멤버 구성과 존재하지 않는 NFT 사업 모델을 지어내는 답을 내놓았고, sources가
    비어 있어 "출처 더보기"도 뜨지 않았다.
    """

    def test_greeting_prefixed_about_query_routes_to_realtime_search(self):
        # 실제 운영에서 재현된 질의 그대로 - ActionClassifier의 confidence와
        # 무관하게 결정적으로 external_or_realtime이 나와야 한다.
        self.assertEqual(
            resolve_strong_retrieval_route(
                "고마워! 리센느 걸그룹에 대해 알려줘."
            ),
            "external_or_realtime",
        )

    def test_external_subject_summary_query_is_a_strong_route_directly(self):
        for query in (
            "BTS에 대해 알려줘. 최근 이슈와 관련해",
            "이순신 장군에 대해 설명해줘",
            "리센느에 대하여 소개해줘",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    resolve_strong_retrieval_route(query),
                    "external_or_realtime",
                )

    def test_self_referential_about_query_is_not_a_strong_route(self):
        # "내 프로필에 대해 알려줘"까지 결정적으로 external_or_realtime으로
        # 보내면 안 된다 - 이건 여전히 user_context/ML 판단에 맡긴다.
        self.assertIsNone(
            resolve_strong_retrieval_route("내 프로필에 대해 알려줘")
        )

    def test_internal_topic_about_query_is_not_a_strong_external_route(self):
        self.assertEqual(
            resolve_strong_retrieval_route("우리 회사 정책에 대해 알려줘"),
            "internal_rag",
        )


class ExternalEntityAttributeLookupTest(unittest.TestCase):
    """
    1-A: "OO는 누구야"류는 검색되는데, "OO 나이/생일/키/주소/소속사 알려줘"
    처럼 구체적 속성을 묻는 질문은 기존 WHO/WHAT/KIND/PROFILE 패턴 중 어디에도
    안 걸려서 검색 자체가 누락되고 HCX가 근거 없이 답을 지어내던 문제.
    query_intent._ATTRIBUTE_LOOKUP_RE로 최소 범위(나이/생일/키/주소/소속사)만
    보강한다. "이력서/프로필/경력/약력/학력/소속"은 이미 _PROFILE_LOOKUP_RE가
    다루므로 여기서 다시 검증하지 않는다.
    """

    def test_external_entity_attribute_questions_route_to_realtime_search(self):
        for query in (
            "손흥민 나이 알려줘",
            "아이유 생일이 언제야",
            "삼성전자 주소 알려줘",
            "이재용 키가 몇이야",
            "BTS 소속사 어디야",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    resolve_strong_retrieval_route(query),
                    "external_or_realtime",
                )

    def test_self_referential_attribute_questions_are_not_forced_external(self):
        # 속성 단어만 보고 무조건 web으로 보내면 안 된다 - 자기참조 표현은
        # 기존처럼 user_context/ML 판단에 맡긴다.
        for query in (
            "내 나이 알려줘",
            "제 생일 알려줘",
            "내 프로필 이름 알려줘",
        ):
            with self.subTest(query=query):
                self.assertIsNone(resolve_strong_retrieval_route(query))

    def test_company_self_reference_attribute_question_is_not_forced_external(self):
        # "우리 회사"/"우리회사"도 "내"/"제"와 동일하게 자기참조로 취급한다.
        for query in (
            "우리 회사 주소 알려줘",
            "우리회사 주소 알려줘",
        ):
            with self.subTest(query=query):
                self.assertIsNone(resolve_strong_retrieval_route(query))

    def test_internal_document_attribute_question_still_prefers_internal_rag(self):
        # 내부 문서를 명시적으로 지칭하면 이번 변경과 무관하게 internal_rag가
        # 여전히 우선한다 (resolve_strong_retrieval_route의 기존 우선순위 유지).
        for query in (
            "사내 문서에서 회사 주소 찾아줘",
            "첨부 문서 내용 알려줘",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    resolve_strong_retrieval_route(query),
                    "internal_rag",
                )


class FinanceStrongRouteTest(unittest.TestCase):
    """
    2026-09-02: 실제 EC2 운영에서 "삼성전자 주가는 어때?"/"아이폰 가격이
    얼마야?"가 route='no_retrieval'로 끝나 Tavily가 아예 실행되지 않는
    문제가 재현됨 - _is_likely_realtime_fact()가 시간 표현(오늘/지금 등)
    을 요구해서, 시간 표현 없이 쓰이는 FINANCE 질의를 놓쳤다.
    """

    def test_market_value_queries_route_to_realtime_search_without_time_marker(self):
        # "환율"/"주가"/"시세"류는 시간 표현이 없어도 결정적으로
        # external_or_realtime이어야 한다.
        for query in (
            "삼성전자 주가는 어때?",
            "삼성전자 주가는?",
            "원달러 환율은?",
            "원달러 환율 알려줘",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    resolve_strong_retrieval_route(query),
                    "external_or_realtime",
                )

    def test_price_queries_route_via_dedicated_price_lookup_helper(self):
        # "가격"은 market-value marker가 아니라, query_intent.
        # is_external_price_lookup_query()(전용 helper, entity_subject
        # 추출과 완전히 분리됨)가 "주어 + 가격 + 종결어미" 문장 형태
        # 전체를 확인할 때만 external_or_realtime이 된다.
        for query in (
            "아이폰 가격이 얼마야?",
            "아이폰 가격은?",
            "아이폰 가격 알려줘",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    resolve_strong_retrieval_route(query),
                    "external_or_realtime",
                )

    def test_internal_priority_is_preserved_over_finance_marker(self):
        # "가격"이라는 단어가 있어도 내부 문서 신호가 있으면 web으로
        # 뒤집히면 안 된다 - 기존 internal 우선순위(_is_explicit_internal_rag
        # / _is_company_internal_artifact_query)가 먼저 걸린다.
        self.assertEqual(
            resolve_strong_retrieval_route("우리 회사 가격 정책 문서 보여줘"),
            "internal_rag",
        )

    def test_generic_price_mention_without_internal_or_entity_shape_is_not_a_strong_route(self):
        # 내부 신호도 없고, "주어 + 가격 + 종결어미" 문장 형태도 아니면
        # (다른 단어가 사이에 끼어 있음) 결정적 signal이 아니어야 한다 -
        # 기존 ActionClassifier 판단에 맡긴다.
        self.assertIsNone(
            resolve_strong_retrieval_route("프로젝트 가격 정책 정리해줘")
        )

    def test_org_self_reference_price_query_is_not_forced_strong_external(self):
        # "우리"/"저희"로 시작하는 자기 조직/서비스 지칭은 외부 entity로
        # 확정할 수 없다 - 내부 서비스일 수도 있으므로 결정적으로
        # external_or_realtime을 강제하지 않고 기존 ActionResolver
        # 판단에 넘긴다.
        for query in (
            "우리 서비스 가격 알려줘",
            "저희 서비스 가격 알려줘",
        ):
            with self.subTest(query=query):
                self.assertNotEqual(
                    resolve_strong_retrieval_route(query),
                    "external_or_realtime",
                )

    def test_concept_questions_with_bitcoin_or_rate_are_not_strong_market_value(self):
        # "비트코인"/"금리"는 개념/분석 질문에도 흔히 쓰여서
        # is_market_value_query()의 strong routing 범위에서 뺐다 -
        # "값 조회" 의미가 뚜렷한 환율/주가/시세/코스피/코스닥만 남는다.
        # build_search_plan()의 FINANCE intent 분류에는 여전히 남아
        # 있어도 된다(서로 다른 책임 - 여기서는 확인하지 않음).
        for query in (
            "비트코인 작동 원리 설명해줘",
            "금리 인상이 경제에 미치는 영향 설명해줘",
        ):
            with self.subTest(query=query):
                self.assertFalse(is_market_value_query(query))


if __name__ == "__main__":
    unittest.main()
