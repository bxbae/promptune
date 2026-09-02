package com.promptune.service;

import com.promptune.domain.StylePreferenceScore;
import com.promptune.repository.StylePreferenceScoreRepository;
import org.springframework.stereotype.Service;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class StylePreferenceService {

    private static final Pattern STRUCTURE_MARKER =
            Pattern.compile("(?m)^\\s*(\\||[-*]\\s|\\d+\\.\\s)");

    private final StylePreferenceScoreRepository repository;

    public StylePreferenceService(StylePreferenceScoreRepository repository) {
        this.repository = repository;
    }

    public void recordEdit(Long userId, String generatedResult, String userFinalResult) {
        if (generatedResult == null || userFinalResult == null
                || generatedResult.isBlank() || userFinalResult.isBlank()) {
            return;
        }

        double lengthRatio = (double) userFinalResult.length() / Math.max(1, generatedResult.length());
        int structureDelta = countStructureMarkers(userFinalResult) - countStructureMarkers(generatedResult);

        StylePreferenceScore score = repository.findByUserId(userId)
                .orElseGet(() -> new StylePreferenceScore(userId));
        score.accumulate(lengthRatio, structureDelta);
        repository.save(score);
    }

    private int countStructureMarkers(String text) {
        Matcher m = STRUCTURE_MARKER.matcher(text);
        int count = 0;
        while (m.find()) count++;
        return count;
    }

    // 2026-09-02: 승득님 output_preferences 스키마에 맞춰 매핑 (재검토 후 수정).
    // 승득님 파트(ai-service, 이번 프롬프트에 명시된 형식 감지)가 우선이고,
    // 이 메서드가 반환하는 값은 "명시된 게 없을 때만" 쓰이는 폴백 데이터.
    // 그래서 프론트/모델에게 단정적으로 보이지 않도록, 필드가 비면 그냥 null.
    public Map<String, String> toOutputPreferences(Long userId) {
        Map<String, String> prefs = new HashMap<>();
        prefs.put("format", null);
        prefs.put("length", null);
        prefs.put("structure", null);
        prefs.put("detail_level", null);

        java.util.Optional<StylePreferenceScore> maybeScore = repository.findByUserId(userId);
        if (maybeScore.isEmpty() || maybeScore.get().getSampleCount() < 5) {
            return prefs; // 데이터 부족 - 전부 null
        }
        StylePreferenceScore score = maybeScore.get();

        if (score.getAvgLengthRatio() > 1.3) prefs.put("detail_level", "detailed");
        else if (score.getAvgLengthRatio() < 0.7) prefs.put("detail_level", "concise");

        if (score.getAvgStructureDelta() > 2) prefs.put("structure", "structured");
        // "format": "table"처럼 구체적인 형식까지는 지금 감지 로직(정규식)으로
        // 확신할 수 없어서(표인지 목록인지 구분 못함) null로 남김 - 오늘 하루
        // 계속 지켰던 "확신 없으면 단정하지 않는다" 원칙과 동일.

        return prefs;
    }
}
