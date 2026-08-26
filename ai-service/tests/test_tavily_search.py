import os
import unittest
from unittest.mock import MagicMock, patch

from app.services.retrieval.tavily_search import _trusted_domains, search_web


class TrustedDomainsTest(unittest.TestCase):
    """
    2026-08-26: "침착맨 몇살이야?" 질의에서 은퇴 준비 나이를 다루는 완전히
    무관한 영문 기사가 검색 결과에 섞여 들어와 HCX가 근거 없는 생년월일을
    지어내는 사례가 확인됨. include_domains로 신뢰 도메인(기본값: 네이버
    뉴스)만 검색하도록 제한한 뒤, 이 동작을 고정한다.
    """

    def setUp(self):
        self._original = os.environ.get("TAVILY_TRUSTED_DOMAINS")

    def tearDown(self):
        if self._original is None:
            os.environ.pop("TAVILY_TRUSTED_DOMAINS", None)
        else:
            os.environ["TAVILY_TRUSTED_DOMAINS"] = self._original

    def test_defaults_to_naver_news_when_unset(self):
        os.environ.pop("TAVILY_TRUSTED_DOMAINS", None)
        self.assertEqual(_trusted_domains(), ["news.naver.com"])

    def test_reads_comma_separated_custom_list(self):
        os.environ["TAVILY_TRUSTED_DOMAINS"] = "news.naver.com, reuters.com , cnbc.com"
        self.assertEqual(
            _trusted_domains(), ["news.naver.com", "reuters.com", "cnbc.com"]
        )

    def test_explicit_blank_value_disables_restriction(self):
        os.environ["TAVILY_TRUSTED_DOMAINS"] = "   "
        self.assertEqual(_trusted_domains(), [])


class SearchWebTest(unittest.TestCase):

    def setUp(self):
        self._original_key = os.environ.get("TAVILY_API_KEY")
        os.environ["TAVILY_API_KEY"] = "test-key"
        self._original_domains = os.environ.get("TAVILY_TRUSTED_DOMAINS")

    def tearDown(self):
        if self._original_key is None:
            os.environ.pop("TAVILY_API_KEY", None)
        else:
            os.environ["TAVILY_API_KEY"] = self._original_key
        if self._original_domains is None:
            os.environ.pop("TAVILY_TRUSTED_DOMAINS", None)
        else:
            os.environ["TAVILY_TRUSTED_DOMAINS"] = self._original_domains

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_passes_default_trusted_domains_to_tavily(self, mock_client_cls):
        os.environ.pop("TAVILY_TRUSTED_DOMAINS", None)
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": [{"title": "t", "url": "u", "content": "c"}]}
        mock_client_cls.return_value = mock_client

        results = search_web("침착맨 몇살이야", max_results=3)

        self.assertEqual(results, [{"title": "t", "url": "u", "content": "c"}])
        _, kwargs = mock_client.search.call_args
        self.assertEqual(kwargs["include_domains"], ["news.naver.com"])
        self.assertEqual(kwargs["topic"], "news")
        self.assertEqual(kwargs["max_results"], 3)

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_no_include_domains_when_restriction_disabled(self, mock_client_cls):
        os.environ["TAVILY_TRUSTED_DOMAINS"] = ""
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}
        mock_client_cls.return_value = mock_client

        search_web("아무 질의", max_results=3)

        _, kwargs = mock_client.search.call_args
        self.assertNotIn("include_domains", kwargs)

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_finance_query_uses_finance_topic_without_domain_restriction(
        self, mock_client_cls
    ):
        """
        2026-08-26: 신뢰 도메인을 news.naver.com 하나로 제한한 직후 "오늘
        삼성 주가"에 실제(261,500원)와 전혀 다른 가격(약 90,000원)을 답하는
        회귀가 확인됨 - news.naver.com은 시세 숫자가 박힌 페이지가 아니라
        일반 보도 위주라 구체적인 오늘자 가격을 못 찾고 지어낸 것으로 보임.
        시세류 질의는 Tavily 전용 topic="finance"를 쓰고 도메인 제한도
        걸지 않아야 한다.
        """
        os.environ.pop("TAVILY_TRUSTED_DOMAINS", None)
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [{"title": "t", "url": "u", "content": "261,500원"}]
        }
        mock_client_cls.return_value = mock_client

        results = search_web("오늘 삼성 주가를 안내해주고 3문단으로", max_results=3)

        self.assertEqual(
            results, [{"title": "t", "url": "u", "content": "261,500원"}]
        )
        _, kwargs = mock_client.search.call_args
        self.assertEqual(kwargs["topic"], "finance")
        self.assertNotIn("include_domains", kwargs)
        self.assertEqual(mock_client.search.call_count, 1)

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_falls_back_to_unrestricted_when_restricted_search_is_empty(
        self, mock_client_cls
    ):
        """
        2026-08-26: "어제 lg 트윈스 경기 결과 알려줘" 처럼 인물 프로필이
        아닌 뉴스성 질의에서 news.naver.com 제한 검색이 0건이 되면 웹 검색
        결과 없이 생성이 진행돼, HCX가 회피 답변을 내는 사례가 확인됨.
        제한된 검색이 0건이면 제한 없이 한 번 더 시도해야 한다.
        (인물 프로필류 질의의 도메인 제한/폴백은 ProfileQueryDomainsTest 참고 -
        "단장"/"약력" 같은 단어가 있으면 이제 이 뉴스 경로가 아니라 위키백과/
        나무위키 등 프로필 전용 경로를 탄다.)
        """
        os.environ.pop("TAVILY_TRUSTED_DOMAINS", None)
        mock_client = MagicMock()
        mock_client.search.side_effect = [
            {"results": []},
            {"results": [{"title": "t2", "url": "u2", "content": "c2"}]},
        ]
        mock_client_cls.return_value = mock_client

        results = search_web("어제 lg 트윈스 경기 결과 알려줘", max_results=3)

        self.assertEqual(
            results, [{"title": "t2", "url": "u2", "content": "c2"}]
        )
        self.assertEqual(mock_client.search.call_count, 2)

        first_kwargs = mock_client.search.call_args_list[0].kwargs
        second_kwargs = mock_client.search.call_args_list[1].kwargs
        self.assertEqual(first_kwargs["include_domains"], ["news.naver.com"])
        self.assertNotIn("include_domains", second_kwargs)

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_no_fallback_call_when_restricted_search_has_results(
        self, mock_client_cls
    ):
        os.environ.pop("TAVILY_TRUSTED_DOMAINS", None)
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [{"title": "t", "url": "u", "content": "c"}]
        }
        mock_client_cls.return_value = mock_client

        search_web("아무 뉴스 질의", max_results=3)

        self.assertEqual(mock_client.search.call_count, 1)


