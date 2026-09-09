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

    // 2026-09-08: 프론트 lib/toneMapping.ts의 suggestToneFromJobTitle()과 동일 규칙의
    // 백엔드 사본. MS 동기화 시점에 즉시 기본 톤을 채우기 위해 필요 - 이 계산은
    // 대화(applyConsent)를 거치지 않고도 MS 연동 직후에 바로 실행돼야 하므로,
    // 프론트 로직만으로는 커버가 안 되고 백엔드에도 같은 매핑이 있어야 함.
    // 두 쪽 매핑이 어긋나면 "MS 연동 직후 기본값"과 "대화 중 재확인 후 값"이
    // 서로 달라질 수 있으니, 직급 목록을 바꿀 때는 반드시 프론트 쪽도 같이 바꿀 것.
    private static final java.util.Set<String> SENIOR_TITLES =
            java.util.Set.of("이사", "부장", "상무", "전무", "대표");
    private static final java.util.Set<String> MID_TITLES =
            java.util.Set.of("차장", "과장", "팀장");

    // 기존 receiver_profile은 receiverName에 직급까지 합쳐 저장돼 있다
    // (예: "유재석 부장"). 기존 데이터/수신자 매칭 계약을 깨지 않으면서
    // 히스토리 화면과 기본 톤 백필에 직급을 사용할 수 있도록 마지막 토큰만 해석한다.
    private static final java.util.Set<String> KNOWN_TITLES =
            java.util.Set.of(
                    "대표", "이사", "상무", "전무", "부장",
                    "차장", "과장", "팀장", "대리", "사원", "인턴");

    private String suggestToneFromJobTitle(String jobTitle) {
        if (jobTitle == null || jobTitle.isBlank()) {
            return null;
        }
        if (SENIOR_TITLES.stream().anyMatch(jobTitle::contains)) {
            return "격식체";
        }
        if (MID_TITLES.stream().anyMatch(jobTitle::contains)) {
            return "정중체";
        }
        return "편한존댓말";
    }

    private String extractJobTitleFromReceiverName(String receiverName) {
        if (receiverName == null || receiverName.isBlank()) {
            return null;
        }

        String[] parts = receiverName.trim().split("\\s+");
        if (parts.length < 2) {
            return null;
        }

        String last = parts[parts.length - 1];
        return KNOWN_TITLES.contains(last) ? last : null;
    }

    public ReceiverProfile upsert(Long userId, String receiverName, String tone, int length) {
        ReceiverProfile profile = repository.findByUserIdAndReceiverName(userId, receiverName)
                .orElseGet(() -> new ReceiverProfile(userId, receiverName));
        profile.setPreferredTone(tone);
        profile.setAvgLength((profile.getAvgLength() + length) / 2);
        return repository.save(profile);
    }

    // MS 조직도 구성원 목록을 불러올 때, 그 사람들을 자동으로 수신자별 스타일에
    // "풀네임+직함"(예: "정형돈 대리") + 부서로 저장한다.
    // relationship은 MS가 모르는 정보라 여기서 안 건드리고 그대로 둔다.
    //
    // 2026-09-08(변경): preferredTone은 예전엔 여기서 안 건드리고 null로 시작해
    // "채팅에서 자연히 학습됨"을 기다렸는데, 그러면 아직 한 번도 대화 안 나눈
    // 사람은 수신자별 스타일 화면에서 계속 텅 비어 보이는 문제가 있었음.
    // 이제는 MS 연동 직후 직급 기반 기본값을 즉시 채운다 - 단, 이미 대화로 학습된
    // 값(preferredTone != null)이 있는 프로필은 재동기화 때마다 덮어쓰지 않고 보존한다.
    public ReceiverProfile upsertFromMicrosoft(Long userId, String displayName, String jobTitle, String department) {
        if (displayName == null || displayName.isBlank()) {
            return null;
        }
        String receiverName = (jobTitle == null || jobTitle.isBlank())
                ? displayName.trim()
                : displayName.trim() + " " + jobTitle.trim();

        ReceiverProfile profile = repository.findByUserIdAndReceiverName(userId, receiverName)
                .orElseGet(() -> new ReceiverProfile(userId, receiverName));
        profile.setMsSynced(true);
        profile.setDepartment(department);

        if (profile.getPreferredTone() == null || profile.getPreferredTone().isBlank()) {
            profile.setPreferredTone(suggestToneFromJobTitle(jobTitle));
        }

        return repository.save(profile);
    }

    public List<ReceiverProfile> list(Long userId) {
        List<ReceiverProfile> profiles = repository.findByUserId(userId);

        for (ReceiverProfile profile : profiles) {
            // 2026-09-09: 직급 기반 기본 톤 도입 전에 생성된 기존 프로필은
            // preferredTone이 비어 있을 수 있다. receiverName 끝의 직급을 해석해
            // 한 번만 기본값을 백필한다. 이미 학습/수정된 톤은 절대 덮어쓰지 않는다.
            if (profile.getPreferredTone() == null || profile.getPreferredTone().isBlank()) {
                String jobTitle = extractJobTitleFromReceiverName(profile.getReceiverName());
                String suggestedTone = suggestToneFromJobTitle(jobTitle);
                if (suggestedTone != null) {
                    profile.setPreferredTone(suggestedTone);
                    repository.save(profile);
                }
            }

            profile.setApplyRate(calculateApplyRate(userId, profile.getId()));
        }

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
        // department는 MS 조직도 동기화 값(2026-09-02)이라, MS로 동기화된 프로필은
        // 프론트에서 입력창 자체를 안 보여주지만 백엔드에서도 한 번 더 막아둔다
        // (MS가 원천 소스라 사용자가 직접 고치면 다음 동기화 때 다시 덮어써져서 혼란만 생김).
        if (department != null) {
            if (profile.isMsSynced()) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT, "MS 조직도와 동기화된 수신자는 부서를 직접 수정할 수 없습니다.");
            }
            profile.setDepartment(department);
        }
        if (preferredTone != null) profile.setPreferredTone(preferredTone);
        // 동명이인 통합 시 더 완전한 이름(성+이름+직함)으로 정정하는 용도.
        // department와 같은 이유로, MS 동기화 프로필은 이름도 MS가 원천 소스라
        // 사용자가 직접 고치면 다음 동기화 때 다시 덮어써져서 혼란만 생긴다.
        if (receiverName != null && !receiverName.isBlank()) {
            if (profile.isMsSynced()) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT, "MS 조직도와 동기화된 수신자는 이름을 직접 수정할 수 없습니다.");
            }
            profile.setReceiverName(receiverName);
        }

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