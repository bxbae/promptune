package com.promptune.repository;

import com.promptune.domain.PersonalizationScore;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface PersonalizationScoreRepository extends JpaRepository<PersonalizationScore, Long> {
    Optional<PersonalizationScore> findByUserIdAndElement(Long userId, String element);
}