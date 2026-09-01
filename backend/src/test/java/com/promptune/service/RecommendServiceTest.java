package com.promptune.service;

import com.promptune.domain.PersonalizationScore;
import com.promptune.dto.PipelineDtos.DiagnoseResult;
import com.promptune.dto.PipelineDtos.RecommendResult;
import com.promptune.repository.PersonalizationScoreRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class RecommendServiceTest {

  private PersonalizationScoreRepository scoreRepository;
  private RecommendService service;

  @BeforeEach
  void setUp() {
    scoreRepository = mock(PersonalizationScoreRepository.class);

    service = new RecommendService();

    ReflectionTestUtils.setField(service, "scoreRepository", scoreRepository);
  }

  private PersonalizationScore scoreWith(String element, int accept, int dismiss) {
    PersonalizationScore score = new PersonalizationScore(1L, element);
    for (int i = 0; i < accept; i++) {
      score.incrementAccept();
    }
    for (int i = 0; i < dismiss; i++) {
      score.incrementDismiss();
    }
    return score;
  }

  @Test
  void frequentlyAcceptedElement_isRankedBeforeFrequentlyDismissedElement() {
    // (P1-3) 문서 예시: CONTEXT는 주로 accept, TONE은 주로 dismiss된 사용자.
    // "자주 accept한 요소를 우선한다"는 의도대로 CONTEXT가 먼저 나와야 한다.
    when(scoreRepository.findByUserIdAndElement(1L, "CONTEXT"))
        .thenReturn(Optional.of(scoreWith("CONTEXT", 8, 2)));
    when(scoreRepository.findByUserIdAndElement(1L, "TONE"))
        .thenReturn(Optional.of(scoreWith("TONE", 2, 8)));

    Map<String, Integer> missing = new LinkedHashMap<>();
    missing.put("TONE", 1);
    missing.put("CONTEXT", 1);

    DiagnoseResult diagnose = new DiagnoseResult(missing, "email", List.of(), false);

    RecommendResult result = service.select(diagnose, 1L);

    assertEquals(List.of("CONTEXT", "TONE"), result.targetElements());
  }

  @Test
  void newUserWithNoHistory_doesNotThrowAndReturnsMissingElements() {
    // (P1-3) 기록이 전혀 없는 신규 사용자 - divide-by-zero 없이, 예외 없이
    // 부족 요소가 그대로 반환돼야 한다.
    when(scoreRepository.findByUserIdAndElement(1L, "TASK"))
        .thenReturn(Optional.empty());
    when(scoreRepository.findByUserIdAndElement(1L, "FORMAT"))
        .thenReturn(Optional.empty());

    Map<String, Integer> missing = new LinkedHashMap<>();
    missing.put("TASK", 1);
    missing.put("FORMAT", 1);

    DiagnoseResult diagnose = new DiagnoseResult(missing, "email", List.of(), false);

    RecommendResult result = assertDoesNotThrow(
        () -> service.select(diagnose, 1L));

    assertEquals(2, result.targetElements().size());
    assertTrue(result.targetElements().containsAll(List.of("TASK", "FORMAT")));
  }

  @Test
  void nonMissingElement_isNeverIncludedRegardlessOfPersonalizationScore() {
    // (P1-3) KcELECTRA가 missing=0으로 판단한 요소는, 개인화 점수가 아무리
    // 높아도(=자주 accept됐어도) 새로 추천되면 안 된다 - 개인화는 이미
    // 확정된 부족 요소 후보들의 "순서"만 조정해야 한다.
    when(scoreRepository.findByUserIdAndElement(1L, "CONSTRAINT"))
        .thenReturn(Optional.of(scoreWith("CONSTRAINT", 20, 0)));

    Map<String, Integer> missing = new LinkedHashMap<>();
    missing.put("CONSTRAINT", 0);
    missing.put("EXAMPLE", 1);

    DiagnoseResult diagnose = new DiagnoseResult(missing, "email", List.of(), false);

    RecommendResult result = service.select(diagnose, 1L);

    assertFalse(result.targetElements().contains("CONSTRAINT"));
    assertEquals(List.of("EXAMPLE"), result.targetElements());
  }

  @Test
  void moreThanThreeMissingElements_isCappedAtThree() {
    when(scoreRepository.findByUserIdAndElement(1L, "TASK"))
        .thenReturn(Optional.of(scoreWith("TASK", 10, 0)));
    when(scoreRepository.findByUserIdAndElement(1L, "AUDIENCE"))
        .thenReturn(Optional.of(scoreWith("AUDIENCE", 8, 2)));
    when(scoreRepository.findByUserIdAndElement(1L, "CONTEXT"))
        .thenReturn(Optional.of(scoreWith("CONTEXT", 6, 4)));
    when(scoreRepository.findByUserIdAndElement(1L, "FORMAT"))
        .thenReturn(Optional.of(scoreWith("FORMAT", 1, 9)));

    Map<String, Integer> missing = new LinkedHashMap<>();
    missing.put("TASK", 1);
    missing.put("AUDIENCE", 1);
    missing.put("CONTEXT", 1);
    missing.put("FORMAT", 1);

    DiagnoseResult diagnose = new DiagnoseResult(missing, "email", List.of(), false);

    RecommendResult result = service.select(diagnose, 1L);

    assertEquals(3, result.targetElements().size());
    assertEquals(List.of("TASK", "AUDIENCE", "CONTEXT"), result.targetElements());
  }
}
