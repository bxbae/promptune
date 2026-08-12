package com.promptune.controller;

import com.promptune.domain.User;
import com.promptune.dto.UserDtos.UpdateCompanyRequest;
import com.promptune.repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserRepository userRepository;

    public UserController(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @PutMapping("/company")
    public ResponseEntity<?> updateCompany(@RequestBody UpdateCompanyRequest req, Authentication authentication) {
        User user = currentUser(authentication);
        user.setCompanyId(req.companyId());
        userRepository.save(user);
        return ResponseEntity.ok(java.util.Map.of("ok", true, "companyId", user.getCompanyId()));
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}