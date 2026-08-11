package com.promptune.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.microsoft.aad.msal4j.*;
import com.promptune.domain.MicrosoftConnection;
import com.promptune.domain.MicrosoftOauthState;
import com.promptune.repository.MicrosoftConnectionRepository;
import com.promptune.repository.MicrosoftOauthStateRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

import java.net.URI;
import java.time.Instant;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
public class MicrosoftGraphService {

    private static final Set<String> SCOPES = Set.of(
            "User.Read",
            "Mail.Read",
            "Calendars.Read",
            "Files.Read",
            "offline_access"
    );

    private final MicrosoftConnectionRepository connectionRepository;
    private final MicrosoftOauthStateRepository oauthStateRepository;
    private final TokenCryptoService tokenCryptoService;
    private final RestClient graphClient = RestClient.create();

    public MicrosoftGraphService(
            MicrosoftConnectionRepository connectionRepository,
            MicrosoftOauthStateRepository oauthStateRepository,
            TokenCryptoService tokenCryptoService
    ) {
        this.connectionRepository = connectionRepository;
        this.oauthStateRepository = oauthStateRepository;
        this.tokenCryptoService = tokenCryptoService;
    }

    @Value("${microsoft.client-id:}")
    private String clientId;

    @Value("${microsoft.client-secret:}")
    private String clientSecret;

    @Value("${microsoft.tenant:common}")
    private String tenant;

    @Value("${microsoft.redirect-uri:http://localhost:8080/api/integrations/microsoft/callback}")
    private String redirectUri;

    @Value("${microsoft.frontend-url:http://localhost:3000}")
    private String frontendUrl;

    public String getFrontendUrl() {
        return frontendUrl;
    }

    @Transactional
    public String createAuthorizationUrl(Long userId) {
        requireMicrosoftConfig();
        String state = UUID.randomUUID().toString();
        oauthStateRepository.save(
                new MicrosoftOauthState(
                        state,
                        userId,
                        Instant.now().plusSeconds(600)
                )
        );

        ConfidentialClientApplication app = buildClient();
        AuthorizationRequestUrlParameters params = AuthorizationRequestUrlParameters
                .builder(redirectUri, SCOPES)
                .responseMode(ResponseMode.FORM_POST)
                .prompt(Prompt.SELECT_ACCOUNT)
                .state(state)
                .build();
        return app.getAuthorizationRequestUrl(params).toString();
    }

