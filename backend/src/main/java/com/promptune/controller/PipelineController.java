package com.promptune.controller;

import java.util.Map;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable; // 추가
import org.springframework.web.bind.annotation.PostMapping; // 추가
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.server.ResponseStatusException;

import com.promptune.domain.User;
import com.promptune.dto.PipelineDtos.*;
import com.promptune.dto.PipelineDtos.AnalyzeRequest;
import com.promptune.dto.PipelineDtos.AnalyzeResponse;
import com.promptune.dto.PipelineDtos.DiagnoseResult;
import com.promptune.dto.PipelineDtos.ExecuteRequest;
import com.promptune.dto.PipelineDtos.GateResult;
import com.promptune.dto.PipelineDtos.RecommendResult;
import com.promptune.dto.PipelineDtos.SuggestResult;
import com.promptune.repository.UserRepository;
import com.promptune.service.AiServiceClient;
import com.promptune.service.BehaviorLogService;
import com.promptune.service.GateService;
import com.promptune.service.GraphMockService;
import com.promptune.service.RecommendService;
import com.promptune.service.ConsentService;

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
    private final UserRepository userRepository; // 추가 (companyId 조회용)
    private final BehaviorLogService behaviorLog; // 필드 추가
    private final com.promptune.repository.PromptSessionRepository promptSessionRepository;
    private final com.promptune.repository.ChatSessionRepository chatSessionRepository;

        private final ConsentService consentService;
    private final com.promptune.service.MicrosoftGraphService microsoftGraphService;
    private final com.promptune.service.PreferenceResolutionService preferenceResolutionService;
    private final com.promptune.repository.ReceiverProfileRepository receiverProfileRepository; // 추가

    public PipelineController(GateService gate, AiServiceClient ai,
        RecommendService recommend, GraphMockService graph,
        UserRepository userRepository,
        BehaviorLogService behaviorLog,
        com.promptune.repository.PromptSessionRepository promptSessionRepository,
        com.promptune.repository.ChatSessionRepository chatSessionRepository,
        ConsentService consentService,
        com.promptune.service.MicrosoftGraphService microsoftGraphService,
        com.promptune.service.PreferenceResolutionService preferenceResolutionService,
        com.promptune.repository.ReceiverProfileRepository receiverProfileRepository) {
        this.gate = gate;
        this.ai = ai;
        this.recommend = recommend;
        this.graph = graph;
        this.userRepository = userRepository;
        this.behaviorLog = behaviorLog;
        this.promptSessionRepository = promptSessionRepository;
        this.chatSessionRepository = chatSessionRepository;
        this.consentService = consentService;
        this.microsoftGraphService = microsoftGraphService;
        this.preferenceResolutionService = preferenceResolutionService;
        this.receiverProfileRepository = receiverProfileRepository;
    }

    /**
     * 2번: 프롬프트 분석 (입력 중단 시 프론트가 호출).
     * 흐름: 3게이트 → 5진단(AI) → 6수정요소선정 → 7추천문구선정(AI)
     */
    @PostMapping("/analyze")
    public AnalyzeResponse analyze(@RequestBody AnalyzeRequest req, org.springframework.security.core.Authentication authentication) {
        User currentUser = userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new org.springframework.web.server.ResponseStatusException(
                        org.springframework.http.HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));

        // 3번 게이트
        GateResult g = gate.check(req.text());
        if (!g.passed()) {
            return new AnalyzeResponse(
                    g,
                    null,
                    null,
                    null);
        }
        // 5번 진단 (ai-service 호출)
        DiagnoseResult d = ai.diagnose(req.text());

        // 6번 수정요소 선정
        RecommendResult r = recommend.select(d, currentUser.getId());

        // 7번 문맥 기반 추천문구 선정
        SuggestResult s;

        if (r.targetElements().isEmpty()) {
            s = new SuggestResult(java.util.List.of());
        } else {
            s = ai.suggest(
                    req.text(),
                    r.targetElements());
        }

        return new AnalyzeResponse(
                g,
                d,
                r,
                s);
    }

    /**
     * 11번: 실행 (Enter).
     * 흐름: 12분류 → (13검색) → 14생성(AI) → 16저장
     */
    @PostMapping("/execute")
