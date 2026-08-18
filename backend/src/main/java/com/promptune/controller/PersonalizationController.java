package com.promptune.controller;

import com.promptune.domain.User;
import com.promptune.dto.PersonalizationDtos.PersonalizationExport;
import com.promptune.repository.*;
import com.promptune.service.ConsentService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/users/me/personalization")
public class PersonalizationController {

    private final UserRepository userRepository;
    private final UserPreferenceRepository userPreferenceRepository;
    private final ReceiverProfileRepository receiverProfileRepository;
    private final ConsentRecordRepository consentRecordRepository;
    private final BehaviorLogRepository behaviorLogRepository;
    private final PersonalizationScoreRepository personalizationScoreRepository;
    private final ConsentService consentService;

    public PersonalizationController(UserRepository userRepository,
                                      UserPreferenceRepository userPreferenceRepository,
                                      ReceiverProfileRepository receiverProfileRepository,
                                      ConsentRecordRepository consentRecordRepository,
                                      BehaviorLogRepository behaviorLogRepository,
                                      PersonalizationScoreRepository personalizationScoreRepository,
                                      ConsentService consentService) {
        this.userRepository = userRepository;
        this.userPreferenceRepository = userPreferenceRepository;
        this.receiverProfileRepository = receiverProfileRepository;
        this.consentRecordRepository = consentRecordRepository;
        this.behaviorLogRepository = behaviorLogRepository;
        this.personalizationScoreRepository = personalizationScoreRepository;
        this.consentService = consentService;
    }

    // 히스토리 > 개인화 설정 화면의 "전체 초기화" 버튼
    @DeleteMapping
    @Transactional
    public ResponseEntity<Void> reset(Authentication authentication) {
        User user = currentUser(authentication);
        Long userId = user.getId();

        userPreferenceRepository.findByUserId(userId).ifPresent(userPreferenceRepository::delete);
        // receiver_profile 삭제 시 그 수신자에 딸린 consent_records는 CASCADE로 자동 삭제됨
        receiverProfileRepository.deleteByUserId(userId);
        // 전체(수신자 무관) 동의 기록은 CASCADE 대상이 아니라 별도 삭제 필요
        consentRecordRepository.deleteByUserIdAndReceiverProfileIdIsNull(userId);
        behaviorLogRepository.deleteByUserId(userId);
        personalizationScoreRepository.deleteByUserId(userId);

        return ResponseEntity.noContent().build();
    }

    // 히스토리 > 개인화 설정 화면의 "내보내기" 버튼
    @GetMapping("/export")
    public PersonalizationExport export(Authentication authentication) {
        User user = currentUser(authentication);
        Long userId = user.getId();

        var preferences = userPreferenceRepository.findByUserId(userId).orElse(null);
        var receivers = receiverProfileRepository.findByUserId(userId);
        boolean globalConsent = consentService.canUsePersonalization(userId);

        return new PersonalizationExport(preferences, receivers, globalConsent);
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}
