package com.promptune.service;

import com.promptune.dto.PipelineDtos.DiagnoseResult;
import com.promptune.dto.PipelineDtos.RecommendResult;
import com.promptune.domain.PersonalizationScore;
import com.promptune.repository.PersonalizationScoreRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.*;

@Service
public class RecommendService {

    @Autowired
    private PersonalizationScoreRepository scoreRepository;

    @Autowired
    private RetrievalPatternService retrievalPatternService;

    public RecommendResult select(DiagnoseResult diagnose, Long userId) {
        List<String> missing = new ArrayList<>();
        diagnose.missing().forEach((el, v) -> { if (v == 1) missing.add(el); });

        // 2026-09-02: 습관학습 3단계 - dominantRoute는 DB 조회라, sort()의
        // 비교 함수 안에서 부르면 같은 쿼리가 반복 실행된다. 정렬 시작 전
        // 딱 한 번만 조회해서 재사용.
        String dominantRoute = retrievalPatternService.dominantRoute(userId);

        missing.sort((a, b) -> Double.compare(
                getPriorityScore(userId, b, dominantRoute),
                getPriorityScore(userId, a, dominantRoute)));
        return new RecommendResult(missing.stream().limit(3).toList());
    }

    private double getPriorityScore(Long userId, String element, String dominantRoute) {
        // (P1-3) 이전에는 dismissCount / (accept+dismiss) - 즉 "거절 비율"을
        // 내림차순 정렬해서, 사용자가 자주 거절한 요소가 오히려 먼저
        // 추천되는 역방향 개인화 버그가 있었다. "자주 accept한 요소를
        // 우선한다"는 제품 의도에 맞게 accept 비율로 바꾼다.
        // +1/+2 smoothing은 기록이 적거나 없는 요소가 0 또는 1 같은
        // 극단값으로 쏠리지 않게 하고, accept=dismiss=0인 신규 사용자도
        // 항상 0.5(중립, 기존 기본값과 동일)로 시작하게 한다 - 분모가
        // 항상 2 이상이라 나눗셈 예외도 없다.
        double base = scoreRepository.findByUserIdAndElement(userId, element)
                .map(s -> (s.getAcceptCount() + 1.0) / (s.getAcceptCount() + s.getDismissCount() + 2.0))
                .orElse(0.5);

        // 2026-09-02: 습관학습 3단계 - 평소 내부문서를 자주 쓰는 사용자는
        // CONTEXT 추천 우선순위를 살짝 올림. 확정 규칙이 아니라 약한 가산점
        // 수준으로만 반영 (기존 accept/dismiss 학습이 여전히 주된 신호).
        if ("CONTEXT".equals(element) && "internal_rag".equals(dominantRoute)) {
            base += 0.15;
        }

        return base;
    }
}
