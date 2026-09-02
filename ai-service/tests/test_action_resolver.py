import unittest

from app.services.action.action_resolver import resolve_action


class ActionResolverTest(unittest.TestCase):

    def test_chat_without_retrieval(self):
        plan = resolve_action("안녕하세요 오늘도 잘 부탁해")
        self.assertEqual(plan.action.value, "CHAT")
        self.assertEqual(plan.retrieval_route, "no_retrieval")
        self.assertFalse(plan.retrieval_required)

    def test_memory_write(self):
        plan = resolve_action("앞으로 나를 사장님이라고 불러줘")
        self.assertEqual(plan.action.value, "MEMORY_WRITE")
        self.assertEqual(plan.retrieval_route, "no_retrieval")

    def test_memory_read(self):
        plan = resolve_action("내 프로젝트 이름 뭐라고 했지?")
        self.assertEqual(plan.action.value, "MEMORY_READ")
        self.assertEqual(plan.retrieval_route, "no_retrieval")

    def test_web_fact(self):
        plan = resolve_action("리센느라는 그룹에 대해 알려줘")
        self.assertEqual(plan.action.value, "WEB_FACT")
        self.assertEqual(
            plan.retrieval_route,
            "external_or_realtime",
        )

    def test_realtime_fact(self):
        plan = resolve_action("오늘 원달러 환율 얼마야?")
        self.assertEqual(plan.action.value, "WEB_FACT")

    def test_internal_document(self):
        plan = resolve_action("첨부한 계약서 핵심 내용 알려줘")
        self.assertEqual(plan.action.value, "INTERNAL_DOC")

    def test_transform(self):
        plan = resolve_action("이 문장을 좀 더 자연스럽게 수정해줘")
        self.assertEqual(plan.action.value, "TEXT_TRANSFORM")
        self.assertEqual(plan.retrieval_route, "no_retrieval")

    def test_greeting_word_is_not_always_chat(self):
        plan = resolve_action("안녕이라는 표현의 유래를 조사해줘")
        self.assertEqual(plan.action.value, "WEB_FACT")


if __name__ == "__main__":
    unittest.main()


class StrongRetrievalSignalTest(unittest.TestCase):

    def test_realtime_weather_is_strong_web_signal(self):
        from app.services.retrieval.ml_router import (
            resolve_strong_retrieval_route,
        )

        self.assertEqual(
            resolve_strong_retrieval_route("오늘 날씨 어때?"),
            "external_or_realtime",
        )

    def test_third_party_profile_is_strong_web_signal(self):
        from app.services.retrieval.ml_router import (
            resolve_strong_retrieval_route,
        )

        self.assertEqual(
            resolve_strong_retrieval_route(
                "lg 트윈스 단장님의 이름과 약력을 안내해줘"
            ),
            "external_or_realtime",
        )

    def test_greeting_has_no_strong_retrieval_signal(self):
        from app.services.retrieval.ml_router import (
            resolve_strong_retrieval_route,
        )

        self.assertIsNone(
            resolve_strong_retrieval_route("안녕")
        )


class ExecutionContextActionResolverTest(unittest.TestCase):

    def test_current_user_name_is_normalized_to_self_context(self):
        plan = resolve_action(
            "차승연 이력서 알려줘",
            {
                "name": "차승연",
                "displayName": "차승연",
            },
        )

        self.assertEqual(
            plan.routing_query,
            "내 이력서 알려줘",
        )
        self.assertEqual(
            plan.action.value,
            "USER_CONTEXT",
        )
        self.assertEqual(
            plan.retrieval_route,
            "user_context",
        )

    def test_current_user_possessive_name_is_self_context(self):
        plan = resolve_action(
            "차승연의 경력 정리해줘",
            {"name": "차승연"},
        )

        self.assertEqual(
            plan.routing_query,
            "내 경력 정리해줘",
        )
        self.assertEqual(
            plan.action.value,
            "USER_CONTEXT",
        )

    def test_other_person_is_not_normalized_to_self(self):
        plan = resolve_action(
            "손흥민 이력서 알려줘",
            {"name": "차승연"},
        )

        self.assertEqual(
            plan.routing_query,
            "손흥민 이력서 알려줘",
        )
        self.assertEqual(
            plan.action.value,
            "WEB_FACT",
        )

    def test_current_user_web_news_remains_web(self):
        plan = resolve_action(
            "차승연 최근 뉴스 찾아줘",
            {"name": "차승연"},
        )

        self.assertNotEqual(
            plan.action.value,
            "USER_CONTEXT",
        )

    def test_self_referential_attribute_questions_route_to_user_context(self):
        # 2026-09-02 회귀: ActionClassifier가 "내 나이"/"제 생일"/"내 소속"을
        # 독자적으로 WEB_FACT(confidence 0.29~0.31)로 오분류해 Tavily 웹검색
        # 으로 잘못 나가던 문제. self_reference_attribute_guard가 ML보다
        # 먼저 기존 USER_CONTEXT action/route로 결정적으로 보내야 한다.
        for query in (
            "내 나이 알려줘",
            "제 생일 알려줘",
            "내 이름 알려줘",
            "내 프로필 알려줘",
            "내 프로필 이름 알려줘",
            "내 소속 알려줘",
        ):
            with self.subTest(query=query):
                plan = resolve_action(query)
                self.assertEqual(plan.action.value, "USER_CONTEXT")
                self.assertEqual(plan.retrieval_route, "user_context")
                self.assertEqual(
                    plan.reason,
                    "self_reference_attribute_guard",
                )

    def test_third_party_attribute_questions_are_not_treated_as_self_reference(self):
        # 속성 명사만 보고 guard가 과잉 적용되면 안 된다 - 외부 entity
        # 질문은 그대로 WEB_FACT/ActionClassifier 판단으로 남아야 한다.
        for query in (
            "손흥민 나이 알려줘",
            "아이유 생일이 언제야",
        ):
            with self.subTest(query=query):
                plan = resolve_action(query)
                self.assertNotEqual(plan.action.value, "USER_CONTEXT")
                self.assertNotEqual(
                    plan.reason,
                    "self_reference_attribute_guard",
                )

    def test_company_self_reference_attribute_question_is_not_forced_user_context(self):
        # "우리 회사 주소 알려줘"는 이번 guard의 대상이 아니다(회사
        # 자기참조는 별도 문제) - USER_CONTEXT로 강제하지 않는다.
        plan = resolve_action("우리 회사 주소 알려줘")
        self.assertNotEqual(
            plan.reason,
            "self_reference_attribute_guard",
        )
