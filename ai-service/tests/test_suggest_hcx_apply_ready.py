import unittest
from unittest.mock import patch

from app.schemas.models import SuggestRequest
from app.services.suggest_hcx import (
    _make_apply_ready_candidate,
    _prepare_candidates,
    suggest,
)



ELEMENTS = [
    "TASK",
    "AUDIENCE",
    "CONTEXT",
    "FORMAT",
    "TONE",
    "LENGTH",
    "CONSTRAINT",
    "EXAMPLE",
]


def _predict_missing_with_valid_candidates(original_text: str):
    """
    suggest() 단위 테스트에서는 실제 KcELECTRA 모델을 로드하지 않는다.
    원문은 보완 필요(1), 후보 적용 후 문장은 충분(0)으로 가정해
    diagnosis guard와 기존 suggest 동작을 함께 검증한다.
    """
    def fake_predict_missing(text: str) -> dict[str, int]:
        if text == original_text:
            return {element: 1 for element in ELEMENTS}

        return {element: 0 for element in ELEMENTS}

    return fake_predict_missing


class SuggestApplyReadyCandidateTest(unittest.TestCase):
    def test_context_candidate_becomes_explicit_context_statement(self):
        self.assertEqual(
            _make_apply_ready_candidate(
                "CONTEXT",
                "내부 공유용 자료라는 배경을 반영해서",
            ),
            "내부 공유용 자료로 사용할 예정이야.",
        )

    def test_format_candidate_becomes_complete_instruction(self):
        self.assertEqual(
            _make_apply_ready_candidate(
                "FORMAT",
                "표 형식으로 정리해서",
            ),
            "표 형식으로 정리해줘.",
        )

    def test_audience_candidate_becomes_complete_instruction(self):
        self.assertEqual(
            _make_apply_ready_candidate(
                "AUDIENCE",
                "임원진을 대상으로",
            ),
            "임원진을 대상으로 작성해줘.",
        )

    def test_prepare_candidates_requires_three_unique_items(self):
        with self.assertRaises(ValueError):
            _prepare_candidates(
                "FORMAT",
                ["표 형식으로 정리해서"] * 3,
            )

    @patch("app.services.suggest_hcx._rerank", side_effect=RuntimeError("boom"))
    @patch(
        "app.services.suggest_hcx.get_candidates",
        return_value=[
            "의사결정을 위한 자료라는 배경을 반영해서",
            "내부 공유용 자료라는 배경을 반영해서",
            "회의 후속 업무를 위한 자료라는 배경을 반영해서",
        ],
    )
    def test_suggest_uses_first_candidate_when_rerank_fails(
        self,
        mock_get_candidates,
        mock_rerank,
    ):
        req = SuggestRequest(
            text="회의 내용 정리해줘",
            target_elements=["CONTEXT"],
            context=None,
        )

        with patch(
            "app.services.suggest_hcx.predict_missing",
            side_effect=_predict_missing_with_valid_candidates(req.text),
        ):
            result = suggest(req)

        self.assertEqual(len(result.suggestions), 1)
        self.assertEqual(
            result.suggestions[0].primary,
            "의사결정을 위한 자료로 사용할 예정이야.",
        )
        self.assertEqual(len(result.suggestions[0].alternatives), 2)


if __name__ == "__main__":
    unittest.main()