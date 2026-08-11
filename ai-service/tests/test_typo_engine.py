import unittest
from unittest.mock import patch

from app.services.diagnose_rules import (
    detect_typos,
    detect_typos_detailed,
)
from app.services.spellcheck_bareun import (
    check_spelling_hybrid,
    merge_detected_typos,
)
from app.services.typo_models import DetectedTypo


class TypoRuleEngineTest(unittest.TestCase):
    def test_detect_rule_typo(self):
        result = detect_typos(
            "회의록 정리헤줘"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0].span,
            "정리헤줘",
        )
        self.assertEqual(
            result[0].suggest,
            "정리해줘",
        )

    def test_nested_rule_is_not_duplicated(self):
        result = detect_typos_detailed(
            "부탁드림니다"
        )

        self.assertEqual(len(result), 1)

        detected = result[0]

        self.assertEqual(
            detected.span,
            "부탁드림니다",
        )
        self.assertEqual(
            detected.suggest,
            "부탁드립니다",
        )
        self.assertEqual(
            detected.start,
            0,
        )
        self.assertEqual(
            detected.end,
            6,
        )
        self.assertEqual(
            detected.source,
            "rule",
        )

    def test_same_typo_can_be_detected_twice(self):
        result = detect_typos_detailed(
            "정리헤줘 하고 다시 정리헤줘"
        )

        self.assertEqual(len(result), 2)

        self.assertEqual(
            (result[0].start, result[0].end),
            (0, 4),
        )
        self.assertEqual(
            (result[1].start, result[1].end),
            (11, 15),
        )


class TypoMergeEngineTest(unittest.TestCase):
    def test_spacing_and_rule_are_merged(self):
        rule = DetectedTypo(
            span="정리헤줘",
            suggest="정리해줘",
            start=3,
            end=7,
            source="rule",
            category="keyboard_typo",
            priority=100,
        )

        bareun_spacing = DetectedTypo(
            span="회의록정리헤줘",
            suggest="회의록 정리헤줘",
            start=0,
            end=7,
            source="bareun",
            category="SPACING",
            priority=60,
        )

        bareun_inner_spacing = DetectedTypo(
            span="정리헤줘",
            suggest="정리 헤줘",
            start=3,
            end=7,
            source="bareun",
            category="SPACING",
            priority=60,
        )

        bareun_typo = DetectedTypo(
            span="헤줘",
            suggest="해줘",
            start=5,
            end=7,
            source="bareun",
            category="TYPO",
            priority=80,
        )

        result = merge_detected_typos(
            text="회의록정리헤줘",
            rule_typos=[rule],
            bareun_typos=[
                bareun_spacing,
                bareun_inner_spacing,
                bareun_typo,
            ],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0].span,
            "회의록정리헤줘",
        )
        self.assertEqual(
            result[0].suggest,
            "회의록 정리해줘",
        )

    def test_rule_wins_when_same_range_conflicts(self):
        rule = DetectedTypo(
            span="한태",
            suggest="한테",
            start=3,
            end=5,
            source="rule",
            category="particle_typo",
            priority=95,
        )

        bareun = DetectedTypo(
            span="한태",
            suggest="한 태",
            start=3,
            end=5,
            source="bareun",
            category="SPACING",
            priority=60,
        )

        result = merge_detected_typos(
            text="담당자한태",
            rule_typos=[rule],
            bareun_typos=[bareun],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0].span,
            "한태",
        )
        self.assertEqual(
            result[0].suggest,
            "한테",
        )


class HybridSpellcheckTest(unittest.TestCase):
    @patch(
        "app.services.spellcheck_bareun."
        "check_spelling_detailed"
    )
    def test_bareun_failure_falls_back_to_rule(
        self,
        mock_check_spelling,
    ):
        mock_check_spelling.side_effect = RuntimeError(
            "Bareun unavailable"
        )

        result = check_spelling_hybrid(
            "회의록 정리헤줘"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0].span,
            "정리헤줘",
        )
        self.assertEqual(
            result[0].suggest,
            "정리해줘",
        )

    @patch(
        "app.services.spellcheck_bareun."
        "check_spelling_detailed"
    )
    def test_normal_sentence_has_no_typo(
        self,
        mock_check_spelling,
    ):
        mock_check_spelling.return_value = []

        result = check_spelling_hybrid(
            "오늘 회의 내용을 정리해 주세요."
        )

        self.assertEqual(
            result,
            [],
        )


if __name__ == "__main__":
    unittest.main()