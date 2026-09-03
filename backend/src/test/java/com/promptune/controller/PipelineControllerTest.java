package com.promptune.controller;

import com.promptune.repository.ChatSessionRepository;
import com.promptune.repository.DocumentRepository;
import com.promptune.repository.PromptSessionRepository;
import com.promptune.repository.ReceiverProfileRepository;
import com.promptune.repository.UserRepository;
import com.promptune.service.AiServiceClient;
import com.promptune.service.BehaviorLogService;
import com.promptune.service.ConsentService;
import com.promptune.service.DocumentFollowupClassifier;
import com.promptune.service.DocumentIntentResolver;
import com.promptune.service.GateService;
import com.promptune.service.GraphMockService;
import com.promptune.service.MicrosoftGraphService;
import com.promptune.service.OutputPreferenceDetector;
import com.promptune.service.PreferenceResolutionService;
import com.promptune.service.RecommendService;
import com.promptune.service.RetrievalPatternService;
import com.promptune.service.StylePreferenceService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class PipelineControllerTest {

    private AiServiceClient ai;
    private PipelineController controller;

    @BeforeEach
    void setUp() {
        GateService gate = mock(GateService.class);
        ai = mock(AiServiceClient.class);
        RecommendService recommend = mock(RecommendService.class);
        GraphMockService graph = mock(GraphMockService.class);
        UserRepository userRepository = mock(UserRepository.class);
        BehaviorLogService behaviorLog = mock(BehaviorLogService.class);
        PromptSessionRepository promptSessionRepository = mock(PromptSessionRepository.class);
        ChatSessionRepository chatSessionRepository = mock(ChatSessionRepository.class);
        ConsentService consentService = mock(ConsentService.class);
        MicrosoftGraphService microsoftGraphService = mock(MicrosoftGraphService.class);
        PreferenceResolutionService preferenceResolutionService =
                mock(PreferenceResolutionService.class);
        ReceiverProfileRepository receiverProfileRepository =
                mock(ReceiverProfileRepository.class);
        DocumentRepository documentRepository = mock(DocumentRepository.class);
        DocumentIntentResolver documentIntentResolver =
                mock(DocumentIntentResolver.class);
        DocumentFollowupClassifier documentFollowupClassifier =
                mock(DocumentFollowupClassifier.class);
        RetrievalPatternService retrievalPatternService =
                mock(RetrievalPatternService.class);
        StylePreferenceService stylePreferenceService =
                mock(StylePreferenceService.class);
        OutputPreferenceDetector outputPreferenceDetector =
                mock(OutputPreferenceDetector.class);

        controller = new PipelineController(
                gate,
                ai,
                recommend,
                graph,
                userRepository,
                behaviorLog,
                promptSessionRepository,
                chatSessionRepository,
                consentService,
                microsoftGraphService,
                preferenceResolutionService,
                receiverProfileRepository,
                documentRepository,
                documentIntentResolver,
                documentFollowupClassifier,
                retrievalPatternService,
                stylePreferenceService,
                outputPreferenceDetector);
    }

    @Test
    void validationFailure_keepsOriginalGeneratedResponseWithoutRetry() throws Exception {
        String originalPrompt = "ORIGINAL_PROMPT_WITH_FACTS_3_8_28";

        Map<String, Object> firstResult = Map.of(
                "result",
                "FIRST_GENERATION_MISSING_FACTS");

        String validationIssue = "missing fact numbers: 28, 3, 8";

        Map<String, Object> failedValidation = Map.of(
                "passed", false,
                "facts_preserved", false,
                "issues", List.of(validationIssue));

        // 컨트롤러는 4-args validate(original, generated, documents,
        // webResults)를 호출하므로 그 시그니처에 맞춰 stub한다.
        when(ai.validate(eq(originalPrompt), anyString(), anyList(), anyList()))
                .thenReturn(failedValidation);

        Method method = PipelineController.class.getDeclaredMethod(
                "validateWithRetry",
                String.class,
                Map.class,
                String.class,
                List.class,
                List.class,
                Map.class,
                Map.class,
                List.class);

        method.setAccessible(true);

        // passed=false여도 method.invoke()가 예외 없이 끝까지 도달하는 것
        // 자체가 "예외/503이 발생하지 않는다"의 증거다 (목표 3).
        Object returned = method.invoke(
                controller,
                originalPrompt,
                firstResult,
                "email",
                List.of(),
                List.of(),
                Map.of(),
                Map.of(),
                List.of());

        // 목표 2: validate()는 정확히 1회만 호출된다 (재검증 없음).
        verify(ai, times(1)).validate(
                eq(originalPrompt),
                anyString(),
                anyList(),
                anyList());

        // 목표 4: validateWithRetry() 내부에서 두 번째 generate()는
        // 절대 호출되지 않는다. execute()가 validateWithRetry() 호출
        // 전에 최초 generate()를 정확히 1회 호출한다는 점(코드 검토로
        // 확인됨, 399행)과 합치면, 요청당 generate 호출은 항상 1회로
        // 고정된다 (목표 1).
        verify(ai, never()).generate(
                anyString(),
                anyString(),
                anyList(),
                anyList(),
                anyMap(),
                anyMap(),
                anyList());

        // 목표 5 & 6: 반환값은 항상 최초 generate 결과(firstResult) 그대로다.
        // 실제 컨트롤러의 session.setAiResponseText(result.get("result")...)
        // 저장 로직은 이 반환값을 그대로 사용하므로(수정 없음), 여기서
        // 반환값이 firstResult와 같음을 확인하는 것이 aiResponseText도
        // 최초 generate 결과로 저장됨을 보증한다.
        assertEquals(firstResult, returned);
        assertEquals(
                "FIRST_GENERATION_MISSING_FACTS",
                ((Map<?, ?>) returned).get("result"));
    }
}
