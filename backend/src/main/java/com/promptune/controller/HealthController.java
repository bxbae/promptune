package com.promptune.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 배포 헬스체크용. nginx가 /health를 이미 backend로 프록시하고 있고
 * SecurityConfig도 이미 permitAll 처리돼 있었으나 실제 구현이 없었음 (2026-09-01 확인).
 * DB/ai-service까지는 확인하지 않는 단순 liveness check.
 */
@RestController
public class HealthController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }
}
