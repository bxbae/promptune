package com.promptune.controller;

import com.promptune.domain.ChatSession;
import com.promptune.domain.User;
import com.promptune.repository.ChatSessionRepository;
import com.promptune.repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
@RequestMapping("/api/chat-sessions")
public class ChatSessionController {

    private final ChatSessionRepository chatSessionRepository;
    private final UserRepository userRepository;

    public ChatSessionController(ChatSessionRepository chatSessionRepository, UserRepository userRepository) {
        this.chatSessionRepository = chatSessionRepository;
        this.userRepository = userRepository;
    }

    @PostMapping
    public ChatSession create(Authentication authentication) {
        // "+새채팅" 버튼을 누르면 이 API가 호출되어 빈 대화 세션 하나를 만듭니다.
        User user = currentUser(authentication);
        return chatSessionRepository.save(new ChatSession(user.getId()));
    }

    @GetMapping
    public List<ChatSession> myChatSessions(Authentication authentication) {
        // 사이드바 "채팅"/"히스토리" 목록에 최근 대화순으로 보여줄 때 사용
        User user = currentUser(authentication);
        return chatSessionRepository.findByUserIdOrderByUpdatedAtDesc(user.getId());
    }

    @PatchMapping("/{id}")
    public ChatSession updateTitle(@PathVariable Long id,
                                    @RequestBody com.promptune.dto.ChatSessionDtos.UpdateTitleRequest req,
                                    Authentication authentication) {
        User user = currentUser(authentication);
        ChatSession chat = chatSessionRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "대화를 찾을 수 없습니다."));

        if (!chat.getUserId().equals(user.getId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "본인 대화만 수정할 수 있습니다.");
        }

        chat.setTitle(req.title());
        return chatSessionRepository.save(chat);
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}
