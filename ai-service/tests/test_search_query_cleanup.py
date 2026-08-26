import unittest

from app.services.retrieval.search_query_cleanup import build_search_query


class BuildSearchQueryTest(unittest.TestCase):
    """
    2026-08-26: PrompTune의 8요소 다듬기 기능이 붙인 어조/분량/대상/제약
    지시문까지 그대로 Tavily 검색어로 보내면, 실제 검색에 필요 없는 문구가
    섞여 들어가 엉뚱한 결과가 상위로 올라오는 사례가 확인됨:
    - "이강인 축구선수" 검색에 무관한 하키/축구 프리뷰 기사가 섞여 들어옴
      (관련 기사 1건은 있었는데도 최종 답변은 그 기사와도 다른 오래된 정보를 냄)
    - "침착맨" 검색 결과가 전혀 무관한 정치 기사 1건뿐이었음
    검색어에서는 이런 상투구 절을 제거하고, 실제 질문 내용만 남겨야 한다.
    """

    def test_strips_audience_tone_length_context_constraint_example_clauses(self):
        query = (
            "그럼 이강인 축구선수에대해 알려줘 지금 소속팀과 프로필 부탁해. "
            "요약해줘. 나에게. 최근 이슈와 관련해. 3문단으로. 친근하게. "
            "숫자는 꼭 포함해서"
        )
        self.assertEqual(
            build_search_query(query),
            "그럼 이강인 축구선수에대해 알려줘 지금 소속팀과 프로필 부탁해",
        )

    def test_strips_trailing_directives_but_keeps_task_verb_in_first_clause(self):
        query = (
            "침착맨이라는 유튜버를 간략하게 요약해줘. 나에게. 최근 이슈와 "
            "관련해. 3문단으로. 친근하게. 전문용어는 빼고"
        )
        self.assertEqual(
            build_search_query(query),
            "침착맨이라는 유튜버를 간략하게 요약해줘",
        )

    def test_strips_directives_with_trailing_comma_before_period(self):
        query = (
            "오늘 삼성 주가를 안내해주고,. 3문단으로. 나에게. 이번 분기 "
            "상황에서. 전문적으로. 숫자는 꼭 포함해서. 기존 템플릿 기반으로"
        )
        self.assertEqual(
            build_search_query(query),
            "오늘 삼성 주가를 안내해주고",
        )

    def test_strips_directives_from_short_query(self):
        query = (
            "lg 트윈스 단장님의 이름과 약력을 안내해줘. 나에게. 최근 이슈와 "
            "관련해. 간단하게. 친근하게. 간결하게"
        )
        self.assertEqual(
            build_search_query(query),
            "lg 트윈스 단장님의 이름과 약력을 안내해줘",
        )

    def test_falls_back_to_original_when_entire_query_is_stock_phrases(self):
        # 극단적인 경우(질의 자체가 스타일 지시문 하나뿐)에도 검색어가 아예
        # 빈 문자열이 되면 안 된다 - 잡음이 섞이더라도 검색은 되는 편이 낫다.
        self.assertEqual(build_search_query("친근하게"), "친근하게")

    def test_query_without_periods_is_unchanged(self):
        self.assertEqual(build_search_query("오늘 날씨 어때"), "오늘 날씨 어때")

    def test_empty_query_is_left_unchanged(self):
        self.assertEqual(build_search_query(""), "")

    def test_legitimate_multi_clause_content_is_preserved(self):
        query = "이강인 소식 알려줘. 최근에 이적했어? 어느 팀으로 갔어"
        self.assertEqual(
            build_search_query(query),
            "이강인 소식 알려줘 최근에 이적했어? 어느 팀으로 갔어",
        )


if __name__ == "__main__":
    unittest.main()
