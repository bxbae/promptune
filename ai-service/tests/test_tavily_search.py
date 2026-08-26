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
        2026-08-26: "lg 트윈스 단장님의 이름과 약력을 안내해줘" 질의에서
        news.naver.com 제한 검색이 0건이 되면서 웹 검색 결과 없이 생성이
        진행돼, HCX가 "제공할 수 없습니다"로 답을 회피하는 사례가 확인됨.
        제한된 검색이 0건이면 제한 없이 한 번 더 시도해야 한다.
        """
        os.environ.pop("TAVILY_TRUSTED_DOMAINS", None)
        mock_client = MagicMock()
        mock_client.search.side_effect = [
            {"results": []},
            {"results": [{"title": "t2", "url": "u2", "content": "c2"}]},
        ]
        mock_client_cls.return_value = mock_client

        results = search_web("lg 트윈스 단장님의 이름과 약력을 안내해줘", max_results=3)

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


if __name__ == "__main__":
    unittest.main()
