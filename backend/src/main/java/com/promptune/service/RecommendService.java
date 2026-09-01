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

    public RecommendResult select(DiagnoseResult diagnose, Long userId) {
        List<String> missing = new ArrayList<>();
        diagnose.missing().forEach((el, v) -> { if (v == 1) missing.add(el); });
        missing.sort((a, b) -> Double.compare(getPriorityScore(userId, b), getPriorityScore(userId, a)));
        return new RecommendResult(missing.stream().limit(3).toList());
    }

    private double getPriorityScore(Long userId, String element) {
        // (P1-3) 이전에는 dismissCount / (accept+dismiss) - 즉 "거절 비율"을
        // 내림차순 정렬해서, 사용자가 자주 거절한 요소가 오히려 먼저
        // 추천되는 역방향 개인화 버그가 있었다. "자주 accept한 요소를
        // 우선한다"는 제품 의도에 맞게 accept 비율로 바꾼다.
        // +1/+2 smoothing은 기록이 적거나 없는 요소가 0 또는 1 같은
        // 극단값으로 쏠리지 않게 하고, accept=dismiss=0인 신규 사용자도
        // 항상 0.5(중립, 기존 기본값과 동일)로 시작하게 한다 - 분모가
        // 항상 2 이상이라 나눗셈 예외도 없다.
        return scoreRepository.findByUserIdAndElement(userId, element)
                .map(s -> (s.getAcceptCount() + 1.0) / (s.getAcceptCount() + s.getDismissCount() + 2.0))
                .orElse(0.5);
    }
}