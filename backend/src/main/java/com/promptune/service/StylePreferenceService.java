package com.promptune.service;

import com.promptune.domain.StylePreferenceScore;
import com.promptune.repository.StylePreferenceScoreRepository;
import org.springframework.stereotype.Service;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Comparator;

@Service
public class StylePreferenceService {

    private static final List<String> FIELDS = List.of("format", "structure", "detail_level");

    private final StylePreferenceScoreRepository repository;

    public StylePreferenceService(StylePreferenceScoreRepository repository) {
        this.repository = repository;
    }

    // 2026-09-02: 4단계 재설계 - 명시적으로 감지된 값들을 카운트로 누적.
    // detected의 값이 null인 필드는 그냥 건너뜀 (이번엔 언급 안 한 것뿐).
    public void recordExplicitMention(Long userId, Map<String, String> detected) {
        for (String field : FIELDS) {
            String value = detected.get(field);
            if (value == null) continue;

            StylePreferenceScore score = repository.findByUserIdAndFieldAndValue(userId, field, value)
                    .orElseGet(() -> new StylePreferenceScore(userId, field, value));
            score.incrementUse();
            repository.save(score);
        }
    }

    // RetrievalPatternService.dominantRoute()와 동일한 안전장치:
    // 5건 미만이거나 60% 미만 쏠림이면 그 필드는 null.
    public Map<String, String> toOutputPreferences(Long userId) {
        Map<String, String> prefs = new HashMap<>();
        for (String field : FIELDS) {
            prefs.put(field, dominantValue(userId, field));
        }
        return prefs;
    }

    private String dominantValue(Long userId, String field) {
        List<StylePreferenceScore> scores = repository.findByUserIdAndField(userId, field);
        int total = scores.stream().mapToInt(StylePreferenceScore::getUseCount).sum();
        if (total < 5) return null;

        StylePreferenceScore dominant = scores.stream()
                .max(Comparator.comparingInt(StylePreferenceScore::getUseCount))
                .orElse(null);
        if (dominant == null) return null;

        double ratio = (double) dominant.getUseCount() / total;
        return ratio >= 0.6 ? dominant.getValue() : null;
    }
}