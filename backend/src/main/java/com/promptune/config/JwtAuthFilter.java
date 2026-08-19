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
        System.out.println("[JWT DEBUG] " + req.getMethod() + " " + req.getRequestURI() + " / auth header 존재: " + (auth != null) + " / content-type: " + req.getContentType());
        if (auth != null && auth.startsWith("Bearer ")) {
            try {
                String email = jwt.validateAndGetEmail(auth.substring(7));
                var authentication = new UsernamePasswordAuthenticationToken(email, null, List.of());
                SecurityContextHolder.getContext().setAuthentication(authentication);
                System.out.println("[JWT DEBUG] 인증 성공: " + email);
            } catch (Exception e) {
                System.out.println("[JWT DEBUG] 인증 실패! 원인: " + e.getClass().getSimpleName() + " - " + e.getMessage());
                e.printStackTrace();
            }
        }
        chain.doFilter(req, res);
    }
}
