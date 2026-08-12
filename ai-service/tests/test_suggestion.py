import unittest
from unittest.mock import patch

from app.schemas.models import SuggestRequest
from app.services.candidate_bank import get_candidates
from app.services.suggest_hcx import (
    _normalize_target_elements,
    _parse_choice,
    suggest,
)


class CandidateBankTest(unittest.TestCase):
    def test_format_context_prefers_comparison_table(self):
        candidates = get_candidates(
            element="FORMAT",
            text="경쟁사 세 곳의 가격과 기능 정리해줘",
            context="각 경쟁사의 차이를 한눈에 비교해야 한다.",
            limit=3,
        )

        self.assertEqual(
            candidates[0],
            "비교 표 형식으로 정리해서",
        )
        self.assertEqual(len(candidates), 3)

    def test_unknown_element_raises_error(self):
        with self.assertRaises(ValueError):
            get_candidates(
                element="UNKNOWN",
                text="테스트",
            )


class HcxSuggestionTest(unittest.TestCase):
    def test_parse_letter_choice(self):
        candidates = [
            "표 형식으로 정리해서",
            "불릿 목록으로 정리해서",
            "마크다운 구조로 작성해서",
        ]

        self.assertEqual(
            _parse_choice("B", candidates),
            1,
        )

    def test_parse_candidate_text_choice(self):
        candidates = [
            "표 형식으로 정리해서",
            "불릿 목록으로 정리해서",
            "마크다운 구조로 작성해서",
        ]

        self.assertEqual(
            _parse_choice(
                "불릿 목록으로 정리해서",
                candidates,
            ),
            1,
        )

    def test_target_elements_are_normalized_and_deduplicated(self):
        result = _normalize_target_elements(["format", "FORMAT", "tone"])

        self.assertEqual(
            result,
            ["FORMAT", "TONE"],
        )

    @patch(
        "app.services.suggest_hcx._rerank",
        return_value=1,
    )
    def test_suggest_builds_primary_and_alternatives(
        self,
        mock_rerank,
    ):
        req = SuggestRequest(
            text="회의 결과 정리해줘",
            target_elements=["FORMAT"],
            context="팀원들이 결정사항을 빠르게 확인해야 한다.",
        )

        result = suggest(req)

        self.assertEqual(
            len(result.suggestions),
            1,
        )

        suggestion = result.suggestions[0]

        self.assertEqual(
            suggestion.element,
            "FORMAT",
        )
        self.assertTrue(
            suggestion.primary,
        )
        self.assertEqual(
            len(suggestion.alternatives),
            2,
        )
        self.assertNotIn(
            suggestion.primary,
            suggestion.alternatives,
        )

        mock_rerank.assert_called_once()

    @patch("app.services.suggest_hcx._rerank", return_value=0)
    def test_suggest_returns_one_suggestion_per_target_element(
        self,
        mock_rerank,
    ):
        req = SuggestRequest(
            text="경쟁사 세 곳의 가격과 기능 정리해줘",
            target_elements=[
                "TASK",
                "AUDIENCE",
                "CONTEXT",
            ],
            context=None,
        )

        result = suggest(req)

        self.assertEqual(len(result.suggestions), 3)

        self.assertEqual(
            [item.element for item in result.suggestions],
            [
                "TASK",
                "AUDIENCE",
                "CONTEXT",
            ],
        )

        self.assertEqual(mock_rerank.call_count, 3)

        for item in result.suggestions:
            self.assertTrue(item.primary)
            self.assertEqual(len(item.alternatives), 2)


if __name__ == "__main__":
    unittest.main()
