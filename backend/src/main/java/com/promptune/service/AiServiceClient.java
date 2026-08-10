package com.promptune.service;

import com.promptune.dto.PipelineDtos.DiagnoseResult;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import java.util.Map;

/**
 * ai-service(FastAPI) 호출 클라이언트.
 * 백엔드는 오케스트레이터로서 AI 단계(5,7,13,14,15)를 HTTP로 호출한다.
 */
@Service
public class AiServiceClient {

    private final RestClient client;

    public AiServiceClient(@Value("${ai.service.url:http://localhost:8000}") String baseUrl) {
        this.client = RestClient.builder().baseUrl(baseUrl).build();
    }

    // 5번 통합 진단 호출
    public DiagnoseResult diagnose(String text) {
        return client.post()
                .uri("/api/ai/diagnose")
                .body(Map.of("text", text))
                .retrieve()
                .body(DiagnoseResult.class);
    }

    // 14번 최종 답변 생성 호출
    public Map generate(String prompt, String taskType, boolean useWebSearch) {
        return client.post()
                .uri("/api/ai/generate")
                .body(Map.of("prompt", prompt, "task_type", taskType,
                        "use_web_search", useWebSearch))
                .retrieve()
                .body(Map.class);
    }
}
