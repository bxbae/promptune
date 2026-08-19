import unittest

from app.schemas.models import PreferenceInput, PromptRuleRequest
from app.services.prompt_rule import apply_prompt_rule


def make_request(
    *,
    task_type="email",
    speed="fast",
    detail="brief",
    preserve="keep",
    missing=None,
):
    return PromptRuleRequest(
        text="테스트 프롬프트",
        missing=missing or {},
        task_type=task_type,
        preference=PreferenceInput(
            speed=speed,
            detail=detail,
            preserve=preserve,
        ),
    )


class PromptRuleTest(unittest.TestCase):

    def test_missing_elements_are_extracted_in_official_order(self):
        req = make_request(
            missing={
                "EXAMPLE": 1,
                "TASK": 1,
                "CONTEXT": 1,
                "FORMAT": 0,
                "UNKNOWN": 1,
            },
        )

        result = apply_prompt_rule(req)

        self.assertEqual(
            result.missing_elements,
            ["TASK", "CONTEXT", "EXAMPLE"],
        )

    def test_report_accurate_improve_enables_role(self):
        req = make_request(
            task_type="report",
            speed="accurate",
            preserve="improve",
        )

        result = apply_prompt_rule(req)

        self.assertTrue(result.use_role)
        self.assertEqual(
            result.role_hint,
            "업무 보고서 작성 전문가",
        )
        self.assertTrue(result.use_positive_instruction)

    def test_report_fast_improve_disables_active_strategies(self):
        req = make_request(
            task_type="report",
            speed="fast",
            preserve="improve",
        )

        result = apply_prompt_rule(req)

        self.assertFalse(result.use_role)
        self.assertIsNone(result.role_hint)
        self.assertFalse(result.use_positive_instruction)

    def test_report_accurate_keep_disables_active_strategies(self):
        req = make_request(
            task_type="report",
            speed="accurate",
            preserve="keep",
        )

        result = apply_prompt_rule(req)

        self.assertFalse(result.use_role)
        self.assertIsNone(result.role_hint)
        self.assertFalse(result.use_positive_instruction)

    def test_email_does_not_enable_role_even_when_active_improvement_allowed(self):
        req = make_request(
            task_type="email",
            speed="accurate",
            preserve="improve",
        )

        result = apply_prompt_rule(req)

        self.assertFalse(result.use_role)
        self.assertIsNone(result.role_hint)
        self.assertTrue(result.use_positive_instruction)

    def test_report_internal_uses_internal_report_role_hint(self):
        req = make_request(
            task_type="report_internal",
            speed="accurate",
            preserve="improve",
        )

        result = apply_prompt_rule(req)

        self.assertTrue(result.use_role)
        self.assertEqual(
            result.role_hint,
            "사내 보고 문서 작성 전문가",
        )

    def test_decompose_task_is_false_in_phase2b(self):
        req = make_request(
            task_type="report",
            speed="accurate",
            detail="detailed",
            preserve="improve",
        )

        result = apply_prompt_rule(req)

        self.assertFalse(result.decompose_task)

    def test_few_shot_is_false_in_phase2b(self):
        req = make_request(
            task_type="report_internal",
            speed="accurate",
            detail="detailed",
            preserve="improve",
        )

        result = apply_prompt_rule(req)

        self.assertFalse(result.use_few_shot)

    def test_detail_does_not_change_phase2b_strategy(self):
        brief = apply_prompt_rule(
            make_request(
                task_type="report",
                speed="accurate",
                detail="brief",
                preserve="improve",
            )
        )

        detailed = apply_prompt_rule(
            make_request(
                task_type="report",
                speed="accurate",
                detail="detailed",
                preserve="improve",
            )
        )

        self.assertEqual(brief.use_role, detailed.use_role)
        self.assertEqual(
            brief.use_positive_instruction,
            detailed.use_positive_instruction,
        )
        self.assertEqual(
            brief.decompose_task,
            detailed.decompose_task,
        )


if __name__ == "__main__":
    unittest.main()