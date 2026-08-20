import unittest

from app.services.validation.rule_validator import validate_rules


class ValidationRuleTest(unittest.TestCase):

    def test_max_length_passes(self):
        original = "100자 이내로 작성해줘"
        generated = "짧게 작성한 답변입니다."

        result = validate_rules(original, generated)

        self.assertTrue(result.length_ok)

    def test_max_length_fails(self):
        original = "10자 이내로 작성해줘"
        generated = "이 문장은 열 글자를 명확하게 초과하는 답변입니다."

        result = validate_rules(original, generated)

        self.assertFalse(result.length_ok)

    def test_requested_item_count_passes(self):
        original = "핵심 내용을 3개 항목으로 정리해줘"
        generated = "- 첫 번째\n- 두 번째\n- 세 번째"

        result = validate_rules(original, generated)

        self.assertTrue(result.item_count_ok)

    def test_markdown_table_passes(self):
        original = "결과를 표 형식으로 정리해줘"
        generated = (
            "| 항목 | 내용 |\n"
            "| --- | --- |\n"
            "| A | 설명 |\n"
        )

        result = validate_rules(original, generated)

        self.assertTrue(result.format_ok)

    def test_plain_text_fails_when_table_requested(self):
        original = "결과를 표 형식으로 정리해줘"
        generated = "A 항목에 대한 설명입니다."

        result = validate_rules(original, generated)

        self.assertFalse(result.format_ok)

    def test_fact_numbers_are_preserved(self):
        original = "매출은 120억이고 성장률은 15%야. 이를 요약해줘"
        generated = "매출은 120억이며 성장률은 15%입니다."

        result = validate_rules(original, generated)

        self.assertTrue(result.facts_preserved)

    def test_missing_fact_number_fails(self):
        original = "매출은 120억이고 성장률은 15%야. 이를 요약해줘"
        generated = "매출은 120억입니다."

        result = validate_rules(original, generated)

        self.assertFalse(result.facts_preserved)

    def test_constraint_number_is_not_treated_as_fact(self):
        original = "핵심 내용을 3개 항목으로 정리해줘"
        generated = "- A\n- B\n- C"

        result = validate_rules(original, generated)

        self.assertTrue(result.facts_preserved)

    def test_product_quantity_is_not_item_count_constraint(self):
        original = "사과 3개 가격을 요약해줘"
        generated = "사과 3개의 가격을 요약했습니다."

        result = validate_rules(original, generated)

        self.assertTrue(result.item_count_ok)


    def test_product_quantity_is_treated_as_fact_number(self):
        original = "사과 3개 가격을 요약해줘"
        generated = "사과 가격을 요약했습니다."

        result = validate_rules(original, generated)

        self.assertFalse(result.facts_preserved)


if __name__ == "__main__":
    unittest.main()