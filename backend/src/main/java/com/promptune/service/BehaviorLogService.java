package com.promptune.service;

import com.promptune.domain.BehaviorLogEntity;
import com.promptune.domain.PersonalizationScore;
import com.promptune.repository.BehaviorLogRepository;
import com.promptune.repository.PersonalizationScoreRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class BehaviorLogService {

    @Autowired private BehaviorLogRepository logRepository;
    @Autowired private PersonalizationScoreRepository scoreRepository;

    @Transactional
    public void recordAction(Long userId, String element, String action) {
        logRepository.save(new BehaviorLogEntity(userId, element, action));

        PersonalizationScore score = scoreRepository.findByUserIdAndElement(userId, element)
                .orElseGet(() -> new PersonalizationScore(userId, element));
        if ("tab".equals(action)) {
            score.incrementAccept();
        } else {
            score.incrementDismiss();
        }
        scoreRepository.save(score);
    }
}