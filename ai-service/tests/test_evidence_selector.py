import unittest

from app.services.retrieval.evidence_selector import (
    select_web_evidence,
    _query_tokens,
)


class EvidenceSelectorTest(unittest.TestCase):

    def test_entity_match_beats_mismatch(self):
        results = [
            {
                "title": "다른 아이돌 해외 활동",
                "url": "https://news.example/a",
                "content": "다른 그룹의 활동",
                "score": 0.90,
            },
            {
                "title": "BTS 경제적 영향",
                "url": "https://news.example/b",
                "content": "BTS의 국가 경제 기여",
                "score": 0.82,
            },
        ]

        selected = select_web_evidence(
            results,
            query="BTS가 국가에 기여한 점",
            intent="RESEARCH",
            entity="BTS",
            limit=1,
        )

        self.assertEqual(
            selected[0]["title"],
            "BTS 경제적 영향",
        )

    def test_research_authority_bonus(self):
        results = [
            {
                "title": "BTS 경제 효과 블로그",
                "url": "https://blog.example/a",
                "content": "BTS 경제 효과",
                "score": 0.85,
            },
            {
                "title": "BTS 문화경제 연구",
                "url": "https://example.go.kr/report",
                "content": "BTS 문화 경제 기여 연구",
                "score": 0.75,
            },
        ]

        selected = select_web_evidence(
            results,
            query="BTS 국가 기여",
            intent="RESEARCH",
            entity="BTS",
            limit=1,
        )

        self.assertIn(
            "go.kr",
            selected[0]["url"],
        )

    def test_duplicate_removed(self):
        results = [
            {
                "title": "같은 기사",
                "url": "https://example.com/a",
                "content": "첫 결과",
                "score": 0.9,
            },
            {
                "title": "같은 기사",
                "url": "https://example.com/b",
                "content": "중복 결과",
                "score": 0.8,
            },
        ]

        selected = select_web_evidence(
            results,
            query="테스트",
            intent="GENERAL",
            entity=None,
            limit=3,
        )

        self.assertEqual(
            len(selected),
            1,
        )

    def test_limit(self):
        results = [
            {
                "title": f"result-{i}",
                "url": f"https://example.com/{i}",
                "content": "내용",
                "score": 1 - i * 0.1,
            }
            for i in range(5)
        ]

        selected = select_web_evidence(
            results,
            query="테스트",
            intent="GENERAL",
            entity=None,
            limit=3,
        )

        self.assertEqual(
            len(selected),
            3,
        )


