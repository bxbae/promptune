package com.promptune.service;

import com.promptune.dto.PipelineDtos.DiagnoseResult;
import com.promptune.dto.PipelineDtos.SuggestResult;
import com.promptune.domain.ModelUsageLog;
import com.promptune.repository.ModelUsageLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import java.net.http.HttpClient;
import java.util.Map;
import java.util.List;

@Service
public class AiServiceClient {

    private final RestClient client;

    @Autowired
    private ModelUsageLogRepository logRepository;

    public AiServiceClient(@Value("${ai.service.url:http://localhost:8000}") String baseUrl) {
        HttpClient httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .build();

        JdkClientHttpRequestFactory requestFactory = new JdkClientHttpRequestFactory(httpClient);

        this.client = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(requestFactory)
                .build();
    }

    public DiagnoseResult diagnose(String text) {
        long start = System.currentTimeMillis();
        try {
            DiagnoseResult result = client.post()
                    .uri("/api/ai/diagnose")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of("text", text))
                    .retrieve()
                    .body(DiagnoseResult.class);
            log("ai-service", "/api/ai/diagnose", start, "success");
            return result;
        } catch (Exception e) {
            log("ai-service", "/api/ai/diagnose", start, "error");
            throw e;
        }
    }

    public SuggestResult suggest(
            String text,
            List<String> targetElements) {
        long start = System.currentTimeMillis();

        try {
            SuggestResult result = client.post()
                    .uri("/api/ai/suggest")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of(
                            "text", text,
                            "target_elements", targetElements))
                    .retrieve()
                    .body(SuggestResult.class);

            log("ai-service", "/api/ai/suggest", start, "success");

            return result;
        } catch (Exception e) {
            log("ai-service", "/api/ai/suggest", start, "error");
            throw e;
        }
    }

    public Map generate(String prompt, String taskType, boolean useWebSearch) {
        long start = System.currentTimeMillis();
        try {
            Map result = client.post()
                    .uri("/api/ai/generate")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of(
                            "prompt", prompt,
                            "task_type", taskType,
                            "use_web_search", useWebSearch))
                    .retrieve()
                    .body(Map.class);
            log("ai-service", "/api/ai/generate", start, "success");
            return result;
        } catch (Exception e) {
            log("ai-service", "/api/ai/generate", start, "error");
            throw e;
        }
    }

    public String summarizeTitle(String text) {
        long start = System.currentTimeMillis();
        try {
            Map result = client.post()
                    .uri("/api/ai/summarize-title")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of("text", text))
                    .retrieve()
                    .body(Map.class);
            log("ai-service", "/api/ai/summarize-title", start, "success");
            return (String) result.get("title");
        } catch (Exception e) {
            log("ai-service", "/api/ai/summarize-title", start, "error");
            return null;   // 실패해도 전체 흐름은 안 끊기게, null 반환
        }
    }

    private void log(String provider, String endpoint, long startTime, String status) {
        int elapsed = (int) (System.currentTimeMillis() - startTime);
        logRepository.save(new ModelUsageLog(provider, endpoint, elapsed, status));
    }
}