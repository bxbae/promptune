package com.promptune.service;

import com.promptune.domain.ReceiverProfile;
import com.promptune.repository.ReceiverProfileRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
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

    // ← 신규 추가: PATCH /api/receiver-profiles/{id}
    public ReceiverProfile update(Long userId, Long id, String relationship, String preferredTone, String receiverName) {
        ReceiverProfile profile = repository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "수신자 프로필을 찾을 수 없습니다."));

        if (!profile.getUserId().equals(userId)) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN, "본인 수신자 프로필만 수정할 수 있습니다.");
        }

        // null이 아닌 필드만 부분 수정 (PATCH 시맨틱 — DocumentController.update()와 동일 패턴)
        if (relationship != null) profile.setRelationship(relationship);
        if (preferredTone != null) profile.setPreferredTone(preferredTone);
        // 동명이인 통합 시 더 완전한 이름(성+이름+직함)으로 정정하는 용도.
        if (receiverName != null && !receiverName.isBlank()) profile.setReceiverName(receiverName);

        return repository.save(profile);
    }

    // ← 신규 추가: DELETE /api/receiver-profiles/{id}
    public void delete(Long userId, Long id) {
        ReceiverProfile profile = repository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "수신자 프로필을 찾을 수 없습니다."));

        if (!profile.getUserId().equals(userId)) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN, "본인 수신자 프로필만 삭제할 수 있습니다.");
        }

        repository.deleteById(id);
        // consent_records.receiver_profile_id는 V18에서 ON DELETE CASCADE로 걸어놨으므로
        // 관련 동의 기록은 DB가 알아서 같이 정리합니다. 자바에서 따로 지울 필요 없음.
    }
}