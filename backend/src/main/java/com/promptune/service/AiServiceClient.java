package com.promptune.service;

import com.promptune.dto.PipelineDtos.DiagnoseResult;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Map;

@Service
public class AiServiceClient {

    private final RestClient client;

    public AiServiceClient(
            RestClient.Builder builder,
            @Value("${ai.service.url:http://localhost:8000}") String baseUrl) {
        this.client = builder
                .baseUrl(baseUrl)
                .build();
    }

    public DiagnoseResult diagnose(String text) {
        return client.post()
                .uri("/api/ai/diagnose")
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.APPLICATION_JSON)
                .body(Map.of("text", text))
                .retrieve()
                .body(DiagnoseResult.class);
    }

    public Map generate(String prompt, String taskType, boolean useWebSearch) {
        return client.post()
                .uri("/api/ai/generate")
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.APPLICATION_JSON)
                .body(Map.of(
                        "prompt", prompt,
                        "task_type", taskType,
                        "use_web_search", useWebSearch))
                .retrieve()
                .body(Map.class);
    }
}