class ProfileQueryDomainsTest(unittest.TestCase):
    """
    2026-08-26: "이강인 축구선수 프로필/소속" 질의가 (검색어 정제 이후로는)
    관련 있는 기사를 찾긴 하는데도, 나무위키의 오래된 문단(발렌시아 CF
    시절)이나 근거 없는 수치(체중 90kg, 생년월일 2003년 등 - 실제는 66kg,
    2001년생)를 섞어 답하는 사례가 확인됨. 사용자가 "선수는 올림픽 사이트,
    가수/배우는 그래미 사이트 기준으로" 요청해서, 인물 프로필류 질의는
    위키백과/나무위키(+종목별 공식 사이트)로 검색을 제한한다.
    """

    def setUp(self):
        self._original_key = os.environ.get("TAVILY_API_KEY")
        os.environ["TAVILY_API_KEY"] = "test-key"
        # 2026-08-26: 샌드박스 셸 환경에 TAVILY_TRUSTED_DOMAINS=""가 미리
        # 설정돼 있어서(다른 테스트 클래스는 각자 pop/restore로 정규화함),
        # 여기서도 동일하게 정규화하지 않으면 뉴스 경로(비-프로필 질의)를
        # 검증하는 테스트가 우연한 셸 상태에 따라 흔들린다.
        self._original_domains = os.environ.get("TAVILY_TRUSTED_DOMAINS")
        os.environ.pop("TAVILY_TRUSTED_DOMAINS", None)

    def tearDown(self):
        if self._original_key is None:
            os.environ.pop("TAVILY_API_KEY", None)
        else:
            os.environ["TAVILY_API_KEY"] = self._original_key
        if self._original_domains is None:
            os.environ.pop("TAVILY_TRUSTED_DOMAINS", None)
        else:
            os.environ["TAVILY_TRUSTED_DOMAINS"] = self._original_domains

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_athlete_profile_query_uses_all_four_profile_domains(
        self, mock_client_cls
    ):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [{"title": "이강인", "url": "u", "content": "c"}]
        }
        mock_client_cls.return_value = mock_client

        search_web("그럼 이강인 축구선수에대해 알려줘 지금 소속팀과 프로필 부탁해", max_results=3)

        _, kwargs = mock_client.search.call_args
        self.assertEqual(kwargs["topic"], "general")
        self.assertEqual(
            kwargs["include_domains"],
            ["ko.wikipedia.org", "namu.wiki", "olympics.com", "grammy.com"],
        )

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_singer_actor_profile_query_includes_grammy(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [{"title": "t", "url": "u", "content": "c"}]
        }
        mock_client_cls.return_value = mock_client

        search_web("어느 가수의 프로필을 알려줘", max_results=3)

        _, kwargs = mock_client.search.call_args
        self.assertEqual(
            kwargs["include_domains"],
            ["ko.wikipedia.org", "namu.wiki", "olympics.com", "grammy.com"],
        )

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_profile_query_without_category_keyword_still_includes_all_domains(
        self, mock_client_cls
    ):
        # 2026-08-26: "이강인 소속과 프로필을 알려줘"처럼 "선수"/"축구" 같은
        # 직업 카테고리 단어가 전혀 없는 프로필 질의에서 olympics.com이
        # 빠져서 결과가 부실해지는 사례가 반복 확인됨 - 카테고리 추측 없이
        # 항상 4개 도메인 전부 후보에 넣도록 고쳤다.
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [{"title": "이강인", "url": "u", "content": "c"}]
        }
        mock_client_cls.return_value = mock_client

        search_web("이강인 소속과 프로필을 알려줘", max_results=3)

        _, kwargs = mock_client.search.call_args
        self.assertEqual(
            kwargs["include_domains"],
            ["ko.wikipedia.org", "namu.wiki", "olympics.com", "grammy.com"],
        )

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_profile_query_falls_back_to_unrestricted_when_empty(
        self, mock_client_cls
    ):
        mock_client = MagicMock()
        mock_client.search.side_effect = [
            {"results": []},
            {"results": [{"title": "t2", "url": "u2", "content": "c2"}]},
        ]
        mock_client_cls.return_value = mock_client

        results = search_web(
            "lg 트윈스 단장님의 이름과 약력을 안내해줘", max_results=3
        )

        self.assertEqual(
            results, [{"title": "t2", "url": "u2", "content": "c2"}]
        )
        self.assertEqual(mock_client.search.call_count, 2)

        first_kwargs = mock_client.search.call_args_list[0].kwargs
        second_kwargs = mock_client.search.call_args_list[1].kwargs
        self.assertEqual(first_kwargs["topic"], "general")
        self.assertEqual(
            first_kwargs["include_domains"],
            ["ko.wikipedia.org", "namu.wiki", "olympics.com", "grammy.com"],
        )
        self.assertNotIn("include_domains", second_kwargs)

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_stale_wiki_revision_results_are_filtered_out(
        self, mock_client_cls
    ):
        # 2026-08-26: "이강인 소속과 프로필" 검색 결과에 "이강인 (r444 판)",
        # "이강인 (r297 판)"처럼 예전 리비전 스냅샷(발렌시아 CF 시절 등,
        # 현재 소속이 반영 안 됨)이 섞여 들어와 답변이 오래된 정보로
        # 후퇴한 사례가 확인됨 - 이런 스냅샷 결과는 걸러야 한다.
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "이강인 (r444 판) - 나무위키", "url": "u1", "content": "c1"},
                {"title": "이강인 (r297 판) - 나무위키", "url": "u2", "content": "c2"},
                {"title": "이강인 - 나무위키", "url": "u3", "content": "c3"},
            ]
        }
        mock_client_cls.return_value = mock_client

        results = search_web("이강인 소속과 프로필을 알려줘", max_results=3)

        self.assertEqual(
            results,
            [{"title": "이강인 - 나무위키", "url": "u3", "content": "c3"}],
        )

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_all_stale_wiki_revisions_trigger_unrestricted_fallback(
        self, mock_client_cls
    ):
        # 필터링 결과 0건이 되면(전부 예전 리비전이면), 기존 "0건이면 무제한
        # 재시도" 폴백이 그대로 이어받아야 한다.
        mock_client = MagicMock()
        mock_client.search.side_effect = [
            {
                "results": [
                    {"title": "이강인 (r444 판)", "url": "u1", "content": "c1"},
                ]
            },
            {"results": [{"title": "이강인 최신", "url": "u2", "content": "c2"}]},
        ]
        mock_client_cls.return_value = mock_client

        results = search_web("이강인 소속과 프로필을 알려줘", max_results=3)

        self.assertEqual(
            results, [{"title": "이강인 최신", "url": "u2", "content": "c2"}]
        )
        self.assertEqual(mock_client.search.call_count, 2)

    @patch("app.services.retrieval.tavily_search.TavilyClient")
    def test_non_profile_query_is_unaffected(self, mock_client_cls):
        mock_client = MagicMock()
        # 결과를 비워두면(빈 리스트) 뉴스 경로의 "0건이면 무제한 재시도"
        # 폴백(0008)이 걸려서 두 번째 호출(무제한)이 마지막 call_args가 돼
        # 버리므로, 이 테스트에서 확인하려는 "첫 호출이 뉴스+신뢰 도메인으로
        # 나가는지"를 결과가 있는 상태로 확인한다.
        mock_client.search.return_value = {
            "results": [{"title": "t", "url": "u", "content": "c"}]
        }
        mock_client_cls.return_value = mock_client

        search_web("어제 lg 트윈스 경기 결과 알려줘", max_results=3)

        _, kwargs = mock_client.search.call_args
        self.assertEqual(kwargs["topic"], "news")
        self.assertEqual(kwargs["include_domains"], ["news.naver.com"])
        self.assertEqual(mock_client.search.call_count, 1)


if __name__ == "__main__":
    unittest.main()
