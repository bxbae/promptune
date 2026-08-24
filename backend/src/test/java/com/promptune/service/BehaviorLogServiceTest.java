package com.promptune.service;

import com.promptune.domain.BehaviorLogEntity;
import com.promptune.domain.PersonalizationScore;
import com.promptune.repository.BehaviorLogRepository;
import com.promptune.repository.PersonalizationScoreRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class BehaviorLogServiceTest {

  private BehaviorLogRepository logRepository;
  private PersonalizationScoreRepository scoreRepository;
  private BehaviorLogService service;

  @BeforeEach
  void setUp() {
    logRepository = mock(BehaviorLogRepository.class);
    scoreRepository = mock(PersonalizationScoreRepository.class);

    service = new BehaviorLogService();

    ReflectionTestUtils.setField(service, "logRepository", logRepository);
    ReflectionTestUtils.setField(service, "scoreRepository", scoreRepository);
  }

  @Test
  void apply_normalizesElementAndIncrementsAccept() {
    when(scoreRepository.findByUserIdAndElement(1L, "TONE"))
        .thenReturn(Optional.empty());

    service.recordAction(1L, "tone", "APPLY", 10L);

    ArgumentCaptor<BehaviorLogEntity> logCaptor = ArgumentCaptor.forClass(BehaviorLogEntity.class);

    verify(logRepository).save(logCaptor.capture());

    BehaviorLogEntity savedLog = logCaptor.getValue();

    assertEquals("TONE", savedLog.getElement());
    assertEquals("APPLY", savedLog.getAction());
    assertEquals(10L, savedLog.getChatSessionId());

    ArgumentCaptor<PersonalizationScore> scoreCaptor = ArgumentCaptor.forClass(PersonalizationScore.class);

    verify(scoreRepository).save(scoreCaptor.capture());

    PersonalizationScore score = scoreCaptor.getValue();

    assertEquals("TONE", score.getElement());
    assertEquals(1, score.getAcceptCount());
    assertEquals(0, score.getDismissCount());
  }

  @Test
  void reject_incrementsDismiss() {
    when(scoreRepository.findByUserIdAndElement(1L, "FORMAT"))
        .thenReturn(Optional.empty());

    service.recordAction(1L, "format", "REJECT", 10L);

    ArgumentCaptor<PersonalizationScore> scoreCaptor = ArgumentCaptor.forClass(PersonalizationScore.class);

    verify(scoreRepository).save(scoreCaptor.capture());

    PersonalizationScore score = scoreCaptor.getValue();

    assertEquals("FORMAT", score.getElement());
    assertEquals(0, score.getAcceptCount());
    assertEquals(1, score.getDismissCount());
  }

  @Test
  void manualFill_incrementsAccept() {
    when(scoreRepository.findByUserIdAndElement(1L, "CONTEXT"))
        .thenReturn(Optional.empty());

    service.recordAction(1L, "Context", "MANUAL_FILL", 10L);

    ArgumentCaptor<BehaviorLogEntity> logCaptor = ArgumentCaptor.forClass(BehaviorLogEntity.class);

    verify(logRepository).save(logCaptor.capture());

    assertEquals("CONTEXT", logCaptor.getValue().getElement());
    assertEquals("MANUAL_FILL", logCaptor.getValue().getAction());

    ArgumentCaptor<PersonalizationScore> scoreCaptor = ArgumentCaptor.forClass(PersonalizationScore.class);

    verify(scoreRepository).save(scoreCaptor.capture());

    assertEquals(1, scoreCaptor.getValue().getAcceptCount());
    assertEquals(0, scoreCaptor.getValue().getDismissCount());
  }

  @Test
  void typoApply_savesLogOnly() {
    service.recordAction(1L, null, "TYPO_APPLY", 10L);

    ArgumentCaptor<BehaviorLogEntity> logCaptor = ArgumentCaptor.forClass(BehaviorLogEntity.class);

    verify(logRepository).save(logCaptor.capture());

    BehaviorLogEntity savedLog = logCaptor.getValue();

    assertEquals("TYPO", savedLog.getElement());
    assertEquals("TYPO_APPLY", savedLog.getAction());

    verifyNoInteractions(scoreRepository);
  }

  @Test
  void legacyTab_isStillAccept() {
    when(scoreRepository.findByUserIdAndElement(1L, "TASK"))
        .thenReturn(Optional.empty());

    service.recordAction(1L, "task", "tab", null);

    ArgumentCaptor<PersonalizationScore> scoreCaptor = ArgumentCaptor.forClass(PersonalizationScore.class);

    verify(scoreRepository).save(scoreCaptor.capture());

    assertEquals(1, scoreCaptor.getValue().getAcceptCount());
    assertEquals(0, scoreCaptor.getValue().getDismissCount());
  }

  @Test
  void unsupportedElement_isRejectedWithoutSaving() {
    assertThrows(
        IllegalArgumentException.class,
        () -> service.recordAction(
            1L,
            "report",
            "APPLY",
            10L));

    verify(logRepository, never()).save(any());
    verifyNoInteractions(scoreRepository);
  }

  @Test
  void unsupportedAction_isRejectedWithoutSaving() {
    assertThrows(
        IllegalArgumentException.class,
        () -> service.recordAction(
            1L,
            "TONE",
            "UNKNOWN",
            10L));

    verify(logRepository, never()).save(any());
    verifyNoInteractions(scoreRepository);
  }
}