package com.promptune.service;

import com.promptune.domain.User;
import com.promptune.repository.UserRepository;
import org.springframework.security.oauth2.client.userinfo.DefaultOAuth2UserService;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserRequest;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.stereotype.Service;
import java.util.Map;

/**
 * 소셜 로그인 시 사용자 정보를 받아 DB에 조회/자동가입.
 * 제공자(google/naver/kakao)마다 응답 형식이 달라 여기서 통일한다.
 */
@Service
public class OAuth2UserService extends DefaultOAuth2UserService {

    private final UserRepository users;

    public OAuth2UserService(UserRepository users) { this.users = users; }

    @Override
    public OAuth2User loadUser(OAuth2UserRequest req) {
        OAuth2User oAuth2User = super.loadUser(req);
        String provider = req.getClientRegistration().getRegistrationId();  // google/naver/kakao
        Map<String, Object> attrs = oAuth2User.getAttributes();

        // 제공자별 이메일·이름 추출 (형식이 다 다름)
        String email, name;
        switch (provider) {
            case "google" -> {
                email = (String) attrs.get("email");
                name = (String) attrs.get("name");
            }
            case "naver" -> {
                Map<String, Object> r = (Map<String, Object>) attrs.get("response");
                email = (String) r.get("email");
                name = (String) r.get("name");
            }
            case "kakao" -> {
                Map<String, Object> account = (Map<String, Object>) attrs.get("kakao_account");
                email = account != null ? (String) account.get("email") : null;
                Map<String, Object> profile = account != null ? (Map<String, Object>) account.get("profile") : null;
                name = profile != null ? (String) profile.get("nickname") : "카카오사용자";
            }
            default -> { email = null; name = "사용자"; }
        }

        // DB 조회, 없으면 자동 가입
        if (email != null) {
            users.findByEmail(email).orElseGet(() -> {
                User u = new User(email, null, name);   // 소셜은 비밀번호 없음
                return users.save(u);
            });
        }
        return oAuth2User;
    }
}
