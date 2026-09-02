package com.promptune.repository;

import com.promptune.domain.StylePreferenceScore;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface StylePreferenceScoreRepository extends JpaRepository<StylePreferenceScore, Long> {
    Optional<StylePreferenceScore> findByUserId(Long userId);
}
