package com.promptune.service;

import com.promptune.domain.ReceiverProfile;
import com.promptune.repository.ReceiverProfileRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
public class ReceiverProfileService {

    @Autowired
    private ReceiverProfileRepository repository;

    public ReceiverProfile upsert(Long userId, String receiverName, String tone, int length) {
        ReceiverProfile profile = repository.findByUserIdAndReceiverName(userId, receiverName)
                .orElseGet(() -> new ReceiverProfile(userId, receiverName));
        profile.setPreferredTone(tone);
        profile.setAvgLength((profile.getAvgLength() + length) / 2);
        return repository.save(profile);
    }

    public List<ReceiverProfile> list(Long userId) {
        return repository.findByUserId(userId);
    }
}