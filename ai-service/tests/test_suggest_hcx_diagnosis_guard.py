import unittest
from unittest.mock import patch

from app.services.suggest_hcx import (
    _candidate_is_diagnosis_safe,
    _validated_candidates_in_hcx_order,
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
    def test_filters_candidates_and_keeps_hcx_selected_candidate_first(
        self,
        mock_predict_missing,
    ):
        baseline = state(CONTEXT=1)

        # selected_index=1 이므로 검사 순서는 B -> A -> C
        mock_predict_missing.side_effect = [
            state(CONTEXT=0),          # B: 통과
            state(CONTEXT=0, TASK=1),  # A: 다른 요소 회귀로 탈락
            state(CONTEXT=0),          # C: 통과
        ]

        result = _validated_candidates_in_hcx_order(
            text="회의 내용 정리해 줘",
            element="CONTEXT",
            candidates=["A 후보.", "B 후보.", "C 후보."],
            selected_index=1,
            baseline=baseline,
        )

        self.assertEqual(result, ["B 후보.", "C 후보."])
        self.assertEqual(mock_predict_missing.call_count, 3)


if __name__ == "__main__":
    unittest.main()