package com.promptune.service;

import com.promptune.domain.BehaviorLogEntity;
import com.promptune.domain.PersonalizationScore;
import com.promptune.repository.BehaviorLogRepository;
import com.promptune.repository.PersonalizationScoreRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Locale;
import java.util.Set;

@Service
public class BehaviorLogService {

    private static final Set<String> ACCEPT_ACTIONS = Set.of("tab", "APPLY", "MANUAL_FILL");

    private static final Set<String> DISMISS_ACTIONS = Set.of("esc", "REJECT");

    private static final Set<String> LOG_ONLY_ACTIONS = Set.of("TYPO_APPLY");

    @Autowired
    private BehaviorLogRepository logRepository;

    @Autowired
    private PersonalizationScoreRepository scoreRepository;

    // 2026-09-08: Consent Gate 보완용 - ConsentService는 같은 패키지(com.promptune.service)라 import 불필요
    @Autowired
    private ConsentService consentService;

    @Transactional
    public void recordAction(Long userId, String element, String action) {
        recordAction(userId, element, action, null);
    }

    private static final Set<String> PROMPT_ELEMENTS = Set.of(
            "TASK",
            "AUDIENCE",
            "CONTEXT",
            "FORMAT",
            "TONE",
            "LENGTH",
            "CONSTRAINT",
            "EXAMPLE");

    @Transactional
    public void recordAction(
            Long userId,
            String element,
            String action,
            Long chatSessionId) {

        // 2026-09-08: 동의하지 않은 사용자의 행동은 기록하지 않는다(Consent Gate 보완).
        // 프론트가 이미 전역적으로 미동의 사용자를 이 화면까지 못 오게 막고 있어
        // 정상 흐름에선 도달할 일이 없으나, API 직접 호출 경로에 대한 최후 방어선.
        if (!consentService.canUsePersonalization(userId)) {
            return;
        }

        if (!isSupportedAction(action)) {
            throw new IllegalArgumentException("Unsupported behavior action: " + action);
        }

        String normalizedElement = normalizeElement(element, action);

        logRepository.save(
                new BehaviorLogEntity(
                        userId,
                        normalizedElement,
                        action,
                        chatSessionId));

        if (LOG_ONLY_ACTIONS.contains(action)) {
            return;
        }

        PersonalizationScore score = scoreRepository.findByUserIdAndElement(userId, normalizedElement)
                .orElseGet(() -> new PersonalizationScore(userId, normalizedElement));

        if (ACCEPT_ACTIONS.contains(action)) {
            score.incrementAccept();
        } else if (DISMISS_ACTIONS.contains(action)) {
            score.incrementDismiss();
        }

        scoreRepository.save(score);
    }

    public static boolean isApplyAction(String action) {
        return "tab".equals(action) || "APPLY".equals(action);
    }

    public static boolean isRejectAction(String action) {
        return "esc".equals(action) || "REJECT".equals(action);
    }

    public static boolean isSupportedAction(String action) {
        return ACCEPT_ACTIONS.contains(action)
                || DISMISS_ACTIONS.contains(action)
                || LOG_ONLY_ACTIONS.contains(action);
    }

    public static String normalizeElement(String element, String action) {
        if ("TYPO_APPLY".equals(action)) {
            return "TYPO";
        }

        if (element == null || element.isBlank()) {
            throw new IllegalArgumentException("Behavior element is required");
        }

        String normalized = element.trim().toUpperCase(Locale.ROOT);

        if (!PROMPT_ELEMENTS.contains(normalized)) {
            throw new IllegalArgumentException(
                    "Unsupported behavior element: " + element);
        }

        return normalized;
    }
}
