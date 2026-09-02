import unittest

from app.services.retrieval.evidence_selector import (
    select_web_evidence,
    _query_tokens,
    _score_breakdown,
    _normalize,
    _authority_bonus,
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


class EntityScoringConsistencyTest(unittest.TestCase):
    """
    2026-09-02(1-B): entity 보너스/페널티가 여전히 entity "전체 문자열"
    exact match였다(gate는 단어 단위인데 scoring은 문자열 단위 - 기준
    불일치). entity="서울 강남구"인데 정상 기사가 "강남구"만 쓰면, gate는
    통과시키지만 scoring에서는 "서울강남구" 전체가 없다는 이유로 오답과
    똑같이 페널티를 받아 사실상 상수처럼 작동했다. 단어 단위 부분 매치
    비율로 바꿔서 고친다 - 기존 +0.20/-0.08 범위 자체는 바꾸지 않는다.

    이 새 로직은 CURRENT_FACT/FINANCE에만 적용되고, PROFILE/RESEARCH 등
    나머지 intent는 아래 PreExistingIntentScoringUnchangedTest가
    "이전 공식과 final_score가 완전히 같음"을 직접 검증한다.
    """

    def test_partial_entity_match_gets_partial_bonus_not_full_penalty(self):
        item_full_match = {
            "title": "서울 강남구 오늘 날씨",
            "url": "https://example.com/a",
            "content": "서울 강남구 지역 오늘 날씨는 흐림.",
            "score": 0.3,
        }
        item_partial_match = {
            "title": "강남구 오늘 기온 안내",
            "url": "https://example.com/b",
            "content": "강남구 오늘 기온은 28도.",
            "score": 0.3,
        }
        item_no_match = {
            "title": "미국 weather",
            "url": "https://example.com/c",
            "content": "Weather across the United States.",
            "score": 0.3,
        }

        full = _score_breakdown(
            item_full_match,
            query="오늘 서울 강남구 날씨는 어때?",
            intent="CURRENT_FACT",
            entity="서울 강남구",
        )
        partial = _score_breakdown(
            item_partial_match,
            query="오늘 서울 강남구 날씨는 어때?",
            intent="CURRENT_FACT",
            entity="서울 강남구",
        )
        none_ = _score_breakdown(
            item_no_match,
            query="오늘 서울 강남구 날씨는 어때?",
            intent="CURRENT_FACT",
            entity="서울 강남구",
        )

        # 전체 일치(0.20) > 부분 일치(0 ~ 0.20 사이) > 불일치(-0.08).
        self.assertEqual(full["entity_bonus"], 0.20)
        self.assertGreater(partial["entity_bonus"], 0)
        self.assertLess(partial["entity_bonus"], 0.20)
        self.assertEqual(none_["entity_bonus"], -0.08)

    def test_single_word_entity_bonus_is_unchanged_binary_behavior(self):
        # PROFILE 등 단어 1개짜리 entity는 부분 매치가 있을 수 없으므로
        # (0개 아니면 1개), 기존 이진 +0.20/-0.08 동작과 완전히 동일해야
        # 한다 - PROFILE 회귀가 없다는 근거.
        match = _score_breakdown(
            {"title": "BTS 경제적 영향", "url": "https://x.com/a", "content": "BTS의 경제 기여", "score": 0.5},
            query="BTS가 국가에 기여한 점",
            intent="RESEARCH",
            entity="BTS",
        )
        mismatch = _score_breakdown(
            {"title": "다른 아이돌", "url": "https://x.com/b", "content": "다른 그룹 활동", "score": 0.5},
            query="BTS가 국가에 기여한 점",
            intent="RESEARCH",
            entity="BTS",
        )
        self.assertEqual(match["entity_bonus"], 0.20)
        self.assertEqual(mismatch["entity_bonus"], -0.08)


class PreExistingIntentScoringUnchangedTest(unittest.TestCase):
    """
    2026-09-02(1-B, scope 최소화): 이번 작업 범위는 CURRENT_FACT/FINANCE
    relevance 개선이다 - PROFILE/RESEARCH/GENERAL 등 다른 intent의
    scoring은 한 글자도 안 바뀌어야 한다. entity_match_ratio/topic_tokens
    분리는 CURRENT_FACT/FINANCE에서만 켜지므로, 그 외 intent는 여전히
    (a) entity 전체 문자열 exact match, (b) query 전체 토큰(_query_tokens)
    lexical overlap을 쓴다 - 이 두 가지를 1-B 이전 공식 그대로 직접
    재구현해서 _score_breakdown()의 final_score와 완전히 같은지 비교한다.
    """

    @staticmethod
    def _pre_1b_score(item, *, query, intent, entity):
        tavily_score = float(item.get("score") or 0.0)
        combined = f"{item.get('title', '')} {item.get('content', '')}"
        final_score = tavily_score

        if entity:
            normalized_entity = _normalize(entity)
            normalized_result = _normalize(combined)
            if normalized_entity and normalized_entity in normalized_result:
                final_score += 0.20
            else:
                final_score -= 0.08

        tokens = _query_tokens(query)
        if tokens:
            lowered = combined.lower()
            matched = sum(1 for token in tokens if token in lowered)
            final_score += min(matched * 0.03, 0.15)

        final_score += _authority_bonus(str(item.get("url") or ""), intent)
        return final_score

    def test_profile_final_score_matches_pre_1b_formula_exactly(self):
        cases = [
            (
                {"title": "BTS 경제적 영향", "url": "https://news.example/b", "content": "BTS의 국가 경제 기여", "score": 0.82},
                "BTS가 국가에 기여한 점",
                "PROFILE",
                "BTS",
            ),
            (
                {"title": "다른 아이돌 해외 활동", "url": "https://news.example/a", "content": "다른 그룹의 활동", "score": 0.90},
                "BTS가 국가에 기여한 점",
                "PROFILE",
                "BTS",
            ),
        ]
        for item, query, intent, entity in cases:
            with self.subTest(title=item["title"]):
                old = self._pre_1b_score(item, query=query, intent=intent, entity=entity)
                new = _score_breakdown(item, query=query, intent=intent, entity=entity)["final_score"]
                self.assertAlmostEqual(old, new)

    def test_research_final_score_matches_pre_1b_formula_exactly(self):
        cases = [
            (
                {"title": "BTS 경제 효과 블로그", "url": "https://blog.example/a", "content": "BTS 경제 효과", "score": 0.85},
                "BTS 국가 기여",
                "RESEARCH",
                "BTS",
            ),
            (
                {"title": "BTS 문화경제 연구", "url": "https://example.go.kr/report", "content": "BTS 문화 경제 기여 연구", "score": 0.75},
                "BTS 국가 기여",
                "RESEARCH",
                "BTS",
            ),
        ]
        for item, query, intent, entity in cases:
            with self.subTest(title=item["title"]):
                old = self._pre_1b_score(item, query=query, intent=intent, entity=entity)
                new = _score_breakdown(item, query=query, intent=intent, entity=entity)["final_score"]
                self.assertAlmostEqual(old, new)

    def test_general_intent_with_no_entity_matches_pre_1b_formula(self):
        item = {"title": "강남구 오늘 날씨 예보", "url": "https://example.com/b", "content": "강남구 오늘 날씨는 흐림.", "score": 0.5}
        query = "오늘 강남구 날씨는 어때?"
        old = self._pre_1b_score(item, query=query, intent="GENERAL", entity=None)
        new = _score_breakdown(item, query=query, intent="GENERAL", entity=None)["final_score"]
        self.assertAlmostEqual(old, new)


class FinanceScoringStructureTest(unittest.TestCase):
    """
    2026-09-02(1-B): FINANCE에는 subject hard gate를 확장하지 않는다
    ("원달러" vs "USD/KRW", "아이폰" vs "iPhone"처럼 정상 결과가 다른
    표기를 쓸 수 있어 hard gate가 false negative를 낼 위험이 있음).
    scoring 구조(entity/topic 분리)만 적용되고, 결과가 절대 제거되지
    않는지 확인한다.
    """

    def test_finance_query_has_no_hard_gate_removal(self):
        results = [
            {"title": "삼성전자 주가 기사", "url": "https://x.com/a", "content": "삼성전자 오늘 주가는 7만원대.", "score": 0.5},
            {"title": "삼성전자 채용 기사", "url": "https://x.com/b", "content": "삼성전자 신입 공채 시작.", "score": 0.7},
            {"title": "미국 증시 기사", "url": "https://x.com/c", "content": "다우존스 지수 상승 마감.", "score": 0.6},
        ]

        selected = select_web_evidence(
            results,
            query="삼성전자 주가는?",
            intent="FINANCE",
            entity="삼성전자",
            limit=3,
        )

        # hard gate가 없으므로 entity와 무관한 "미국 증시 기사"도
        # 완전히 제거되지는 않는다(순위만 scoring에 맡김).
        titles = [r["title"] for r in selected]
        self.assertEqual(len(titles), 3)

    def test_synonym_denominated_result_is_not_hard_rejected_usd_krw(self):
        # entity="원달러"인데 실제 정상 결과가 "USD/KRW" 표기만 쓰는 경우 -
        # hard gate가 없으므로 제거되면 안 된다.
        results = [
            {"title": "USD/KRW 환율 동향", "url": "https://x.com/a", "content": "USD/KRW 1,320원대 등락.", "score": 0.4},
        ]
        selected = select_web_evidence(
            results,
            query="원달러 환율은?",
            intent="FINANCE",
            entity="원달러",
            limit=3,
        )
        self.assertEqual(len(selected), 1)

    def test_synonym_denominated_result_is_not_hard_rejected_iphone(self):
        # entity="아이폰"인데 실제 결과가 "iPhone" 영문 표기만 쓰는 경우 -
        # hard gate가 없으므로 제거되면 안 된다.
        results = [
            {"title": "iPhone 17 출고가 공개", "url": "https://x.com/a", "content": "iPhone 17 가격은 129만원부터.", "score": 0.4},
        ]
        selected = select_web_evidence(
            results,
            query="아이폰 가격이 얼마야?",
            intent="FINANCE",
            entity="아이폰",
            limit=3,
        )
        self.assertEqual(len(selected), 1)


class ScoreBreakdownObservabilityTest(unittest.TestCase):
    """
    2026-09-02(1-B): 운영 로그를 새로 늘리지 않고, 테스트에서 각 결과의
    점수 구성 요소(tavily_score/entity_bonus/topic_overlap/
    authority_bonus/final_score)를 근거 있게 확인할 수 있는 구조.
    """

    def test_breakdown_components_sum_to_final_score(self):
        item = {
            "title": "강남구 오늘 날씨 예보",
            "url": "https://example.com/kr1",
            "content": "강남구 오늘 낮 최고기온 29도.",
            "score": 0.25,
        }
        breakdown = _score_breakdown(
            item,
            query="오늘 강남구 날씨는 어때?",
            intent="CURRENT_FACT",
            entity="강남구",
        )

        for key in ("tavily_score", "entity_bonus", "topic_overlap", "authority_bonus", "final_score"):
            self.assertIn(key, breakdown)

        self.assertAlmostEqual(
            breakdown["tavily_score"]
            + breakdown["entity_bonus"]
            + breakdown["topic_overlap"]
            + breakdown["authority_bonus"],
            breakdown["final_score"],
        )


if __name__ == "__main__":
    unittest.main()
