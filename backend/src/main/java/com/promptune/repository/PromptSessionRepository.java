package com.promptune.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.promptune.domain.PromptSession;

public interface PromptSessionRepository extends JpaRepository<PromptSession, Long> {
    List<PromptSession> findByChatSessionIdOrderByCreatedAtAsc(Long chatSessionId);
    List<PromptSession> findByUserId(Long userId);
    List<PromptSession> findByUserIdAndReceiverProfileId(Long userId, Long receiverProfileId);
    // 채팅에 묶인 prompt_sessions는 chat_sessions 삭제 시 ON DELETE CASCADE로 이미 같이
    // 지워지므로, 여기서 또 지우려고 하면 "이미 없는 행"을 지우는 셈이라 Hibernate가
    // StaleObjectStateException을 던진다. 그래서 채팅에 안 묶인(orphan) 것만 지운다.
    void deleteByUserIdAndChatSessionIdIsNull(Long userId);
}
