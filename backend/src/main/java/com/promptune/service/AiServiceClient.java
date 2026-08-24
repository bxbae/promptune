package com.promptune.service;

import com.promptune.dto.PipelineDtos.DiagnoseResult;
import com.promptune.dto.PipelineDtos.ImprovePromptResult;
import com.promptune.dto.PipelineDtos.PromptRuleResult;
import com.promptune.dto.PipelineDtos.SuggestResult;
import com.promptune.domain.ModelUsageLog;
import com.promptune.repository.ModelUsageLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.multipart.MultipartFile;
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

    public PromptRuleResult promptRule(
            String text,
            Map<String, Integer> missing,
            String taskType,
            String speed,
            String detail,
            String preserve) {

        long start = System.currentTimeMillis();

        try {
            PromptRuleResult result = client.post()
                    .uri("/api/ai/prompt-rule")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of(
                            "text", text,
                            "missing", missing,
                            "task_type", taskType,
                            "preference", Map.of(
                                    "speed", speed,
                                    "detail", detail,
                                    "preserve", preserve)))
                    .retrieve()
                    .body(PromptRuleResult.class);

            log("ai-service", "/api/ai/prompt-rule", start, "success");

            return result;
        } catch (Exception e) {
            log("ai-service", "/api/ai/prompt-rule", start, "error");
            throw e;
        }
    }

    public ImprovePromptResult improvePrompt(
            String text,
            String taskType,
            String speed,
            String detail,
            String preserve,
            PromptRuleResult promptRule) {

        long start = System.currentTimeMillis();

        try {
            ImprovePromptResult result = client.post()
                    .uri("/api/ai/improve-prompt")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of(
                            "text", text,
                            "task_type", taskType,
                            "preference", Map.of(
                                    "speed", speed,
                                    "detail", detail,
                                    "preserve", preserve),
                            "prompt_rule", promptRule))
                    .retrieve()
                    .body(ImprovePromptResult.class);

            log("ai-service", "/api/ai/improve-prompt", start, "success");

            return result;
        } catch (Exception e) {
            log("ai-service", "/api/ai/improve-prompt", start, "error");
            throw e;
        }
    }

    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> retrieve(String query, Long ownerUserId, int topK) {
        long start = System.currentTimeMillis();
        try {
            Map result = client.post()
                    .uri("/api/ai/retrieve")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of(
                            "query", query,
                            "owner_user_id", ownerUserId,
                            "top_k", topK))
                    .retrieve()
                    .body(Map.class);

            log("ai-service", "/api/ai/retrieve", start, "success");
            Object documents = result != null ? result.get("documents") : null;
            return documents instanceof List<?> ? (List<Map<String, Object>>) documents : List.of();
        } catch (Exception e) {
            log("ai-service", "/api/ai/retrieve", start, "error");
            throw e;
        }
    }

    // 문서 업로드 직후 ai-service에 청킹·임베딩 요청 (document_chunks 채우기)
    public Map<String, Object> indexDocument(Long documentId, Long ownerUserId, String fileType, MultipartFile file) {
        long start = System.currentTimeMillis();
        try {
            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("document_id", documentId);
            body.add("owner_user_id", ownerUserId);
            body.add("file_type", fileType);
            body.add("file", file.getResource()); // 원본 파일을 그대로 전달 (S3 재조회 없음)

            Map result = client.post()
                    .uri("/api/ai/index-document")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .body(Map.class);

            log("ai-service", "/api/ai/index-document", start, "success");
            return result;
        } catch (Exception e) {
            log("ai-service", "/api/ai/index-document", start, "error");
            throw e;
        }
    }

    // Retrieval Router/Orchestrator 연동 (승연님 PR #67) — 내부문서/웹검색 여부까지 통째로 판단·실행
    public Map<String, Object> retrievalExecute(String query, Long ownerUserId, int topK) {
        long start = System.currentTimeMillis();
        try {
            Map<String, Object> body = Map.of(
                    "query", query,
                    "owner_user_id", ownerUserId,
                    "top_k", topK);
            Map result = client.post()
                    .uri("/api/ai/retrieval-execute")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(Map.class);

            log("ai-service", "/api/ai/retrieval-execute", start, "success");
            return result;
        } catch (Exception e) {
            log("ai-service", "/api/ai/retrieval-execute", start, "error");
            throw e;
        }
    }

    public Map generate(
            String prompt,
            String taskType,
            List<Map<String, Object>> documents,
            List<Map<String, Object>> webResults,
            Map<String, String> userContext,
            Map<String, String> preference) {
        long start = System.currentTimeMillis();

        try {
            Map result = client.post()
                    .uri("/api/ai/generate")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of(
                            "prompt", prompt,
                            "task_type", taskType,
                            "documents", documents,
                            "web_results", webResults,
                            "user_context", userContext,
                            "preference", preference))
                    .retrieve()
                    .body(Map.class);

            log("ai-service", "/api/ai/generate", start, "success");
            return result;
        } catch (Exception e) {
            log("ai-service", "/api/ai/generate", start, "error");
            throw e;
        }
    }

    // 기존 호출부 호환용
    public Map generate(
            String prompt,
            String taskType,
            List<Map<String, Object>> documents,
            List<Map<String, Object>> webResults,
            boolean useWebSearch) {

        return generate(
                prompt,
                taskType,
                documents,
                webResults,
                Map.of(),
                Map.of());
    }

    public Map validate(String original, String generated) {
        long start = System.currentTimeMillis();
        try {
            Map result = client.post()
                    .uri("/api/ai/validate")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of(
                            "original", original,
                            "generated", generated))
                    .retrieve()
                    .body(Map.class);

            log("ai-service", "/api/ai/validate", start, "success");
            return result;
        } catch (Exception e) {
            log("ai-service", "/api/ai/validate", start, "error");
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
            return null; // 실패해도 전체 흐름은 안 끊기게, null 반환
        }
    }

    private void log(String provider, String endpoint, long startTime, String status) {
        int elapsed = (int) (System.currentTimeMillis() - startTime);
        logRepository.save(new ModelUsageLog(provider, endpoint, elapsed, status));
    }
}