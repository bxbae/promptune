package com.promptune.repository;

import com.promptune.domain.ChatSession;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface ChatSessionRepository extends JpaRepository<ChatSession, Long> {
    List<ChatSession> findByUserIdOrderByUpdatedAtDesc(Long userId);
    void deleteByUserId(Long userId);

    @org.springframework.data.jpa.repository.Query(
            "SELECT COALESCE(MAX(c.userSequence), 0) FROM ChatSession c WHERE c.userId = :userId")
    int findMaxUserSequence(@org.springframework.data.repository.query.Param("userId") Long userId);
}
