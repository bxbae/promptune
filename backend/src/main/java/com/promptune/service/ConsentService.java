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

    // 수신자별 동의 저장 (신규)
    public void grant(Long userId, String consentType, Long receiverProfileId) {
        repository.save(new ConsentRecord(userId, consentType, receiverProfileId));
    }

        public boolean canUsePersonalization(Long userId) {
        // receiver_profile_id가 null인(=전체 동의) 기록만 봐야 함. 수신자별 동의랑 섞이면 안 됨.
        return repository.findTopByUserIdAndReceiverProfileIdIsNullOrderByGrantedAtDesc(userId)
                .map(c -> c.getRevokedAt() == null && !"no_save".equals(c.getConsentType()))
                .orElse(false);
    }

    // 특정 수신자에 한정된 동의 여부. 그 수신자 전용 기록이 없으면 전체 동의로 대체 확인.
    public boolean canUsePersonalization(Long userId, Long receiverProfileId) {
        return repository.findTopByUserIdAndReceiverProfileIdOrderByGrantedAtDesc(userId, receiverProfileId)
                .map(c -> c.getRevokedAt() == null && !"no_save".equals(c.getConsentType()))
                .orElseGet(() -> canUsePersonalization(userId));
    }
}