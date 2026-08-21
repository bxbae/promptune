package com.promptune.service;

import com.promptune.domain.BehaviorLogEntity;
import com.promptune.dto.ActivityLogDtos.ActivityLogEntry;
import com.promptune.repository.BehaviorLogRepository;
import com.promptune.repository.PromptSessionRepository;
import com.promptune.repository.ResponseEditRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class ActivityLogServiceTest {

  private BehaviorLogRepository behaviorLogRepository;
  private ResponseEditRepository responseEditRepository;
  private PromptSessionRepository promptSessionRepository;
  private ActivityLogService service;

  @BeforeEach
  void setUp() {
    behaviorLogRepository = mock(BehaviorLogRepository.class);
    responseEditRepository = mock(ResponseEditRepository.class);
    promptSessionRepository = mock(PromptSessionRepository.class);

    service = new ActivityLogService(
        behaviorLogRepository,
        responseEditRepository,
        promptSessionRepository);
  }

  @Test
  void behaviorLogs_classifyApplyAndRejectAndIgnoreOtherActions() {
    when(behaviorLogRepository.findByUserId(1L))
        .thenReturn(List.of(
            new BehaviorLogEntity(1L, "TONE", "APPLY", 10L),
            new BehaviorLogEntity(1L, "FORMAT", "tab", 10L),
            new BehaviorLogEntity(1L, "CONTEXT", "REJECT", 10L),
            new BehaviorLogEntity(1L, "AUDIENCE", "esc", 10L),
            new BehaviorLogEntity(1L, "LENGTH", "MANUAL_FILL", 10L),
            new BehaviorLogEntity(1L, "TYPO", "TYPO_APPLY", 10L)));

    List<ActivityLogEntry> result = service.list(1L, null);

    assertEquals(4, result.size());

    long applied = result.stream()
        .filter(entry -> "applied".equals(entry.type()))
        .count();

    long rejected = result.stream()
        .filter(entry -> "rejected".equals(entry.type()))
        .count();

    assertEquals(2, applied);
    assertEquals(2, rejected);
  }

  @Test
  void appliedFilter_returnsOnlyApplyActions() {
    when(behaviorLogRepository.findByUserId(1L))
        .thenReturn(List.of(
            new BehaviorLogEntity(1L, "TONE", "APPLY", 10L),
            new BehaviorLogEntity(1L, "FORMAT", "tab", 10L),
            new BehaviorLogEntity(1L, "CONTEXT", "REJECT", 10L)));

    List<ActivityLogEntry> result = service.list(1L, "applied");

    assertEquals(2, result.size());
    assertEquals(
        2,
        result.stream()
            .filter(entry -> "applied".equals(entry.type()))
            .count());
  }

  @Test
  void rejectedFilter_returnsOnlyRejectActions() {
    when(behaviorLogRepository.findByUserId(1L))
        .thenReturn(List.of(
            new BehaviorLogEntity(1L, "TONE", "APPLY", 10L),
            new BehaviorLogEntity(1L, "CONTEXT", "REJECT", 10L),
            new BehaviorLogEntity(1L, "AUDIENCE", "esc", 10L)));

    List<ActivityLogEntry> result = service.list(1L, "rejected");

    assertEquals(2, result.size());
    assertEquals(
        2,
        result.stream()
            .filter(entry -> "rejected".equals(entry.type()))
            .count());
  }
}