    @Transactional
    public void completeAuthorization(String code, String state) {
        requireMicrosoftConfig();
        MicrosoftOauthState oauthState = oauthStateRepository.findById(state)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "유효하지 않은 OAuth state입니다."));
        if (oauthState.getExpiresAt().isBefore(Instant.now())) {
            oauthStateRepository.delete(oauthState);
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "OAuth state가 만료되었습니다.");
        }
        oauthStateRepository.delete(oauthState);

        Long userId = oauthState.getUserId();
        ConfidentialClientApplication app = buildClient();
        AuthorizationCodeParameters authParams = AuthorizationCodeParameters
                .builder(code, URI.create(redirectUri))
                .scopes(SCOPES)
                .build();

        IAuthenticationResult authResult;
        try {
            authResult = app.acquireToken(authParams).join();
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Microsoft 인증 코드 교환에 실패했습니다.");
        }

        JsonNode profile = fetchGraph("/v1.0/me", authResult.accessToken());
        String microsoftUserId = profile.path("id").asText(null);
        String displayName = profile.path("displayName").asText(null);
        String email = resolveEmail(profile);

        String serializedCache = app.tokenCache().serialize();
        String encryptedCache = tokenCryptoService.encrypt(serializedCache);

        MicrosoftConnection connection = connectionRepository.findById(userId)
                .orElse(new MicrosoftConnection(userId));
        connection.setMicrosoftUserId(microsoftUserId);
        connection.setMicrosoftEmail(email);
        connection.setDisplayName(displayName);
        connection.setTokenCacheEncrypted(encryptedCache);
        connectionRepository.save(connection);
    }

    public Map<String, Object> status(Long userId) {
        return connectionRepository.findById(userId)
                .map(c -> Map.<String, Object>of(
                        "connected", true,
                        "microsoftEmail", c.getMicrosoftEmail() != null ? c.getMicrosoftEmail() : "",
                        "displayName", c.getDisplayName() != null ? c.getDisplayName() : ""))
                .orElse(Map.of("connected", false));
    }

    @Transactional
    public void disconnect(Long userId) {
        connectionRepository.deleteById(userId);
    }

    public JsonNode getProfile(Long userId) {
        return graphGet(
                userId,
                "/v1.0/me?$select=id,displayName,userPrincipalName,mail,companyName,department,jobTitle"
        );
    }

    public JsonNode getEvents(Long userId) {
        return graphGet(userId, "/v1.0/me/events?$top=10");
    }

    public JsonNode getFiles(Long userId) {
        return graphGet(userId, "/v1.0/me/drive/root/children?$top=10");
    }

    public JsonNode getMessages(Long userId) {
        return graphGet(userId, "/v1.0/me/messages?$top=10");
    }

    private JsonNode graphGet(Long userId, String path) {
        String accessToken = getAccessToken(userId);
        return fetchGraph(path, accessToken);
    }

    @Transactional
    String getAccessToken(Long userId) {
        MicrosoftConnection connection = connectionRepository.findById(userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Microsoft 계정이 연결되어 있지 않습니다."));

        String decryptedCache = tokenCryptoService.decrypt(connection.getTokenCacheEncrypted());
        ConfidentialClientApplication app = buildClient();
        app.tokenCache().deserialize(decryptedCache);

        Set<IAccount> accounts;
        try {
            accounts = app.getAccounts().join();
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Microsoft 토큰 캐시를 읽을 수 없습니다.");
        }
        if (accounts.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Microsoft 계정 정보가 없습니다. 다시 연결하세요.");
        }

        IAccount account = accounts.iterator().next();
        SilentParameters silentParams = SilentParameters.builder(SCOPES)
                .account(account)
                .build();

        IAuthenticationResult result;
        try {
            result = app.acquireTokenSilently(silentParams).join();
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Microsoft 액세스 토큰 갱신에 실패했습니다. 다시 연결하세요.");
        }

        String updatedCache = app.tokenCache().serialize();
        if (!updatedCache.equals(decryptedCache)) {
            connection.setTokenCacheEncrypted(tokenCryptoService.encrypt(updatedCache));
            connectionRepository.save(connection);
        }

        return result.accessToken();
    }

    private JsonNode fetchGraph(String path, String accessToken) {
        try {
            return graphClient.get()
                    .uri("https://graph.microsoft.com" + path)
                    .header("Authorization", "Bearer " + accessToken)
                    .retrieve()
                    .body(JsonNode.class);
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Microsoft Graph API 호출에 실패했습니다.");
        }
    }

    private String resolveEmail(JsonNode profile) {
        if (profile.hasNonNull("mail") && !profile.get("mail").asText().isBlank()) {
            return profile.get("mail").asText();
        }
        if (profile.hasNonNull("userPrincipalName")) {
            return profile.get("userPrincipalName").asText();
        }
        return null;
    }

    private ConfidentialClientApplication buildClient() {
        requireMicrosoftConfig();
        try {
            return ConfidentialClientApplication.builder(
                            clientId,
                            ClientCredentialFactory.createFromSecret(clientSecret))
                    .authority(authority())
                    .build();
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Microsoft 클라이언트 초기화에 실패했습니다.");
        }
    }

    private String authority() {
        return "https://login.microsoftonline.com/" + tenant;
    }

    private void requireMicrosoftConfig() {
        if (clientId == null || clientId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "Microsoft 연결 기능이 설정되지 않았습니다. MICROSOFT_CLIENT_ID를 설정하세요.");
        }
        if (clientSecret == null || clientSecret.isBlank()) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "Microsoft 연결 기능이 설정되지 않았습니다. MICROSOFT_CLIENT_SECRET을 설정하세요.");
        }
        if (redirectUri == null || redirectUri.isBlank()) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "Microsoft 연결 기능이 설정되지 않았습니다. MICROSOFT_REDIRECT_URI를 설정하세요.");
        }
        tokenCryptoService.validateKeyConfigured();
    }
}
