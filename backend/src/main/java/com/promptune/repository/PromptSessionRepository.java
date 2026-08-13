package com.promptune.repository;

import com.promptune.domain.PromptSession;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PromptSessionRepository extends JpaRepository<PromptSession, Long> {
}
