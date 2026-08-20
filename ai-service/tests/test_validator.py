import unittest
from unittest.mock import patch

from app.services.validation.semantic_validator import (
    SemanticValidationResult,
)
from app.services.validation.validator import validate_response


class FinalValidatorTest(unittest.TestCase):

    @patch("app.services.validation.validator.validate_semantic")
    def test_passes_when_rule_and_semantic_both_pass(
        self,
        mock_semantic,
    ):
        mock_semantic.return_value = SemanticValidationResult(
            semantic_ok=True,
            score=0.82,
            issues=[],
        )

        result = validate_response(
            original="핵심 내용을 3개 항목으로 정리해줘",
            generated="- 첫째\n- 둘째\n- 셋째",
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.rule_ok)
        self.assertTrue(result.semantic_ok)
        self.assertEqual(result.issues, [])

    @patch("app.services.validation.validator.validate_semantic")
    def test_fails_when_rule_validation_fails(
        self,
        mock_semantic,
    ):
        mock_semantic.return_value = SemanticValidationResult(
            semantic_ok=True,
            score=0.85,
            issues=[],
        )

        result = validate_response(
            original="10자 이내로 작성해줘",
            generated="이 문장은 요청된 길이 제한을 분명하게 초과합니다.",
        )

        self.assertFalse(result.passed)
        self.assertFalse(result.rule_ok)
        self.assertTrue(result.semantic_ok)
        self.assertTrue(result.issues)

    @patch("app.services.validation.validator.validate_semantic")
    def test_fails_when_semantic_validation_fails(
        self,
        mock_semantic,
    ):
        mock_semantic.return_value = SemanticValidationResult(
            semantic_ok=False,
            score=0.30,
            issues=["의미 기반 지시 준수 점수가 기준보다 낮습니다."],
        )

        result = validate_response(
            original="회의 내용을 요약해줘",
            generated="오늘 날씨는 맑습니다.",
        )

        self.assertFalse(result.passed)
        self.assertTrue(result.rule_ok)
        self.assertFalse(result.semantic_ok)
        self.assertTrue(result.issues)

    @patch("app.services.validation.validator.validate_semantic")
    def test_rule_and_semantic_issues_are_merged(
        self,
        mock_semantic,
    ):
        mock_semantic.return_value = SemanticValidationResult(
            semantic_ok=False,
            score=0.30,
            issues=["의미 기반 지시 준수 실패"],
        )

        result = validate_response(
            original="10자 이내로 회의 내용을 요약해줘",
            generated="오늘 날씨에 대한 아주 긴 설명을 작성했습니다.",
        )

        self.assertFalse(result.passed)
        self.assertFalse(result.rule_ok)
        self.assertFalse(result.semantic_ok)
        self.assertGreaterEqual(len(result.issues), 2)


if __name__ == "__main__":
    unittest.main()