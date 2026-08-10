package com.promptune.controller;

import com.promptune.dto.PipelineDtos.*;
import com.promptune.service.*;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

/**
 * 파이프라인 오케스트레이터.
 * 흐름도의 백엔드 단계(3,4,6,11,12,16)를 지휘하고, AI 단계는 ai-service 호출.
 */
@RestController
@RequestMapping("/api")
public class PipelineController {

    private final GateService gate;
    private final AiServiceClient ai;
    private final RecommendService recommend;
    private final GraphMockService graph;

    public PipelineController(GateService gate, AiServiceClient ai,
                              RecommendService recommend, GraphMockService graph) {
        this.gate = gate; this.ai = ai;
        this.recommend = recommend; this.graph = graph;
    }

    /**
     * 2번: 프롬프트 분석 (입력 중단 시 프론트가 호출).
     * 흐름: 3게이트 → 5진단(AI) → 6추천선정
     */
    @PostMapping("/analyze")
    public AnalyzeResponse analyze(@RequestBody AnalyzeRequest req) {
        // 3번 게이트
        GateResult g = gate.check(req.text());
        if (!g.passed()) {
            return new AnalyzeResponse(g, null, null);
        }
        // 5번 진단 (ai-service 호출)
        DiagnoseResult d = ai.diagnose(req.text());
        // 6번 수정요소 선정
        RecommendResult r = recommend.select(d);
        return new AnalyzeResponse(g, d, r);
    }

    /**
     * 11번: 실행 (Enter).
     * 흐름: 12분류 → (13검색) → 14생성(AI) → 16저장
     */
    @PostMapping("/execute")
    public Map<String, Object> execute(@RequestBody ExecuteRequest req) {
        // 12번 분류 + 14번 생성 (진단으로 taskType 파악)
        DiagnoseResult d = ai.diagnose(req.finalPrompt());
        Map result = ai.generate(req.finalPrompt(), d.taskType(), false);
        // 16번 행동 저장 (mock — 실제론 DB)
        // TODO(형기): 행동 로그를 PostgreSQL에 저장, 개인화 점수 갱신
        return Map.of(
                "taskType", d.taskType(),
                "needsInternalDocs", d.needsInternalDocs(),
                "result", result
        );
    }

    /** 0번: 사용자 맥락 (로그인 후 사전 조회) */
    @GetMapping("/context/{userId}")
    public Map<String, Object> context(@PathVariable Long userId) {
        return Map.of(
                "firstVisit", graph.isFirstVisit(userId),
                "workContext", graph.getUserContext(userId)
        );
    }
}
