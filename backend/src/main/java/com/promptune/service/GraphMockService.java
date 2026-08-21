package com.promptune.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.promptune.domain.MicrosoftConnection;
import com.promptune.repository.MicrosoftConnectionRepository;
import com.promptune.repository.UserPreferenceRepository;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 4번 업무맥락 — department/jobTitle은 microsoft_connections에 캐싱된 값 사용,
 * upcomingEvents는 계속 바뀌는 정보라 캐싱하지 않고 매번 MS Graph 실시간 호출.
 * 0번 첫방문 여부는 user_preferences 존재 여부로 판단.
 */
@Service
public class GraphMockService {

    private final UserPreferenceRepository userPreferenceRepository;
    private final MicrosoftConnectionRepository microsoftConnectionRepository;
    private final MicrosoftGraphService microsoftGraphService;

    public GraphMockService(UserPreferenceRepository userPreferenceRepository,
                             MicrosoftConnectionRepository microsoftConnectionRepository,
                             MicrosoftGraphService microsoftGraphService) {
        this.userPreferenceRepository = userPreferenceRepository;
        this.microsoftConnectionRepository = microsoftConnectionRepository;
        this.microsoftGraphService = microsoftGraphService;
    }

    // 4번: 업무 맥락 조회 — 부서/직급은 DB 캐싱, 일정은 실시간 조회
    public Map<String, Object> getUserContext(Long userId) {
        var connectionOpt = microsoftConnectionRepository.findById(userId);

        if (connectionOpt.isEmpty()) {
            return Map.of(
                    "msConnected", false,
                    "department", "",
                    "position", "",
                    "upcomingEvents", List.of()
            );
        }

        MicrosoftConnection connection = connectionOpt.get();
        String department = connection.getDepartment() != null ? connection.getDepartment() : "";
        String position = connection.getJobTitle() != null ? connection.getJobTitle() : "";

        List<Map<String, Object>> upcomingEvents = new ArrayList<>();
        try {
            JsonNode events = microsoftGraphService.getEvents(userId);
            for (JsonNode event : events.path("value")) {
                upcomingEvents.add(Map.of(
                        "title", event.path("subject").asText(""),
                        "when", event.path("start").path("dateTime").asText("")
                ));
            }
        } catch (Exception e) {
            // 토큰 만료 등으로 실패해도 부서/직급 정보는 정상 노출, 일정만 빈 배열로 처리
        }

        return Map.of(
                "msConnected", true,
                "department", department,
                "position", position,
                "upcomingEvents", upcomingEvents
        );
    }

    // 0번: 첫 방문 여부 — 온보딩(user_preferences) 완료 여부로 실제 판단
    public boolean isFirstVisit(Long userId) {
        return userPreferenceRepository.findByUserId(userId).isEmpty();
    }
}