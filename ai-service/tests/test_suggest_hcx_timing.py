import unittest
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

import torch

from app.schemas.models import ELEMENTS, SuggestRequest
from app.services.suggest_hcx import (
    _generate_candidates,
    _parse_generated_candidates,
    suggest,
)


class _FakeInputs(dict):
    def to(self, _device):
        return self


class SuggestHcxTimingTest(unittest.TestCase):
    @patch("app.services.suggest_hcx.logger.info")
    @patch(
        "app.services.suggest_hcx.time.perf_counter",
        side_effect=[10.0, 10.25, 10.5, 12.0],
    )
    @patch(
        "app.services.suggest_hcx.hcx_lock",
        side_effect=lambda: nullcontext(),
    )
    @patch("app.services.suggest_hcx._load_runtime")
    def test_generate_candidates_logs_lock_wait_and_generation_time_without_raw_content(
        self,
        mock_load_runtime,
        _mock_hcx_lock,
        _mock_perf_counter,
        mock_logger_info,
    ):
        tokenizer = MagicMock()
        model = MagicMock()

        inputs = _FakeInputs(
            input_ids=torch.tensor([[101, 102]])
        )
        tokenizer.apply_chat_template.return_value = inputs
        tokenizer.eos_token_id = 2
        tokenizer.decode.return_value = (
            '{"candidates":["임원 보고용으로 정리해줘."]}'
        )
        model.generate.return_value = torch.tensor(
            [[101, 102, 103]]
        )

        mock_load_runtime.return_value = (
            tokenizer,
            model,
            "cpu",
        )

        sensitive_text = "민감한 사용자 원문 1234"
        sensitive_context = "비공개 업무 맥락 5678"

        result = _generate_candidates(
            text=sensitive_text,
            context=sensitive_context,
            element="CONTEXT",
        )

        self.assertEqual(
            result,
            ["임원 보고용으로 정리해줘."],
        )

        mock_logger_info.assert_any_call(
            "[Suggest][Timing] "
            "element=%s context_present=%s "
            "lock_wait_ms=%.2f generation_ms=%.2f",
            "CONTEXT",
            True,
            250.0,
            1500.0,
        )

        rendered_logs = "\n".join(
            repr(call)
            for call in mock_logger_info.call_args_list
        )
        self.assertNotIn(sensitive_text, rendered_logs)
        self.assertNotIn(sensitive_context, rendered_logs)
        self.assertNotIn(
            tokenizer.decode.return_value,
            rendered_logs,
        )

    @patch("app.services.suggest_hcx.logger.info")
    @patch(
        "app.services.output_preference.merge_with_habit_fallback",
        return_value={
            "format": None,
            "length": None,
            "structure": None,
            "detail_level": None,
        },
    )
    @patch(
        "app.services.output_preference.detect_output_preferences",
        return_value={
            "format": None,
            "length": None,
            "structure": None,
            "detail_level": None,
        },
    )
    @patch("app.services.suggest_hcx.predict_missing_with_rules")
    def test_suggest_logs_normalized_target_element_count(
        self,
        mock_predict_missing,
        _mock_detect_output_preferences,
        _mock_merge_with_habit_fallback,
        mock_logger_info,
    ):
        mock_predict_missing.return_value = {
            element: 0
            for element in ELEMENTS
        }

        cases = [
            ([], 0),
            (["FORMAT"], 1),
            (["FORMAT", "TONE", "LENGTH"], 3),
        ]

        for target_elements, expected_count in cases:
            with self.subTest(
                target_elements=target_elements
            ):
                mock_logger_info.reset_mock()

                response = suggest(
                    SuggestRequest(
                        text="로그에 남으면 안 되는 사용자 원문",
                        target_elements=target_elements,
                        context=None,
                    )
                )

                self.assertEqual(
                    response.suggestions,
                    [],
                )
                mock_logger_info.assert_any_call(
                    "[Suggest][Timing] target_element_count=%d",
                    expected_count,
                )

                rendered_logs = "\n".join(
                    repr(call)
                    for call in mock_logger_info.call_args_list
                )
                self.assertNotIn(
                    "로그에 남으면 안 되는 사용자 원문",
                    rendered_logs,
                )

    def test_parse_error_does_not_echo_raw_model_output(self):
        sensitive_raw = "민감한 HCX 출력 9999"

        with self.assertRaises(RuntimeError) as ctx:
            _parse_generated_candidates(sensitive_raw)

        self.assertNotIn(
            sensitive_raw,
            str(ctx.exception),
        )


if __name__ == "__main__":
    unittest.main()
