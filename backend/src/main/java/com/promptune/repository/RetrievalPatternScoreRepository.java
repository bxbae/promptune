package com.promptune.repository;

import com.promptune.domain.RetrievalPatternScore;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface RetrievalPatternScoreRepository extends JpaRepository<RetrievalPatternScore, Long> {
    Optional<RetrievalPatternScore> findByUserIdAndRoute(Long userId, String route);
    List<RetrievalPatternScore> findByUserId(Long userId);
}
