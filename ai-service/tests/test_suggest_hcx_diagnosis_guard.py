import unittest
from unittest.mock import patch

from app.services.suggest_hcx import (
    _candidate_is_diagnosis_safe,
    _validate_generated_candidates,
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


def state(**overrides):
    result = {element: 0 for element in ELEMENTS}
    result.update(overrides)
    return result


class SuggestionDiagnosisGuardTest(unittest.TestCase):
    def test_accepts_candidate_when_target_is_fixed_without_regression(self):
        baseline = state(CONTEXT=1)
        after = state(CONTEXT=0)

        self.assertTrue(
            _candidate_is_diagnosis_safe(
                element="CONTEXT",
                baseline=baseline,
                after=after,
            )
        )

    def test_rejects_candidate_when_target_is_still_missing(self):
        baseline = state(CONTEXT=1)
        after = state(CONTEXT=1)

        self.assertFalse(
            _candidate_is_diagnosis_safe(
                element="CONTEXT",
                baseline=baseline,
                after=after,
            )
        )

    def test_rejects_candidate_when_other_sufficient_element_regresses(self):
        baseline = state(CONTEXT=1, TASK=0)
        after = state(CONTEXT=0, TASK=1)

        self.assertFalse(
            _candidate_is_diagnosis_safe(
                element="CONTEXT",
                baseline=baseline,
                after=after,
            )
        )

    @patch("app.services.suggest_hcx.predict_missing")
    def test_filters_generated_candidates_and_preserves_generation_order(
        self,
        mock_predict_missing,
    ):
        baseline = state(CONTEXT=1)

        mock_predict_missing.side_effect = [
            state(CONTEXT=0),          # A 통과
            state(CONTEXT=0, TASK=1),  # B 회귀로 탈락
            state(CONTEXT=0),          # C 통과
        ]

        result = _validate_generated_candidates(
            text="회의 내용 정리해 줘",
            element="CONTEXT",
            candidates=[
                "A 후보.",
                "B 후보.",
                "C 후보.",
            ],
            baseline=baseline,
        )

        self.assertEqual(
            result,
            [
                "A 후보.",
                "C 후보.",
            ],
        )

        self.assertEqual(
            mock_predict_missing.call_count,
            3,
        )


if __name__ == "__main__":
    unittest.main()