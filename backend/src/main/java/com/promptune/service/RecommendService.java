package com.promptune.service;

import com.promptune.dto.PipelineDtos.DiagnoseResult;
import com.promptune.dto.PipelineDtos.RecommendResult;
import org.springframework.stereotype.Service;
import java.util.*;

/**
 * 6번 수정요소 선정.
 * 진단에서 '보완 필요(1)'로 나온 요소 중, 점수 상위 1~3개를 추천 대상으로 선정.
 *
 * TODO(형기): 지금은 단순 우선순위 mock. 실제로는 과거 Tab/Esc 기록 +
 *   MS365 업무 맥락을 더한 점수 로직으로 교체. RecommendResult 형식 유지.
 */
@Service
public class RecommendService {

    // 요소별 기본 우선순위 (mock). 값이 클수록 먼저 추천.
    private static final Map<String, Integer> PRIORITY = Map.of(
            "TASK", 100, "AUDIENCE", 80, "CONTEXT", 70, "FORMAT", 60,
            "TONE", 50, "LENGTH", 40, "CONSTRAINT", 30, "EXAMPLE", 20);

    public RecommendResult select(DiagnoseResult diagnose) {
        List<String> missing = new ArrayList<>();
        diagnose.missing().forEach((el, v) -> { if (v == 1) missing.add(el); });
        // 우선순위 내림차순 정렬 후 상위 3개
        missing.sort((a, b) -> PRIORITY.getOrDefault(b, 0) - PRIORITY.getOrDefault(a, 0));
        return new RecommendResult(missing.stream().limit(3).toList());
    }
}