class CurrentFactSubjectGateTest(unittest.TestCase):
    """
    2026-09-02(1-B): CURRENT_FACT(날씨 등) 질의에서 entity가 있어도 hard
    filter가 없어서, "강남구 날씨"를 물었는데 Northern California weather/
    Geneva Watch 행사처럼 주제/지역이 완전히 무관한 결과가 그대로
    selected_results에 남던 문제. PROFILE의 exact-string hard filter와는
    분리된, entity를 단어 단위로 비교하는 관대한 게이트로 고친다.
    """

    def test_completely_unrelated_results_are_removed_single_word_entity(self):
        results = [
            {
                "title": "Northern California weather forecast",
                "url": "https://example.com/us1",
                "content": "Rain expected in California today.",
                "score": 0.72,
            },
            {
                "title": "Geneva Watch 행사 안내",
                "url": "https://example.com/ch1",
                "content": "Geneva Watch 2026 행사가 개최됩니다.",
                "score": 0.55,
            },
            {
                "title": "강남구 오늘 날씨 예보",
                "url": "https://example.com/kr1",
                "content": "강남구 오늘 낮 최고기온 29도, 소나기 가능성.",
                "score": 0.30,
            },
        ]

        selected = select_web_evidence(
            results,
            query="오늘 강남구 날씨는 어때?",
            intent="CURRENT_FACT",
            entity="강남구",
            limit=3,
        )

        titles = [r["title"] for r in selected]
        self.assertEqual(titles, ["강남구 오늘 날씨 예보"])

    def test_multi_word_entity_does_not_require_exact_combined_string(self):
        results = [
            {
                "title": "US weather update",
                "url": "https://example.com/us2",
                "content": "Weather across the United States today.",
                "score": 0.68,
            },
            {
                "title": "서울특별시 대기환경정보",
                "url": "https://example.com/air",
                "content": "서울시 미세먼지 및 대기질 정보를 제공합니다.",
                "score": 0.40,
            },
            {
                "title": "강남구 오늘 기온 안내",
                "url": "https://example.com/kr2",
                "content": "강남구 오늘 기온은 28도, 오후 소나기.",
                "score": 0.28,
            },
            {
                "title": "서울 강남구 오늘 날씨",
                "url": "https://example.com/kr3",
                "content": "서울 강남구 지역 오늘 날씨는 흐림, 강수확률 60%.",
                "score": 0.33,
            },
        ]

        selected = select_web_evidence(
            results,
            query="오늘 서울 강남구 날씨는 어때?",
            intent="CURRENT_FACT",
            entity="서울 강남구",
            limit=3,
        )

        titles = [r["title"] for r in selected]

        # 미국 weather는 entity 단어("서울"/"강남구")가 전혀 없어 제거된다.
        self.assertNotIn("US weather update", titles)

        # entity 전체 문자열("서울 강남구")이 그대로 없어도 "강남구"만
        # 있으면 이 gate에서는 제거되지 않아야 한다.
        self.assertIn("강남구 오늘 기온 안내", titles)

        # "서울"만 있는 "서울특별시 대기환경정보"도 이 gate 단계에서는
        # 무조건 제거하지 않는다(지역만 맞고 주제가 달라도 이 gate의
        # 책임이 아님 - 아래 순위 확인이 실제 weather 우선순위를 본다).
        self.assertIn("서울특별시 대기환경정보", titles)

        # 다만 실제 날씨 기사가 (lexical overlap 덕분에) 대기환경정보보다
        # 우선순위가 높아야 한다.
        self.assertLess(
            titles.index("서울 강남구 오늘 날씨"),
            titles.index("서울특별시 대기환경정보"),
        )

    def test_profile_hard_filter_is_unaffected_by_current_fact_gate(self):
        # PROFILE의 기존 exact-string hard filter 동작이 그대로여야 한다 -
        # 이 gate는 CURRENT_FACT 전용이고 PROFILE에는 적용되지 않는다.
        results = [
            {
                "title": "손흥민 관련 기사",
                "url": "https://news.example/a",
                "content": "손흥민의 이번 시즌 활약",
                "score": 0.9,
            },
            {
                "title": "홍명보 감독 인터뷰",
                "url": "https://news.example/b",
                "content": "홍명보 감독의 전술 이야기",
                "score": 0.95,
            },
        ]

        selected = select_web_evidence(
            results,
            query="손흥민 프로필 알려줘",
            intent="PROFILE",
            entity="손흥민",
            limit=3,
        )

        titles = [r["title"] for r in selected]
        self.assertNotIn("홍명보 감독 인터뷰", titles)
        self.assertIn("손흥민 관련 기사", titles)

    def test_entity_particle_is_stripped_before_token_matching(self):
        # edge case 1: entity="대한민국의"(조사 포함) - 결과 문서의
        # "대한민국"(조사 없음)과 문자열이 안 맞아 정상 evidence가
        # 제거되면 안 된다.
        results = [
            {
                "title": "대한민국 오늘 날씨",
                "url": "https://example.com/kr",
                "content": "전국 곳곳 대체로 맑음.",
                "score": 0.4,
            },
        ]

        selected = select_web_evidence(
            results,
            query="오늘 대한민국의 날씨 정보에 대해서 설명해줘",
            intent="CURRENT_FACT",
            entity="대한민국의",
            limit=3,
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["title"], "대한민국 오늘 날씨")

    def test_generic_time_modifier_in_entity_is_not_a_match_signal(self):
        # edge case 2: entity="손흥민 최근"("최근"이 search_plan.py의
        # subject 캡처 특성으로 섞여 들어온 경우) - "최근" 단어 하나만
        # 겹친다고 완전히 무관한 결과("최근 미국 증시 전망")까지
        # 통과시키면 안 된다.
        results = [
            {
                "title": "손흥민 최근 경기 기록",
                "url": "https://example.com/a",
                "content": "손흥민의 최근 5경기 활약상 정리.",
                "score": 0.5,
            },
            {
                "title": "최근 미국 증시 전망",
                "url": "https://example.com/b",
                "content": "다우존스 지수 최근 동향 분석.",
                "score": 0.9,
            },
            {
                "title": "손흥민 경기 결과",
                "url": "https://example.com/c",
                "content": "손흥민이 출전한 경기의 결과.",
                "score": 0.3,
            },
        ]

        selected = select_web_evidence(
            results,
            query="손흥민 최근 경기 결과는?",
            intent="CURRENT_FACT",
            entity="손흥민 최근",
            limit=3,
        )

        titles = [r["title"] for r in selected]
        self.assertNotIn("최근 미국 증시 전망", titles)
        self.assertIn("손흥민 최근 경기 기록", titles)
        self.assertIn("손흥민 경기 결과", titles)


class QueryTokenParticleNormalizationTest(unittest.TestCase):
    """
    2026-09-02(1-B): _query_tokens()가 "날씨는"/"주가는"/"가격이"처럼
    조사가 붙은 토큰을 그대로 써서, 실제 결과 본문의 "날씨"/"주가"/"가격"과
    문자열이 안 맞아 lexical overlap 점수가 무력화되던 문제.
    """

    def test_common_particles_are_stripped(self):
        self.assertIn("날씨", _query_tokens("날씨는"))
        self.assertIn("주가", _query_tokens("주가는"))
        self.assertIn("가격", _query_tokens("가격이"))

    def test_short_base_word_is_not_over_stripped(self):
        # 벗겨낸 뒤 2자 미만이 되면 원래 토큰을 그대로 유지해야 한다.
        tokens = _query_tokens("평가가 필요해")
        # "평가"(2자)에서 "가"를 벗기면 "평"(1자)이 되어 최소 길이
        # 조건(>=2)에 걸리므로 "평가"가 그대로 유지돼야 한다.
        self.assertIn("평가", tokens)

    def test_lexical_overlap_bonus_uses_normalized_tokens(self):
        results = [
            {
                "title": "무관한 기사",
                "url": "https://example.com/a",
                "content": "이 기사는 질문과 관련이 없습니다.",
                "score": 0.5,
            },
            {
                "title": "강남구 오늘 날씨 예보",
                "url": "https://example.com/b",
                "content": "강남구 오늘 날씨는 흐림.",
                "score": 0.5,
            },
        ]

        selected = select_web_evidence(
            results,
            query="오늘 강남구 날씨는 어때?",
            intent="GENERAL",
            entity=None,
            limit=1,
        )

        self.assertEqual(selected[0]["title"], "강남구 오늘 날씨 예보")


if __name__ == "__main__":
    unittest.main()
