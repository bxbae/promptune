package com.promptune.config;

import com.promptune.service.JwtService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.security.web.authentication.SimpleUrlAuthenticationSuccessHandler;
import org.springframework.stereotype.Component;
import java.io.IOException;
import java.util.Map;

/**
 * 소셜 로그인 성공 시: JWT 발급 → 프론트로 리다이렉트(토큰을 쿼리로 전달).
 * 프론트는 그 토큰을 저장해 로컬 로그인과 동일하게 처리.
 */
@Component
public class OAuth2SuccessHandler extends SimpleUrlAuthenticationSuccessHandler {

    private final JwtService jwt;
    private final String frontendUrl;

    public OAuth2SuccessHandler(JwtService jwt,
                                @Value("${app.frontend-url:http://localhost:3000}") String frontendUrl) {
        this.jwt = jwt;
        this.frontendUrl = frontendUrl;
    }

    @Override
    public void onAuthenticationSuccess(HttpServletRequest req, HttpServletResponse res,
                                        Authentication authentication) throws IOException {
        OAuth2User user = (OAuth2User) authentication.getPrincipal();
        Map<String, Object> attrs = user.getAttributes();

        // 이메일 추출 (제공자 무관하게 시도)
        String email = extractEmail(attrs);
        String token = email != null ? jwt.issue(email) : "";

        // 프론트로 토큰 전달하며 리다이렉트
        getRedirectStrategy().sendRedirect(req, res,
                frontendUrl + "/oauth/callback?token=" + token);
    }

    @SuppressWarnings("unchecked")
    private String extractEmail(Map<String, Object> attrs) {
        if (attrs.containsKey("email")) return (String) attrs.get("email");   // google
        if (attrs.containsKey("response")) {                                   // naver
            var r = (Map<String, Object>) attrs.get("response");
            return (String) r.get("email");
        }
        if (attrs.containsKey("kakao_account")) {                              // kakao
            var a = (Map<String, Object>) attrs.get("kakao_account");
            return (String) a.get("email");
        }
        return null;
    }
}
