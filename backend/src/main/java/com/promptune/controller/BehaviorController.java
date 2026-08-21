package com.promptune.controller;

import com.promptune.domain.ChatSession;
import com.promptune.domain.User;
import com.promptune.dto.BehaviorDtos.BehaviorActionRequest;
import com.promptune.repository.ChatSessionRepository;
import com.promptune.repository.UserRepository;
import com.promptune.service.BehaviorLogService;
import com.promptune.service.ConsentService;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/behavior-actions")
public class BehaviorController {

  private final BehaviorLogService behaviorLogService;
  private final ConsentService consentService;
  private final UserRepository userRepository;
  private final ChatSessionRepository chatSessionRepository;

  public BehaviorController(
      BehaviorLogService behaviorLogService,
      ConsentService consentService,
      UserRepository userRepository,
      ChatSessionRepository chatSessionRepository) {

    this.behaviorLogService = behaviorLogService;
    this.consentService = consentService;
    this.userRepository = userRepository;
    this.chatSessionRepository = chatSessionRepository;
  }

  @PostMapping
  @ResponseStatus(HttpStatus.NO_CONTENT)
  public void recordAction(
      @RequestBody BehaviorActionRequest req,
      Authentication authentication) {

    User user = currentUser(authentication);

    validateChatSession(user.getId(), req.chatSessionId());

    if (!consentService.canUsePersonalization(user.getId())) {
      return;
    }

    try {
      behaviorLogService.recordAction(
          user.getId(),
          req.element(),
          req.action(),
          req.chatSessionId());
    } catch (IllegalArgumentException e) {
      throw new ResponseStatusException(
          HttpStatus.BAD_REQUEST,
          e.getMessage(),
          e);
    }
  }

  private void validateChatSession(Long userId, Long chatSessionId) {
    if (chatSessionId == null) {
      return;
    }

    ChatSession session = chatSessionRepository.findById(chatSessionId)
        .orElseThrow(() -> new ResponseStatusException(
            HttpStatus.NOT_FOUND,
            "Chat session not found"));

    if (!session.getUserId().equals(userId)) {
      throw new ResponseStatusException(
          HttpStatus.FORBIDDEN,
          "You cannot record behavior for another user's chat session");
    }
  }

  private User currentUser(Authentication authentication) {
    if (authentication == null || !authentication.isAuthenticated()) {
      throw new ResponseStatusException(
          HttpStatus.UNAUTHORIZED,
          "Login required");
    }

    return userRepository.findByEmail(authentication.getName())
        .orElseThrow(() -> new ResponseStatusException(
            HttpStatus.NOT_FOUND,
            "User not found"));
  }
}