package com.promptune.controller;

import com.promptune.domain.User;
import com.promptune.domain.UserPreference;
import com.promptune.dto.UserPreferenceDtos.UpsertPreferenceRequest;
import com.promptune.repository.UserPreferenceRepository;
import com.promptune.repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/users/me/preferences")
public class UserPreferenceController {

    private final UserPreferenceRepository preferenceRepository;
    private final UserRepository userRepository;

    public UserPreferenceController(UserPreferenceRepository preferenceRepository, UserRepository userRepository) {
        this.preferenceRepository = preferenceRepository;
        this.userRepository = userRepository;
    }

    // 온보딩 완료 시 최초 저장, 이후엔 설정 변경 시 같은 API로 덮어씀
    @PutMapping
    public UserPreference upsert(@RequestBody UpsertPreferenceRequest req, Authentication authentication) {
        User user = currentUser(authentication);
        UserPreference pref = preferenceRepository.findByUserId(user.getId())
                .orElse(new UserPreference(user.getId(), req.speed(), req.detail(), req.preserve()));
        pref.update(req.speed(), req.detail(), req.preserve());
        return preferenceRepository.save(pref);
    }

    // 온보딩 완료 여부 판단 + 설정 화면 표시용 조회
    @GetMapping
    public UserPreference get(Authentication authentication) {
        User user = currentUser(authentication);
        return preferenceRepository.findByUserId(user.getId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "온보딩이 아직 완료되지 않았습니다."));
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}
