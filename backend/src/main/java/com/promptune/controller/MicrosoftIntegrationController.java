package com.promptune.controller;

import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import com.promptune.service.MicrosoftGraphService;
import com.promptune.domain.User;
import com.promptune.repository.UserRepository;
import org.springframework.security.core.Authentication;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.net.URI;

@RestController
@RequestMapping("/api/integrations/microsoft")
public class MicrosoftIntegrationController {

    private final MicrosoftGraphService microsoftGraphService;
    private final UserRepository userRepository;

    public MicrosoftIntegrationController(
            MicrosoftGraphService microsoftGraphService,
            UserRepository userRepository) {
        this.microsoftGraphService = microsoftGraphService;
        this.userRepository = userRepository;
    }

    @GetMapping("/connect")
    public ResponseEntity<?> connect(Authentication authentication) {
        Long userId = currentUserId(authentication);
        String url = microsoftGraphService.createAuthorizationUrl(userId);
        return ResponseEntity.ok(java.util.Map.of("url", url));
    }

    @RequestMapping(value = "/callback", method = {RequestMethod.GET, RequestMethod.POST})
    public ResponseEntity<Void> callback(
            @RequestParam(required = false) String code,
            @RequestParam(required = false) String state,
            @RequestParam(required = false) String error) {
        String base = microsoftGraphService.getFrontendUrl() + "/settings";
        if (error != null && !error.isBlank()) {
            return redirect(base + "?microsoft=error");
        }
        if (code == null || code.isBlank() || state == null || state.isBlank()) {
            return redirect(base + "?microsoft=error");
        }
        try {
            microsoftGraphService.completeAuthorization(code, state);
            return redirect(base + "?microsoft=connected");
        } catch (ResponseStatusException e) {
            return redirect(base + "?microsoft=error");
        } catch (Exception e) {
            return redirect(base + "?microsoft=error");
        }
    }

    @GetMapping("/status")
    public ResponseEntity<?> status(Authentication authentication) {
        Long userId = currentUserId(authentication);
        return ResponseEntity.ok(microsoftGraphService.status(userId));
    }

    @GetMapping("/profile")
    public ResponseEntity<?> profile(Authentication authentication) {
        Long userId = currentUserId(authentication);
        return ResponseEntity.ok(microsoftGraphService.getProfile(userId));
    }

    @GetMapping("/events")
    public ResponseEntity<?> events(Authentication authentication) {
        Long userId = currentUserId(authentication);
        return ResponseEntity.ok(microsoftGraphService.getEvents(userId));
    }

    @GetMapping("/files")
    public ResponseEntity<?> files(Authentication authentication) {
        Long userId = currentUserId(authentication);
        return ResponseEntity.ok(microsoftGraphService.getFiles(userId));
    }

    @GetMapping("/messages")
    public ResponseEntity<?> messages(Authentication authentication) {
        Long userId = currentUserId(authentication);
        return ResponseEntity.ok(microsoftGraphService.getMessages(userId));
    }

    @DeleteMapping
    public ResponseEntity<?> disconnect(Authentication authentication) {
        Long userId = currentUserId(authentication);
        microsoftGraphService.disconnect(userId);
        return ResponseEntity.ok(java.util.Map.of("ok", true));
    }

    @GetMapping("/users")
    public ResponseEntity<?> organizationUsers(Authentication authentication) {
        Long userId = currentUserId(authentication);
        return ResponseEntity.ok(microsoftGraphService.getOrganizationUsers(userId));
    }

    private Long currentUserId(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(
                    HttpStatus.UNAUTHORIZED,
                    "로그인이 필요합니다."
            );
        }

        User user = userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.UNAUTHORIZED,
                        "사용자를 찾을 수 없습니다."
                ));

        return user.getId();
    }

    private ResponseEntity<Void> redirect(String url) {
        return ResponseEntity.status(HttpStatus.FOUND)
                .header(HttpHeaders.LOCATION, URI.create(url).toString())
                .build();
    }
}
