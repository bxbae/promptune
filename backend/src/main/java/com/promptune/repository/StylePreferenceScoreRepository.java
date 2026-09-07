package com.promptune.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.promptune.domain.StylePreferenceScore;

public interface StylePreferenceScoreRepository extends JpaRepository<StylePreferenceScore, Long> {
    Optional<StylePreferenceScore> findByUserIdAndFieldAndValue(Long userId, String field, String value);
    List<StylePreferenceScore> findByUserIdAndField(Long userId, String field);
    void deleteByUserId(Long userId);
}