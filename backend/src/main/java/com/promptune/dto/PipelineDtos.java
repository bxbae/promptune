package com.promptune.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * 백엔드 파이프라인 DTO 모음.
 * 프론트 ↔ 백엔드 ↔ ai-service 간 데이터 형식(계약서).
 * ai-service는 snake_case, 백엔드/프론트는 camelCase → @JsonProperty로 매핑.
 */
public class PipelineDtos {

    public record AnalyzeRequest(String text, Long userId) {}

    public record GateResult(boolean passed, String reason) {}

    // 5번 ai-service /diagnose 응답. snake_case JSON을 camelCase로 매핑.
    public record DiagnoseResult(
            Map<String, Integer> missing,
            @JsonProperty("task_type") String taskType,
            List<Map<String, String>> typos,
            @JsonProperty("needs_internal_docs") boolean needsInternalDocs
    ) {}

    public record RecommendResult(List<String> targetElements) {}

    public record AnalyzeResponse(
            GateResult gate,
            DiagnoseResult diagnose,
            RecommendResult recommend
    ) {}

    public record ExecuteRequest(String finalPrompt, Long userId) {}

    public record ClassifyResult(
            @JsonProperty("task_type") String taskType,
            @JsonProperty("needs_internal_docs") boolean needsInternalDocs) {}

    public record BehaviorLog(Long userId, String action, String element) {}
}
