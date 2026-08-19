package com.promptune.controller;

import com.promptune.domain.PromptSession;
import com.promptune.domain.ResponseEdit;
import com.promptune.domain.User;
import com.promptune.dto.PromptSessionDtos.SubmitEditRequest;
import com.promptune.repository.PromptSessionRepository;
import com.promptune.repository.ResponseEditRepository;
import com.promptune.repository.UserRepository;
import com.promptune.service.BehaviorLogService;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import com.promptune.service.ConsentService;

@RestController
@RequestMapping("/api/prompt-sessions")
public class PromptSessionController {

    private final PromptSessionRepository promptSessionRepository;
    private final ResponseEditRepository responseEditRepository;
    private final UserRepository userRepository;
    private final BehaviorLogService behaviorLog;
    private final ConsentService consentService;

    public PromptSessionController(PromptSessionRepository promptSessionRepository,
                                    ResponseEditRepository responseEditRepository,
                                    UserRepository userRepository,
                                    BehaviorLogService behaviorLog,
                                    ConsentService consentService) {
        this.promptSessionRepository = promptSessionRepository;
        this.responseEditRepository = responseEditRepository;
        this.userRepository = userRepository;
        this.behaviorLog = behaviorLog;
        this.consentService = consentService;
    }

    @PostMapping("/{id}/edits")
    public PromptSession submitEdit(@PathVariable Long id, @RequestBody SubmitEditRequest req,
                                     Authentication authentication) {
        User user = currentUser(authentication);
        PromptSession session = promptSessionRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "요청을 찾을 수 없습니다."));

        if (!session.getUserId().equals(user.getId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "본인 요청만 수정할 수 있습니다.");
        }

        boolean edited = req.generatedResult() != null
                && req.userFinalResult() != null
                && !req.generatedResult().equals(req.userFinalResult());

        if (edited) {
            responseEditRepository.save(new ResponseEdit(
                    id, user.getId(), req.generatedResult(), req.userFinalResult()));
            if (consentService.canUsePersonalization(user.getId())) {
                behaviorLog.recordAction(user.getId(), session.getTaskType(), "edit", session.getChatSessionId());
            }
        }

        if (req.satisfaction() != null) {
            session.setSatisfaction(req.satisfaction());
        }

        return promptSessionRepository.save(session);
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}
