package com.promptune.repository;

import com.promptune.domain.PersonalizationScore;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;
import java.util.List;

public interface PersonalizationScoreRepository extends JpaRepository<PersonalizationScore, Long> {
    Optional<PersonalizationScore> findByUserIdAndElement(Long userId, String element);
    List<PersonalizationScore> findByUserId(Long userId);
    void deleteByUserId(Long userId);
}
