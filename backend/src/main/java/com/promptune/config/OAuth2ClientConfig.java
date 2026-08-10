package com.promptune.config;

import org.springframework.boot.autoconfigure.security.oauth2.client.OAuth2ClientProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.client.registration.ClientRegistration;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.security.oauth2.client.registration.InMemoryClientRegistrationRepository;
import org.springframework.boot.autoconfigure.security.oauth2.client.OAuth2ClientPropertiesMapper;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 소셜 로그인 제공자 등록.
 * ★ 핵심: client-id가 비어있는 제공자는 자동으로 제외한다.
 *   → 키를 아직 안 넣은 제공자가 있어도 앱이 정상 기동한다.
 *   → 병환님이 나중에 환경변수로 키를 넣으면 그 제공자가 자동 활성화됨.
 */
@Configuration
@EnableConfigurationProperties(OAuth2ClientProperties.class)
public class OAuth2ClientConfig {

    @Bean
    public ClientRegistrationRepository clientRegistrationRepository(OAuth2ClientProperties properties) {
        List<ClientRegistration> registrations = new ArrayList<>(
                new OAuth2ClientPropertiesMapper(properties).asClientRegistrations().values());

        // client-id가 빈 제공자 제거 (키 미설정 시 기동 실패 방지)
        registrations.removeIf(r -> r.getClientId() == null || r.getClientId().isBlank());

        if (registrations.isEmpty()) {
            // 소셜 제공자가 하나도 없어도 앱은 떠야 함 → 더미 하나 등록
            return new InMemoryClientRegistrationRepository(List.of(dummyRegistration()));
        }
        return new InMemoryClientRegistrationRepository(registrations);
    }

    // 소셜 키가 전혀 없을 때를 위한 더미 (실제로 안 쓰임)
    private ClientRegistration dummyRegistration() {
        return ClientRegistration.withRegistrationId("none")
                .clientId("none").clientSecret("none")
                .authorizationGrantType(org.springframework.security.oauth2.core.AuthorizationGrantType.CLIENT_CREDENTIALS)
                .tokenUri("http://localhost/none")
                .build();
    }
}
