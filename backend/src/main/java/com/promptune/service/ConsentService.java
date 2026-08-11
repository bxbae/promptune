package com.promptune.service;

import com.promptune.domain.ConsentRecord;
import com.promptune.repository.ConsentRecordRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class ConsentService {

    @Autowired
    private ConsentRecordRepository repository;

    public void grant(Long userId, String consentType) {
        repository.save(new ConsentRecord(userId, consentType));
    }

    public boolean canUsePersonalization(Long userId) {
        return repository.findTopByUserIdOrderByGrantedAtDesc(userId)
                .map(c -> c.getRevokedAt() == null && !"no_save".equals(c.getConsentType()))
                .orElse(false);
    }
}