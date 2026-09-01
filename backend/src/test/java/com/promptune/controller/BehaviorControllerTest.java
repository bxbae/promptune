package com.promptune.controller;

import com.promptune.domain.ChatSession;
import com.promptune.domain.User;
import com.promptune.dto.BehaviorDtos.BehaviorActionRequest;
import com.promptune.repository.ChatSessionRepository;
import com.promptune.repository.UserRepository;
import com.promptune.service.BehaviorLogService;
// import com.promptune.service.ConsentService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.*;

class BehaviorControllerTest {

  private BehaviorLogService behaviorLogService;
//   private ConsentService consentService;
  private UserRepository userRepository;
  private ChatSessionRepository chatSessionRepository;
  private BehaviorController controller;

  private Authentication authentication;
  private User user;

  @BeforeEach
  void setUp() {
    behaviorLogService = mock(BehaviorLogService.class);
    // consentService = mock(ConsentService.class);
    userRepository = mock(UserRepository.class);
    chatSessionRepository = mock(ChatSessionRepository.class);

    controller = new BehaviorController(
        behaviorLogService,
        // consentService,
        userRepository,
        chatSessionRepository);

    authentication = new UsernamePasswordAuthenticationToken(
        "user@promptune.dev",
        null,
        List.of());

    user = mock(User.class);
    when(user.getId()).thenReturn(1L);
    when(userRepository.findByEmail("user@promptune.dev"))
        .thenReturn(Optional.of(user));
  }

  @Test
  void validAction_recordsBehaviorForOwnedChatSession() {
    ChatSession session = mock(ChatSession.class);
    when(session.getUserId()).thenReturn(1L);
    when(chatSessionRepository.findById(10L))
        .thenReturn(Optional.of(session));
    // when(consentService.canUsePersonalization(1L))
        // .thenReturn(true);

    BehaviorActionRequest request = new BehaviorActionRequest("tone", "APPLY", 10L);

    controller.recordAction(request, authentication);

    verify(behaviorLogService).recordAction(
        1L,
        "tone",
        "APPLY",
        10L);
  }

  @Test
  void noPersonalizationConsent_doesNotRecordBehavior() {
    // when(consentService.canUsePersonalization(1L))
        // .thenReturn(false);

    BehaviorActionRequest request = new BehaviorActionRequest("tone", "APPLY", null);

    controller.recordAction(request, authentication);

    verifyNoInteractions(behaviorLogService);
  }

  @Test
  void anotherUsersChatSession_returnsForbidden() {
    ChatSession session = mock(ChatSession.class);
    when(session.getUserId()).thenReturn(2L);
    when(chatSessionRepository.findById(10L))
        .thenReturn(Optional.of(session));

    BehaviorActionRequest request = new BehaviorActionRequest("tone", "APPLY", 10L);

    ResponseStatusException exception = assertThrows(
        ResponseStatusException.class,
        () -> controller.recordAction(request, authentication));

    assertEquals(HttpStatus.FORBIDDEN, exception.getStatusCode());

    verifyNoInteractions(behaviorLogService);
  }

  @Test
  void missingChatSession_returnsNotFound() {
    when(chatSessionRepository.findById(99L))
        .thenReturn(Optional.empty());

    BehaviorActionRequest request = new BehaviorActionRequest("tone", "APPLY", 99L);

    ResponseStatusException exception = assertThrows(
        ResponseStatusException.class,
        () -> controller.recordAction(request, authentication));

    assertEquals(HttpStatus.NOT_FOUND, exception.getStatusCode());

    verifyNoInteractions(behaviorLogService);
  }

  @Test
  void invalidBehaviorRequest_returnsBadRequest() {
    // when(consentService.canUsePersonalization(1L))
    //     .thenReturn(true);

    doThrow(new IllegalArgumentException("Unsupported behavior element: report"))
        .when(behaviorLogService)
        .recordAction(1L, "report", "APPLY", null);

    BehaviorActionRequest request = new BehaviorActionRequest("report", "APPLY", null);

    ResponseStatusException exception = assertThrows(
        ResponseStatusException.class,
        () -> controller.recordAction(request, authentication));

    assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
  }

  @Test
  void unauthenticatedRequest_returnsUnauthorized() {
    BehaviorActionRequest request = new BehaviorActionRequest("tone", "APPLY", null);

    ResponseStatusException exception = assertThrows(
        ResponseStatusException.class,
        () -> controller.recordAction(request, null));

    assertEquals(HttpStatus.UNAUTHORIZED, exception.getStatusCode());

    verifyNoInteractions(behaviorLogService);
  }
}