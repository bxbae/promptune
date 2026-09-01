package com.promptune.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;
import org.springframework.security.oauth2.client.registration.ClientRegistration;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.security.config.oauth2.client.CommonOAuth2Provider;
import org.springframework.security.oauth2.client.registration.InMemoryClientRegistrationRepository;
import org.springframework.security.oauth2.core.AuthorizationGrantType;
import org.springframework.security.oauth2.core.ClientAuthenticationMethod;

import java.util.ArrayList;
import java.util.List;

@Configuration
public class OAuth2ClientConfig {

    @Bean
    public ClientRegistrationRepository clientRegistrationRepository(
            Environment environment
    ) {
        List<ClientRegistration> registrations = new ArrayList<>();

        String redirectBase = value(
                environment,
                "OAUTH_REDIRECT_BASE",
                "http://localhost:8080"
        );

        addGoogle(environment, redirectBase, registrations);
        addNaver(environment, redirectBase, registrations);
        addKakao(environment, redirectBase, registrations);

        if (registrations.isEmpty()) {
            throw new IllegalStateException(
                    "At least one OAuth2 provider must have real credentials configured."
            );
        }

        return new InMemoryClientRegistrationRepository(registrations);
    }

    private void addGoogle(
            Environment environment,
            String redirectBase,
            List<ClientRegistration> registrations
    ) {
        String clientId = value(environment, "GOOGLE_CLIENT_ID", "");
        String clientSecret = value(environment, "GOOGLE_CLIENT_SECRET", "");

        if (!hasCredentials(clientId, clientSecret)) {
            return;
        }

        ClientRegistration registration = CommonOAuth2Provider.GOOGLE
                .getBuilder("google")
                .clientId(clientId)
                .clientSecret(clientSecret)
                .redirectUri(redirectBase + "/login/oauth2/code/google")
                .scope("profile", "email")
                .build();

        registrations.add(registration);
    }

    private void addNaver(
            Environment environment,
            String redirectBase,
            List<ClientRegistration> registrations
    ) {
        String clientId = value(environment, "NAVER_CLIENT_ID", "");
        String clientSecret = value(environment, "NAVER_CLIENT_SECRET", "");

        if (!hasCredentials(clientId, clientSecret)) {
            return;
        }

        ClientRegistration registration = ClientRegistration
                .withRegistrationId("naver")
                .clientId(clientId)
                .clientSecret(clientSecret)
                .clientName("Naver")
                .clientAuthenticationMethod(ClientAuthenticationMethod.CLIENT_SECRET_BASIC)
                .authorizationGrantType(AuthorizationGrantType.AUTHORIZATION_CODE)
                .redirectUri(redirectBase + "/login/oauth2/code/naver")
                .scope("name", "email")
                .authorizationUri("https://nid.naver.com/oauth2.0/authorize")
                .tokenUri("https://nid.naver.com/oauth2.0/token")
                .userInfoUri("https://openapi.naver.com/v1/nid/me")
                .userNameAttributeName("response")
                .build();

        registrations.add(registration);
    }

    private void addKakao(
            Environment environment,
            String redirectBase,
            List<ClientRegistration> registrations
    ) {
        String clientId = value(environment, "KAKAO_CLIENT_ID", "");
        String clientSecret = value(environment, "KAKAO_CLIENT_SECRET", "");

        if (!hasCredentials(clientId, clientSecret)) {
            return;
        }

        ClientRegistration registration = ClientRegistration
                .withRegistrationId("kakao")
                .clientId(clientId)
                .clientSecret(clientSecret)
                .clientName("Kakao")
                .clientAuthenticationMethod(ClientAuthenticationMethod.CLIENT_SECRET_POST)
                .authorizationGrantType(AuthorizationGrantType.AUTHORIZATION_CODE)
                .redirectUri(redirectBase + "/login/oauth2/code/kakao")
                .scope("profile_nickname", "account_email")
                .authorizationUri("https://kauth.kakao.com/oauth/authorize")
                .tokenUri("https://kauth.kakao.com/oauth/token")
                .userInfoUri("https://kapi.kakao.com/v2/user/me")
                .userNameAttributeName("id")
                .build();

        registrations.add(registration);
    }

    private boolean hasCredentials(String clientId, String clientSecret) {
        return clientId != null
                && !clientId.isBlank()
                && clientSecret != null
                && !clientSecret.isBlank();
    }

    private String value(
            Environment environment,
            String key,
            String defaultValue
    ) {
        String value = environment.getProperty(key);
        return value == null || value.isBlank() ? defaultValue : value;
    }
}
