package com.promptune.controller;

import com.promptune.domain.User;
import com.promptune.dto.UserDtos.UpdateCompanyRequest;
import com.promptune.repository.*;
import com.promptune.service.S3StorageService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserRepository userRepository;
    private final UserPreferenceRepository userPreferenceRepository;
    private final ReceiverProfileRepository receiverProfileRepository;
    private final ConsentRecordRepository consentRecordRepository;
    private final BehaviorLogRepository behaviorLogRepository;
    private final PersonalizationScoreRepository personalizationScoreRepository;
    private final RetrievalPatternScoreRepository retrievalPatternScoreRepository;
    private final StylePreferenceScoreRepository stylePreferenceScoreRepository;
    private final DocumentRepository documentRepository;
    private final ChatSessionRepository chatSessionRepository;
    private final PromptSessionRepository promptSessionRepository;
    private final S3StorageService s3StorageService;

    public UserController(UserRepository userRepository,
                           UserPreferenceRepository userPreferenceRepository,
                           ReceiverProfileRepository receiverProfileRepository,
                           ConsentRecordRepository consentRecordRepository,
                           BehaviorLogRepository behaviorLogRepository,
                           PersonalizationScoreRepository personalizationScoreRepository,
                           RetrievalPatternScoreRepository retrievalPatternScoreRepository,
                           StylePreferenceScoreRepository stylePreferenceScoreRepository,
                           DocumentRepository documentRepository,
                           ChatSessionRepository chatSessionRepository,
                           PromptSessionRepository promptSessionRepository,
                           S3StorageService s3StorageService) {
        this.userRepository = userRepository;
        this.userPreferenceRepository = userPreferenceRepository;
        this.receiverProfileRepository = receiverProfileRepository;
        this.consentRecordRepository = consentRecordRepository;
        this.behaviorLogRepository = behaviorLogRepository;
        this.personalizationScoreRepository = personalizationScoreRepository;
        this.retrievalPatternScoreRepository = retrievalPatternScoreRepository;
        this.stylePreferenceScoreRepository = stylePreferenceScoreRepository;
        this.documentRepository = documentRepository;
        this.chatSessionRepository = chatSessionRepository;
        this.promptSessionRepository = promptSessionRepository;
        this.s3StorageService = s3StorageService;
    }

    @PutMapping("/company")
    public ResponseEntity<?> updateCompany(@RequestBody UpdateCompanyRequest req, Authentication authentication) {
        User user = currentUser(authentication);
        user.setCompanyId(req.companyId());
        userRepository.save(user);
        return ResponseEntity.ok(java.util.Map.of("ok", true, "companyId", user.getCompanyId()));
    }

    // 계정 탈퇴 - 개인화 데이터(PersonalizationController.reset()과 동일한 순서) +
    // 대화 기록 + User row까지 전부 삭제. microsoft_connections/microsoft_oauth_states는
    // ON DELETE CASCADE라 userRepository.delete(user)에서 DB가 알아서 같이 지운다.
    @DeleteMapping("/me")
    @Transactional
    public ResponseEntity<Void> deleteAccount(Authentication authentication) {
        User user = currentUser(authentication);
        Long userId = user.getId();

        // 개인화 데이터
        userPreferenceRepository.findByUserId(userId).ifPresent(userPreferenceRepository::delete);
        // receiver_profile 삭제 시 그 수신자에 딸린 consent_records는 CASCADE로 자동 삭제됨
        receiverProfileRepository.deleteByUserId(userId);
        // 전체(수신자 무관) 동의 기록은 CASCADE 대상이 아니라 별도 삭제 필요
        consentRecordRepository.deleteByUserIdAndReceiverProfileIdIsNull(userId);
        behaviorLogRepository.deleteByUserId(userId);
        personalizationScoreRepository.deleteByUserId(userId);
        // 이 두 테이블은 DB에 user FK 자체가 없어(문서상 확인) 명시적으로 지워야 고아 데이터가 안 남음
        retrievalPatternScoreRepository.deleteByUserId(userId);
        stylePreferenceScoreRepository.deleteByUserId(userId);

        // 업로드한 파일 - S3 먼저, DB는 나중(S3 key를 잃기 전에 지워야 함)
        for (var document : documentRepository.findByOwnerUserId(userId)) {
            s3StorageService.delete(document.getS3Key());
        }
        documentRepository.deleteByOwnerUserId(userId);  // document_chunks는 ON DELETE CASCADE로 자동 삭제

        // 대화 기록 - chat_sessions 삭제 시 prompt_sessions/response_edits는 ON DELETE CASCADE로 같이 삭제됨
        chatSessionRepository.deleteByUserId(userId);
        // 채팅에 안 묶인 orphan prompt_session (및 그에 딸린 response_edits, CASCADE)
        promptSessionRepository.deleteByUserIdAndChatSessionIdIsNull(userId);

        // 계정 자체 삭제
        userRepository.delete(user);

        return ResponseEntity.noContent().build();
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}