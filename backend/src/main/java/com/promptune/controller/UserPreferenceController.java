package com.promptune.controller;

import com.promptune.domain.User;
import com.promptune.domain.UserPreference;
import com.promptune.dto.UserPreferenceDtos.UpsertPreferenceRequest;
import com.promptune.repository.UserPreferenceRepository;
import com.promptune.repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
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
    // 온보딩 전이면 본문이 null인 200을 돌려줌 (ResponseStatusException(404)를 던지면 Spring Security
    // 설정과 맞물려 /login으로 302 리다이렉트되고, fetch가 그 리다이렉트를 따라가 HTML을 JSON으로 파싱하려다
    // 프론트에서 "Unexpected token '<'" 에러가 나는 문제가 있었음 — 그래서 404 대신 이 방식으로 우회)
    @GetMapping
    public ResponseEntity<UserPreference> get(Authentication authentication) {
        User user = currentUser(authentication);
        return ResponseEntity.ok(preferenceRepository.findByUserId(user.getId()).orElse(null));
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}
