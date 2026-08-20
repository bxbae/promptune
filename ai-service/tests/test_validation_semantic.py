import unittest
from unittest.mock import patch

from app.services.validation.semantic_validator import validate_semantic


class SemanticValidationTest(unittest.TestCase):

    @patch(
        "app.services.validation.semantic_validator."
        "_calculate_similarity"
    )
    def test_related_response_passes(self, mock_similarity):
        mock_similarity.return_value = 0.85

        result = validate_semantic(
            original="신제품 출시 계획의 핵심 내용을 요약해줘",
            generated="신제품 출시 계획의 주요 내용을 요약했습니다.",
            threshold=0.70,
        )

        self.assertTrue(result.semantic_ok)
        self.assertEqual(result.score, 0.85)
        self.assertEqual(result.issues, [])

    @patch(
        "app.services.validation.semantic_validator."
        "_calculate_similarity"
    )
    def test_unrelated_response_fails(self, mock_similarity):
        mock_similarity.return_value = 0.25

        result = validate_semantic(
            original="신제품 출시 계획의 핵심 내용을 요약해줘",
            generated="오늘 날씨는 맑고 기온은 25도입니다.",
            threshold=0.70,
        )

        self.assertFalse(result.semantic_ok)
        self.assertEqual(result.score, 0.25)
        self.assertTrue(result.issues)

    @patch(
        "app.services.validation.semantic_validator."
        "_calculate_similarity"
    )
    def test_score_equal_to_threshold_passes(
        self,
        mock_similarity,
    ):
        mock_similarity.return_value = 0.70

        result = validate_semantic(
            original="회의 내용을 정리해줘",
            generated="회의 주요 내용을 정리했습니다.",
            threshold=0.70,
        )

        self.assertTrue(result.semantic_ok)

    def test_empty_generated_response_fails(self):
        result = validate_semantic(
            original="회의 내용을 정리해줘",
            generated="",
            threshold=0.70,
        )

        self.assertFalse(result.semantic_ok)
        self.assertTrue(result.issues)


if __name__ == "__main__":
    unittest.main()