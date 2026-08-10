package com.promptune.service;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import javax.crypto.SecretKey;
import java.util.Date;

/**
 * JWT 토큰 발급·검증.
 * 로그인 성공 시 토큰을 발급하고, 인증이 필요한 요청에서 토큰을 검증한다.
 */
@Service
public class JwtService {

    private final SecretKey key;
    private final long expirationMs;

    public JwtService(
            @Value("${jwt.secret:promptune-dev-secret-key-change-in-production-please}") String secret,
            @Value("${jwt.expiration-ms:86400000}") long expirationMs) {   // 기본 24시간
        this.key = Keys.hmacShaKeyFor(secret.getBytes());
        this.expirationMs = expirationMs;
    }

    /** 로그인 성공 시 토큰 발급 (subject = 사용자 이메일) */
    public String issue(String email) {
        Date now = new Date();
        return Jwts.builder()
                .subject(email)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + expirationMs))
                .signWith(key)
                .compact();
    }

    /** 토큰에서 이메일 추출 (검증 포함). 유효하지 않으면 예외. */
    public String validateAndGetEmail(String token) {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload()
                .getSubject();
    }
}
