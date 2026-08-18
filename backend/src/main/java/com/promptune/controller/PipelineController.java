package com.promptune.controller;

import com.promptune.dto.PipelineDtos.*;
import com.promptune.service.*;
import com.promptune.domain.User; // 추가
import com.promptune.repository.UserRepository; // 추가
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
    private final RequestClassificationService classification; // 추가
    private final UserRepository userRepository; // 추가 (companyId 조회용)
    private final BehaviorLogService behaviorLog; // 필드 추가
    private final com.promptune.repository.PromptSessionRepository promptSessionRepository;
private final com.promptune.repository.ChatSessionRepository chatSessionRepository;

    public PipelineController(GateService gate, AiServiceClient ai,
        RecommendService recommend, GraphMockService graph,
        RequestClassificationService classification,
        UserRepository userRepository,
        BehaviorLogService behaviorLog,
        com.promptune.repository.PromptSessionRepository promptSessionRepository,
        com.promptune.repository.ChatSessionRepository chatSessionRepository) {
        this.gate = gate;
        this.ai = ai;
        this.recommend = recommend;
        this.graph = graph;
        this.classification = classification;
        this.userRepository = userRepository;
        this.behaviorLog = behaviorLog;
        this.promptSessionRepository = promptSessionRepository;
        this.chatSessionRepository = chatSessionRepository;
    }

    /**
     * 2번: 프롬프트 분석 (입력 중단 시 프론트가 호출).
     * 흐름: 3게이트 → 5진단(AI) → 6수정요소선정 → 7추천문구선정(AI)
     */
    @PostMapping("/analyze")
    public AnalyzeResponse analyze(@RequestBody AnalyzeRequest req) {
        System.out.println("========== /api/analyze 호출됨 ==========");
        System.out.println("받은 text 값: " + (req != null ? req.text() : "req가 null입니다"));
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
        RecommendResult r = recommend.select(d, req.userId());

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
public Map<String, Object> execute(@RequestBody ExecuteRequest req) {
    DiagnoseResult d = ai.diagnose(req.finalPrompt());

    String companyId = userRepository.findById(req.userId())
            .map(User::getCompanyId).orElse("default-company");
    boolean needsInternalDocs = classification.needsInternalDocs(d.needsInternalDocs());

    // needsInternalDocs(내부문서 자동검색)와 useWebSearch(사용자가 버튼 누른 외부검색)는 서로 다른 개념 —
    // 지금까지 needsInternalDocs를 그대로 여기 넘기고 있던 버그 수정 (승연님 리포트)
    boolean useWebSearch = Boolean.TRUE.equals(req.useWebSearch());
    Map result = ai.generate(req.finalPrompt(), d.taskType(), useWebSearch);

    // 요소별 적용/거절 기록 (10번 사용자선택 → 16번 행동저장, 파이프라인 문서 기준)
    // taskType 기반 단일 로그(예전 방식)는 제거 — 이제 진짜 8요소 데이터가 element 컬럼에 쌓여야 하므로
    // taskType 문자열과 섞이면 안 됨
    if (req.elementActions() != null) {
        for (com.promptune.dto.PipelineDtos.ElementAction ea : req.elementActions()) {
            behaviorLog.recordAction(req.userId(), ea.element(), ea.action());
        }
    }

    // prompt_sessions 저장 (지금까지 없던 로직, 이번에 신규 추가) + chat_session 연결
    com.promptune.domain.PromptSession session = new com.promptune.domain.PromptSession(
            req.userId(), req.finalPrompt(), req.finalPrompt(), d.taskType(), req.chatSessionId());
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
            "needsInternalDocs", needsInternalDocs,
            "result", result);
}

    /** 0번: 사용자 맥락 (로그인 후 사전 조회) */
    @GetMapping("/context/{userId}")
    public Map<String, Object> context(@PathVariable Long userId) {
        return Map.of(
                "firstVisit", graph.isFirstVisit(userId),
                "workContext", graph.getUserContext(userId));
    }
}
