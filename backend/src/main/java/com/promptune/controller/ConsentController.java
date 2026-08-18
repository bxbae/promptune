package com.promptune.controller;

import com.promptune.domain.User;
import com.promptune.dto.ConsentDtos.GrantConsentRequest;
import com.promptune.repository.UserRepository;
import com.promptune.service.ConsentService;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/consents")
public class ConsentController {

    private final ConsentService consentService;
    private final UserRepository userRepository;

    public ConsentController(ConsentService consentService, UserRepository userRepository) {
        this.consentService = consentService;
        this.userRepository = userRepository;
    }

    // "앞으로 김대리 기본 스타일로 저장할까요?" 동의/거부 버튼에서 호출
    @PostMapping
    public void grant(@RequestBody GrantConsentRequest req, Authentication authentication) {
        User user = currentUser(authentication);
        if (req.receiverProfileId() != null) {
            consentService.grant(user.getId(), req.consentType(), req.receiverProfileId());
        } else {
            consentService.grant(user.getId(), req.consentType());
        }
    }

    // receiverProfileId 파라미터 있으면 그 수신자 기준, 없으면 전체 기준으로 동의 여부 확인
    @GetMapping("/status")
    public java.util.Map<String, Boolean> status(
            @RequestParam(required = false) Long receiverProfileId, Authentication authentication) {
        User user = currentUser(authentication);
        boolean allowed = receiverProfileId != null
                ? consentService.canUsePersonalization(user.getId(), receiverProfileId)
                : consentService.canUsePersonalization(user.getId());
        return java.util.Map.of("allowed", allowed);
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}
