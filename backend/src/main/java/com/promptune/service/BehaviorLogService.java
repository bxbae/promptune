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
