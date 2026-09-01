package com.promptune.controller;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import com.promptune.domain.ChatSession;
import com.promptune.domain.User;
import com.promptune.repository.ChatSessionRepository;
import com.promptune.repository.UserRepository;

@RestController
@RequestMapping("/api/chat-sessions")
public class ChatSessionController {

    private final ChatSessionRepository chatSessionRepository;
    private final UserRepository userRepository;
    private final com.promptune.repository.PromptSessionRepository promptSessionRepository;
    private final com.promptune.repository.DocumentRepository documentRepository;

    public ChatSessionController(ChatSessionRepository chatSessionRepository, UserRepository userRepository,
                                  com.promptune.repository.PromptSessionRepository promptSessionRepository,
                                  com.promptune.repository.DocumentRepository documentRepository) {
        this.chatSessionRepository = chatSessionRepository;
        this.userRepository = userRepository;
        this.promptSessionRepository = promptSessionRepository;
        this.documentRepository = documentRepository;
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

    // 채팅 하나 열었을 때 지난 메시지 목록 조회
    @GetMapping("/{id}/messages")
    public java.util.List<com.promptune.dto.ChatSessionDtos.MessageResponse> messages(
            @PathVariable Long id, Authentication authentication) {
        User user = currentUser(authentication);
        ChatSession chat = chatSessionRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "대화를 찾을 수 없습니다."));

        if (!chat.getUserId().equals(user.getId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "본인 대화만 조회할 수 있습니다.");
        }

        return promptSessionRepository.findByChatSessionIdOrderByCreatedAtAsc(id).stream()
                .map(p -> {
                    java.util.List<com.promptune.dto.ChatSessionDtos.DocumentSummary> attachments =
                            documentRepository.findByPromptSessionId(p.getId()).stream()
                                    .map(doc -> new com.promptune.dto.ChatSessionDtos.DocumentSummary(
                                            doc.getId(), doc.getTitle(), doc.getDocumentType()))
                                    .toList();
                    return new com.promptune.dto.ChatSessionDtos.MessageResponse(
                            p.getId(), p.getOriginalText(), p.getAiResponseText(), p.getTaskType(),
                            p.getCreatedAt(), p.getSatisfaction(), attachments);
                })
                .toList();
    }

    // 채팅 삭제 (메시지·response_edits는 DB CASCADE로 같이 삭제됨)
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id, Authentication authentication) {
        User user = currentUser(authentication);
        ChatSession chat = chatSessionRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "대화를 찾을 수 없습니다."));

        if (!chat.getUserId().equals(user.getId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "본인 대화만 삭제할 수 있습니다.");
        }

        chatSessionRepository.delete(chat);
        return ResponseEntity.noContent().build();
    }

    // 히스토리 > 개인화 설정 화면의 "작업 이력 전체 삭제" 버튼
    // 채팅 세션 전체 삭제 (메시지·response_edits는 DB CASCADE로 같이 삭제됨) + 채팅에 안 묶인 프롬프트 기록까지 정리
    // 주의: chat_sessions 삭제 시 ON DELETE CASCADE로 그 prompt_sessions도 이미 같이 지워지므로,
    // 아래 두 번째 호출은 "채팅에 안 묶인(orphan) 것만" 지워야 한다 - 그냥 deleteByUserId를 쓰면
    // 이미 CASCADE로 지워진 행을 또 지우려다 StaleObjectStateException이 난다.
    @DeleteMapping
    @Transactional
    public ResponseEntity<Void> deleteAll(Authentication authentication) {
        User user = currentUser(authentication);
        chatSessionRepository.deleteByUserId(user.getId());
        promptSessionRepository.deleteByUserIdAndChatSessionIdIsNull(user.getId());
        return ResponseEntity.noContent().build();
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}