public Map<String, Object> execute(@RequestBody ExecuteRequest req, org.springframework.security.core.Authentication authentication) {
    User currentUser = userRepository.findByEmail(authentication.getName())
            .orElseThrow(() -> new org.springframework.web.server.ResponseStatusException(
                    org.springframework.http.HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    Long userId = currentUser.getId();

    java.util.List<java.util.Map<String, String>> conversationHistory =
            buildConversationHistory(req.chatSessionId(), userId);

    DiagnoseResult d = ai.diagnose(req.finalPrompt());

    // Retrieval Router/Orchestrator(승연님 PR #67)가 내부문서 검색·웹검색 여부까지
    // 통째로 판단·실행해서 결과를 돌려줌. 자바 쪽 needsInternalDocs/ai.retrieve()는 더 이상 안 씀.
    // TODO: 사용자가 웹검색 버튼 켰는지(req.useWebSearch())를 retrieval-execute에 전달해야
    // "내부문서+웹검색 복합 요청"이 동작함. 승연님과 함께 필드 추가 작업 진행 중.
    Map<String, Object> retrieval = ai.retrievalExecute(
            req.finalPrompt(),
            userId,
            3,
            conversationHistory);
    java.util.List<java.util.Map<String, Object>> documents =
            (java.util.List<java.util.Map<String, Object>>) retrieval.getOrDefault("documents", java.util.List.of());
    java.util.List<java.util.Map<String, Object>> webResults =
            (java.util.List<java.util.Map<String, Object>>) retrieval.getOrDefault("web_results", java.util.List.of());

    // user_context이면 실제 Microsoft Graph 프로필을 생성 컨텍스트로 전달.
    // Microsoft 미연동/연동 실패 시에도 채팅 자체는 계속 진행돼야 하므로
    // (다른 보조 조회들과 동일하게) 실패는 조용히 무시하고 컨텍스트 없이 진행한다.
    // (안 그러면 user_context 라우트로 분류된 모든 메시지가 Microsoft 미연동
    // 사용자에게는 통째로 실패해버림 - 2026-08-24 채팅 전체 실패 이슈)
    Map<String, String> userContext = new java.util.HashMap<>();

    if ("user_context".equals(retrieval.get("route"))) {
        try {
            com.fasterxml.jackson.databind.JsonNode profile =
                    microsoftGraphService.getProfile(userId);

            String displayName = profile.path("displayName").asText("");
            String companyName = profile.path("companyName").asText("");
            String department = profile.path("department").asText("");
            String jobTitle = profile.path("jobTitle").asText("");
            String mail = profile.path("mail").asText("");

            if (!displayName.isBlank()) userContext.put("displayName", displayName);
            if (!companyName.isBlank()) userContext.put("companyName", companyName);
            if (!department.isBlank()) userContext.put("department", department);
            if (!jobTitle.isBlank()) userContext.put("jobTitle", jobTitle);
            if (!mail.isBlank()) userContext.put("mail", mail);
        } catch (Exception e) {
            // Microsoft 미연동(404) 등 - userContext 없이 계속 진행
        }
    }

    var preference = preferenceResolutionService.resolve(authentication);
    Map<String, String> preferenceMap = new java.util.HashMap<>();
    preferenceMap.put("speed", preference.speed());
    preferenceMap.put("detail", preference.detail());
    preferenceMap.put("preserve", preference.preserve());

    // 수신자가 지정된 경우, 그 사람 preferredTone을 생성 요청에 함께 전달
    // (본인 소유 프로필인지 확인 - 남의 receiverProfileId를 넣어도 무시되도록 방어)
    if (req.receiverProfileId() != null) {
        receiverProfileRepository.findById(req.receiverProfileId())
                .filter(rp -> rp.getUserId().equals(userId))
                .map(com.promptune.domain.ReceiverProfile::getPreferredTone)
                .filter(tone -> tone != null && !tone.isBlank())
                .ifPresent(tone -> preferenceMap.put("receiverTone", tone));
    }

    Map result = ai.generate(
            req.finalPrompt(),
            d.taskType(),
            documents,
            webResults,
            userContext,
            preferenceMap,
            conversationHistory);

    result = validateWithRetry(
              req.finalPrompt(),
              result,
              d.taskType(),
              documents,
              webResults,
              userContext,
              preferenceMap,
              conversationHistory);

    if (req.elementActions() != null && consentService.canUsePersonalization(userId)) {
        for (com.promptune.dto.PipelineDtos.ElementAction ea : req.elementActions()) {
            behaviorLog.recordAction(userId, ea.element(), ea.action(), req.chatSessionId());
        }
    }

    com.promptune.domain.PromptSession session = new com.promptune.domain.PromptSession(
            userId, req.finalPrompt(), req.finalPrompt(), d.taskType(), req.chatSessionId());
    // AI 응답 원문도 같이 저장 (이제까지 저장 안 되고 있던 부분 — 메시지 목록에 필요해서 추가)
    Object aiText = result != null ? result.get("result") : null;
    session.setAiResponseText(aiText != null ? aiText.toString() : null);
    promptSessionRepository.save(session);

    if (req.chatSessionId() != null) {
    chatSessionRepository.findById(req.chatSessionId()).ifPresent(chat -> {
        // 이 대화의 첫 프롬프트라면(title이 아직 없으면) 제목 자동 생성
        if (chat.getTitle() == null || chat.getTitle().isBlank()) {
            String raw = req.finalPrompt();
            String aiTitle = ai.summarizeTitle(raw);   // ai-service 호출 시도

            String title;
            if (aiTitle != null && !aiTitle.isBlank()) {
                title = aiTitle;   // AI 요약 성공
            } else {
                // ai-service 호출 실패 시 안전장치: 기존 방식(앞부분 자르기)으로 대체
                title = raw.length() > 20 ? raw.substring(0, 20) + "..." : raw;
            }
            chat.setTitle(title);
        }
        chat.touch();
        chatSessionRepository.save(chat);
    });
}

    return Map.of(
            "taskType", d.taskType(),
            "needsInternalDocs", "internal_rag".equals(retrieval.get("route")),
            "retrievalRoute", retrieval.get("route"),
            "usedInternalRag", retrieval.getOrDefault("used_internal_rag", false),
            "usedWebSearch", retrieval.getOrDefault("used_web_search", false),
            "result", result,
            "promptSessionId", session.getId());
    }

    private java.util.List<java.util.Map<String, String>> buildConversationHistory(
            Long chatSessionId,
            Long userId) {

        if (chatSessionId == null) {
            return java.util.List.of();
        }

        com.promptune.domain.ChatSession chat =
                chatSessionRepository.findById(chatSessionId)
                        .orElseThrow(() -> new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "대화를 찾을 수 없습니다."));

        if (!userId.equals(chat.getUserId())) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "본인 대화만 사용할 수 있습니다.");
        }

        java.util.List<com.promptune.domain.PromptSession> sessions =
                promptSessionRepository
                        .findByChatSessionIdOrderByCreatedAtAsc(chatSessionId);

        // 최근 6개 대화쌍만 전달하여 HCX context 크기를 제한
        int startIndex = Math.max(0, sessions.size() - 6);

        java.util.List<java.util.Map<String, String>> history =
                new java.util.ArrayList<>();

        for (int i = startIndex; i < sessions.size(); i++) {
            com.promptune.domain.PromptSession session = sessions.get(i);

            String userText = compactHistoryText(session.getOriginalText());

            if (userText != null && !userText.isBlank()) {
                history.add(java.util.Map.of(
                        "role", "user",
                        "content", userText));
            }

            String assistantText =
                    compactHistoryText(session.getAiResponseText());

            if (assistantText != null && !assistantText.isBlank()) {
                history.add(java.util.Map.of(
                        "role", "assistant",
                        "content", assistantText));
            }
        }

        return history;
    }

    private String compactHistoryText(String text) {
        if (text == null || text.length() <= 1500) {
            return text;
        }

        return text.substring(0, 750)
                + "\n...[이전 대화 중략]...\n"
                + text.substring(text.length() - 750);
    }

    // generate() 결과를 검증하고, 실패 시 1회만 재생성 후 재검증.
    // 재생성 시에도 동일한 conversation history를 유지한다.
    private Map validateWithRetry(
            String originalPrompt,
            Map result,
            String taskType,
            java.util.List<java.util.Map<String, Object>> documents,
            java.util.List<java.util.Map<String, Object>> webResults,
            Map<String, String> userContext,
            Map<String, String> preferenceMap,
            java.util.List<java.util.Map<String, String>> conversationHistory) {

        Object generatedText = result != null ? result.get("result") : null;

        if (generatedText == null) {
            return result;
        }

        Map validation =
                ai.validate(originalPrompt, generatedText.toString());

        boolean passed =
                Boolean.TRUE.equals(validation.get("passed"));

        if (passed) {
            return result;
        }

        Map retryResult = ai.generate(
                originalPrompt,
                taskType,
                documents,
                webResults,
                userContext,
                preferenceMap,
                conversationHistory);

        Object retryText =
                retryResult != null ? retryResult.get("result") : null;

        if (retryText == null) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "답변 생성에 실패했습니다.");
        }

        Map retryValidation =
                ai.validate(originalPrompt, retryText.toString());

        boolean retryPassed =
                Boolean.TRUE.equals(retryValidation.get("passed"));

        if (!retryPassed) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "검증을 통과하는 답변을 생성하지 못했습니다.");
        }

        return retryResult;
    }

    /** 0번: 사용자 맥락 (로그인 후 사전 조회) — /api/execute와 동일한 이유로 경로변수 대신 인증 기반으로 전환 */
    @GetMapping("/context")
    public Map<String, Object> context(org.springframework.security.core.Authentication authentication) {
        User currentUser = userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new org.springframework.web.server.ResponseStatusException(
                        org.springframework.http.HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
        return Map.of(
                "firstVisit", graph.isFirstVisit(currentUser.getId()),
                "workContext", graph.getUserContext(currentUser.getId()));
    }
}
