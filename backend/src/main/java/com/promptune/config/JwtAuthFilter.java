package com.promptune.config;

import com.promptune.service.JwtService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import java.io.IOException;
import java.util.List;

/** 요청 헤더의 JWT를 검증해 인증 상태를 설정하는 필터. */
@Component
public class JwtAuthFilter extends OncePerRequestFilter {

    private final JwtService jwt;

    public JwtAuthFilter(JwtService jwt) { this.jwt = jwt; }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String auth = req.getHeader("Authorization");
        if (auth != null && auth.startsWith("Bearer ")) {
            try {
                String email = jwt.validateAndGetEmail(auth.substring(7));
                var authentication = new UsernamePasswordAuthenticationToken(email, null, List.of());
                SecurityContextHolder.getContext().setAuthentication(authentication);
            } catch (Exception e) {
                // 토큰이 없거나 유효하지 않으면 인증 없이 통과시키고, 이후 SecurityConfig의
                // 인가 규칙(permitAll이 아닌 엔드포인트는 401)이 알아서 처리한다.
                // 2026-09-02: 디버그용 println/printStackTrace 제거 — 요청마다 사용자
                // 이메일이 평문으로 로그에 계속 쌓이고 있던 것 확인되어 정리함.
            }
        }
        chain.doFilter(req, res);
    }
}
