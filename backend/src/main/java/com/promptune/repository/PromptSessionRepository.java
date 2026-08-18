package com.promptune.repository;

import com.promptune.domain.PromptSession;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface PromptSessionRepository extends JpaRepository<PromptSession, Long> {
    List<PromptSession> findByChatSessionIdOrderByCreatedAtAsc(Long chatSessionId);
    List<PromptSession> findByUserId(Long userId);
    void deleteByUserId(Long userId);
}
