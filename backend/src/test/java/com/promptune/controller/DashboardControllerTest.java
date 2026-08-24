package com.promptune.controller;

import com.promptune.domain.BehaviorLogEntity;
import com.promptune.domain.User;
import com.promptune.repository.BehaviorLogRepository;
import com.promptune.repository.PersonalizationScoreRepository;
import com.promptune.repository.PromptSessionRepository;
import com.promptune.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class DashboardControllerTest {

  private BehaviorLogRepository behaviorLogRepository;
  private UserRepository userRepository;
  private DashboardController controller;
  private Authentication authentication;

  @BeforeEach
  void setUp() {
    PersonalizationScoreRepository personalizationScoreRepository = mock(PersonalizationScoreRepository.class);
    PromptSessionRepository promptSessionRepository = mock(PromptSessionRepository.class);

    behaviorLogRepository = mock(BehaviorLogRepository.class);
    userRepository = mock(UserRepository.class);

    controller = new DashboardController(
        personalizationScoreRepository,
        behaviorLogRepository,
        promptSessionRepository,
        userRepository);

    authentication = new UsernamePasswordAuthenticationToken(
        "user@promptune.dev",
        null,
        List.of());

    User user = mock(User.class);
    when(user.getId()).thenReturn(1L);
    when(userRepository.findByEmail("user@promptune.dev"))
        .thenReturn(Optional.of(user));
  }

  @Test
  void applyRate_countsOnlyRecommendationApplyAndRejectActions() {
    when(behaviorLogRepository.findByUserId(1L))
        .thenReturn(List.of(
            new BehaviorLogEntity(1L, "TONE", "APPLY", 10L),
            new BehaviorLogEntity(1L, "FORMAT", "tab", 10L),
            new BehaviorLogEntity(1L, "CONTEXT", "REJECT", 10L),
            new BehaviorLogEntity(1L, "AUDIENCE", "esc", 10L),
            new BehaviorLogEntity(1L, "LENGTH", "MANUAL_FILL", 10L),
            new BehaviorLogEntity(1L, "TYPO", "TYPO_APPLY", 10L)));

    Map<String, Object> result = controller.applyRate(authentication);

    assertEquals(4L, result.get("total"));
    assertEquals(2L, result.get("applied"));
    assertEquals(0.5, (double) result.get("applyRate"), 0.0001);
  }

  @Test
  void applyRate_withoutRecommendationActions_returnsZero() {
    when(behaviorLogRepository.findByUserId(1L))
        .thenReturn(List.of(
            new BehaviorLogEntity(1L, "CONTEXT", "MANUAL_FILL", 10L),
            new BehaviorLogEntity(1L, "TYPO", "TYPO_APPLY", 10L)));

    Map<String, Object> result = controller.applyRate(authentication);

    assertEquals(0L, result.get("total"));
    assertEquals(0L, result.get("applied"));
    assertEquals(0.0, (double) result.get("applyRate"), 0.0001);
  }
}