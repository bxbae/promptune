package com.promptune.dto;

/** 인증 요청·응답 DTO. */
public class AuthDtos {
    // 회원가입 요청
    public record SignupRequest(String email, String password, String name) {}
    // 로그인 요청
    public record LoginRequest(String email, String password) {}
    // 로그인·회원가입 응답 (토큰 + 기본 정보)
    public record AuthResponse(String token, String email, String name) {}
}
