package com.promptune.service;

import com.promptune.domain.User;
import com.promptune.dto.AuthDtos.*;
import com.promptune.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

/** 회원가입·로그인 비즈니스 로직. */
@Service
public class AuthService {

    private final UserRepository users;
    private final PasswordEncoder encoder;   // BCrypt
    private final JwtService jwt;

    public AuthService(UserRepository users, PasswordEncoder encoder, JwtService jwt) {
        this.users = users;
        this.encoder = encoder;
        this.jwt = jwt;
    }

    /** 회원가입: 이메일 중복 확인 → 비밀번호 해싱 → 저장 → 토큰 발급 */
    public AuthResponse signup(SignupRequest req) {
        if (users.existsByEmail(req.email())) {
            throw new IllegalArgumentException("이미 가입된 이메일입니다.");
        }
        String hash = encoder.encode(req.password());       // 비밀번호 해싱
        User user = new User(req.email(), hash, req.name());
        users.save(user);
        String token = jwt.issue(user.getEmail());
        return new AuthResponse(token, user.getEmail(), user.getName());
    }

    /** 로그인: 사용자 조회 → 비밀번호 대조 → 토큰 발급 */
    public AuthResponse login(LoginRequest req) {
        User user = users.findByEmail(req.email())
                .orElseThrow(() -> new IllegalArgumentException("이메일 또는 비밀번호가 올바르지 않습니다."));
        if (!encoder.matches(req.password(), user.getPasswordHash())) {   // 해시 대조
            throw new IllegalArgumentException("이메일 또는 비밀번호가 올바르지 않습니다.");
        }
        String token = jwt.issue(user.getEmail());
        return new AuthResponse(token, user.getEmail(), user.getName());
    }
}
