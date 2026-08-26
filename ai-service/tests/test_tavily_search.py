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


if __name__ == "__main__":
    unittest.main()
