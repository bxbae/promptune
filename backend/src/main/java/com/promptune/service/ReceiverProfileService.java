package com.promptune.service;

import com.promptune.domain.PromptSession;
import com.promptune.domain.ReceiverProfile;
import com.promptune.domain.ResponseEdit;
import com.promptune.repository.PromptSessionRepository;
import com.promptune.repository.ReceiverProfileRepository;
import com.promptune.repository.ResponseEditRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import java.math.BigDecimal;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class ReceiverProfileService {

    @Autowired
    private ReceiverProfileRepository repository;

    @Autowired
    private PromptSessionRepository promptSessionRepository;

    @Autowired
    private ResponseEditRepository responseEditRepository;

    public ReceiverProfile upsert(Long userId, String receiverName, String tone, int length) {
        ReceiverProfile profile = repository.findByUserIdAndReceiverName(userId, receiverName)
                .orElseGet(() -> new ReceiverProfile(userId, receiverName));
        profile.setPreferredTone(tone);
        profile.setAvgLength((profile.getAvgLength() + length) / 2);
        return repository.save(profile);
    }

    public List<ReceiverProfile> list(Long userId) {
        List<ReceiverProfile> profiles = repository.findByUserId(userId);
        profiles.forEach(profile -> profile.setApplyRate(calculateApplyRate(userId, profile.getId())));
        return profiles;
    }

    // 2026-09-01: 이 수신자를 지정해서 보낸 요청 중, 수정 없이(response_edits에
    // row가 없이) 그대로 쓴 비율. 이 수신자로 지정해서 보낸 이력이 아예 없으면
    // null(프론트에서 "-"로 표시) — 계산이 안 된 게 아니라 애초에 데이터가 없는
    // 게 맞는 정상 상태다 (수신자 선택은 사용자가 화면에서 명시적으로 골라야만
    // 발생하는 액션이라, 그런 적이 없는 수신자는 계속 이 상태로 남는다).
    private BigDecimal calculateApplyRate(Long userId, Long receiverProfileId) {
        List<PromptSession> sessions =
                promptSessionRepository.findByUserIdAndReceiverProfileId(userId, receiverProfileId);

        if (sessions.isEmpty()) {
            return null;
        }

        List<Long> sessionIds = sessions.stream().map(PromptSession::getId).toList();

        Set<Long> editedSessionIds = responseEditRepository.findByPromptSessionIdIn(sessionIds).stream()
                .map(ResponseEdit::getPromptSessionId)
                .collect(Collectors.toSet());

        long appliedCount = sessions.stream()
                .filter(session -> !editedSessionIds.contains(session.getId()))
                .count();

        double rate = (double) appliedCount / sessions.size();

        return BigDecimal.valueOf(rate);
    }

    // ← 신규 추가: PATCH /api/receiver-profiles/{id}
    public ReceiverProfile update(Long userId, Long id, String relationship, String department, String preferredTone, String receiverName) {
        ReceiverProfile profile = repository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "수신자 프로필을 찾을 수 없습니다."));

        if (!profile.getUserId().equals(userId)) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN, "본인 수신자 프로필만 수정할 수 있습니다.");
        }

        // null이 아닌 필드만 부분 수정 (PATCH 시맨틱 — DocumentController.update()와 동일 패턴)
        if (relationship != null) profile.setRelationship(relationship);
        // department는 MS 조직도 동기화 값 (2026-09-02)
        if (department != null) profile.setDepartment(department);
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