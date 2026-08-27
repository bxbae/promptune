import unittest

from app.schemas.models import ValidateRequest
from app.services.pipeline_mock import validate


class PipelineMockValidateTest(unittest.TestCase):
    """
    2026-08-27: "리센느. 요약해줘. 나에게. 발매 곡 기준으로 추가로 필요한
    정보: [대상/수신자], [배경/상황 정보], [원하는 출력 형식], 전문적으로,
    3~4줄로, [제약 조건]. 숫자는 꼭 포함해서" 요청이 재생성까지 두 번 다
    검증에 실패해 503("검증을 통과하는 답변을 생성하지 못했습니다")으로
    노출된 사례가 팀원 리포트로 재현됨.

    docker logs에서 [Validate] 로그가 전혀 안 찍힌 것으로, 이 환경은
    USE_REAL_VALIDATION=false라서 rule_validator.py(real 경로)가 아니라
    이 pipeline_mock.validate()가 실제로 쓰이고 있음을 확인함. 원인은
    이 모듈의 _FORMAT_INSTRUCTION_NUM_RE가 "3~4줄로"처럼 범위(~)로 된
    서식 지시어를 처리 못 해서 - "4줄"만 지워지고 "3"은 그대로 남아
    "반드시 결과에 있어야 하는 사실 숫자"로 오인됨(생성된 요약문에 우연히
    숫자 "3"이 없으면 바로 실패). rule_validator.py의
    _FORMAT_DIRECTIVE_NUMBER_RE에는 이미 "(?:~\\d+)?" range 처리가
    있었는데, 이 mock 쪽 정규식(2026-08-25에 별도로 추가됨)에는 그
    수정이 반영되지 않아 같은 클래스의 버그가 재발한 것.

    이 모듈에는 지금까지 전용 테스트가 없었다 - 그래서 rule_validator.py
    쪽만 고쳐지고 이 mock 쪽 회귀는 아무도 못 잡았다.
    """

    def test_range_format_directive_length_does_not_require_leaked_number(
        self,
    ):
        original = (
            "리센느. 요약해줘. 나에게. 발매 곡 기준으로 추가로 필요한 정보: "
            "[대상/수신자], [배경/상황 정보], [원하는 출력 형식], 전문적으로, "
            "3~4줄로, [제약 조건]. 숫자는 꼭 포함해서"
        )
        generated = "리센느는 대한민국의 가수입니다. 정확한 정보를 찾기 어렵습니다."

        request = ValidateRequest(original=original, generated=generated)
        result = validate(request)

        self.assertTrue(result.facts_preserved)
        self.assertTrue(result.rule_ok)
        self.assertTrue(result.passed)
        self.assertEqual(result.issues, [])

    def test_other_range_format_directives_are_also_excluded(self):
        for phrase in ("3~4문단으로", "5~6줄로", "2~3가지로"):
            with self.subTest(phrase=phrase):
                original = f"아무 주제나 요약해줘. {phrase}. 숫자는 꼭 포함해서"
                generated = "요청하신 내용을 정리했습니다."

                request = ValidateRequest(
                    original=original, generated=generated
                )
                result = validate(request)

                self.assertTrue(result.facts_preserved, phrase)
                self.assertTrue(result.passed, phrase)

    def test_real_fact_number_is_still_required(self):
        # 회귀 방지: 서식 지시어 단위(문단/문장/줄/개/가지/...)가 전혀 안 붙는
        # 진짜 사실 숫자(예: 원문에 언급된 연도)는 여전히 결과에 보존돼야
        # 한다. ("N개"/"N가지"는 이 mock 모듈이 서식 지시어 단위 목록에
        # 포함시켜 놓은 기존 동작이라 이 테스트의 범위가 아님.)
        original = "2001년생 이강인 선수를 요약해서 알려줘"
        generated = "이강인 선수는 아틀레티코 마드리드 소속입니다."

        request = ValidateRequest(original=original, generated=generated)
        result = validate(request)

        self.assertFalse(result.facts_preserved)
        self.assertFalse(result.passed)
        self.assertIn("2001", result.issues[0])

    def test_single_number_format_directive_is_still_excluded(self):
        # 기존 동작(범위가 아닌 단일 숫자 서식 지시어) 회귀 방지.
        original = "이강인 선수 프로필을 3문단으로 요약해줘"
        generated = "이강인 선수는 아틀레티코 마드리드 소속입니다."

        request = ValidateRequest(original=original, generated=generated)
        result = validate(request)

        self.assertTrue(result.facts_preserved)
        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()
