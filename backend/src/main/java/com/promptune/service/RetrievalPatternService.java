package com.promptune.service;

import com.promptune.domain.RetrievalPatternScore;
import com.promptune.repository.RetrievalPatternScoreRepository;
import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Comparator;

@Service
public class RetrievalPatternService {

    private final RetrievalPatternScoreRepository repository;

    public RetrievalPatternService(RetrievalPatternScoreRepository repository) {
        this.repository = repository;
    }

    public void recordUse(Long userId, String route) {
        RetrievalPatternScore score = repository.findByUserIdAndRoute(userId, route)
                .orElseGet(() -> new RetrievalPatternScore(userId, route));
        score.incrementUse();
        repository.save(score);
    }

    /** 데이터 5건 미만이거나 뚜렷한 쏠림(60% 이상)이 없으면 null. */
    public String dominantRoute(Long userId) {
        List<RetrievalPatternScore> scores = repository.findByUserId(userId);
        int total = scores.stream().mapToInt(RetrievalPatternScore::getUseCount).sum();
        if (total < 5) return null;

        RetrievalPatternScore dominant = scores.stream()
                .max(Comparator.comparingInt(RetrievalPatternScore::getUseCount))
                .orElse(null);
        if (dominant == null) return null;

        double ratio = (double) dominant.getUseCount() / total;
        return ratio >= 0.6 ? dominant.getRoute() : null;
    }
}
