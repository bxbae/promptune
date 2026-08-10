package com.promptune.service;

import com.promptune.dto.PipelineDtos.DiagnoseResult;
import com.promptune.dto.PipelineDtos.RecommendResult;
import com.promptune.domain.PersonalizationScore;
import com.promptune.repository.PersonalizationScoreRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.*;

@Service
public class RecommendService {

    @Autowired
    private PersonalizationScoreRepository scoreRepository;

    public RecommendResult select(DiagnoseResult diagnose, Long userId) {
        List<String> missing = new ArrayList<>();
        diagnose.missing().forEach((el, v) -> { if (v == 1) missing.add(el); });
        missing.sort((a, b) -> Double.compare(getPriorityScore(userId, b), getPriorityScore(userId, a)));
        return new RecommendResult(missing.stream().limit(3).toList());
    }

    private double getPriorityScore(Long userId, String element) {
        return scoreRepository.findByUserIdAndElement(userId, element)
                .map(s -> (double) s.getDismissCount() / Math.max(1, s.getAcceptCount() + s.getDismissCount()))
                .orElse(0.5);
    }
}