package com.promptune.controller;

import com.promptune.domain.ReceiverProfile;
import com.promptune.domain.User;
import com.promptune.dto.ReceiverProfileDtos.UpsertReceiverProfileRequest;
import com.promptune.repository.UserRepository;
import com.promptune.service.ReceiverProfileService;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
@RequestMapping("/api/receiver-profiles")
public class ReceiverProfileController {

    private final ReceiverProfileService receiverProfileService;
    private final UserRepository userRepository;

    public ReceiverProfileController(ReceiverProfileService receiverProfileService, UserRepository userRepository) {
        this.receiverProfileService = receiverProfileService;
        this.userRepository = userRepository;
    }

    // 수신자 등록/갱신 (같은 이름이면 톤·평균길이를 기존값과 평균내어 갱신 — ReceiverProfileService.upsert 로직 그대로 사용)
    @PostMapping
    public ReceiverProfile upsert(@RequestBody UpsertReceiverProfileRequest req, Authentication authentication) {
        User user = currentUser(authentication);
        int length = req.length() != null ? req.length() : 0;
        return receiverProfileService.upsert(user.getId(), req.receiverName(), req.tone(), length);
    }

    // 내 수신자 목록 조회
    @GetMapping
    public List<ReceiverProfile> list(Authentication authentication) {
        User user = currentUser(authentication);
        return receiverProfileService.list(user.getId());
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}
