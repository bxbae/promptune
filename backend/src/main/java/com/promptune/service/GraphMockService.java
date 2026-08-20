package com.promptune.service;

import com.promptune.repository.UserPreferenceRepository;
import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Map;

/**
 * 4번 업무맥락(mock, 승연님 담당 — 실제 MS Graph 연동 예정, 로드맵 B그룹 참고).
 * 0번 첫방문 여부는 오늘부로 실제 로직으로 전환함 (user_preferences 존재 여부 기준).
 *
 * TODO(승연): getUserContext는 아직 mock. Spring Security OAuth2 + MS Graph API 실제 호출로 교체 예정.
 *   반환 형식(department/position/upcomingEvents)은 유지.
 */
@Service
public class GraphMockService {

    private final UserPreferenceRepository userPreferenceRepository;

    public GraphMockService(UserPreferenceRepository userPreferenceRepository) {
        this.userPreferenceRepository = userPreferenceRepository;
    }

    // 4번: 업무 맥락 조회 (직급·부서·가까운 일정) — 아직 mock, 승연님 담당
    public Map<String, Object> getUserContext(Long userId) {
        return Map.of(
                "department", "마케팅팀",
                "position", "사원",
                "upcomingEvents", List.of(
                        Map.of("title", "주간 팀 회의", "when", "내일 10:00"),
                        Map.of("title", "분기 실적 보고", "when", "금요일 14:00")
                )
        );
    }

    // 0번: 첫 방문 여부 — 온보딩(user_preferences) 완료 여부로 실제 판단
    public boolean isFirstVisit(Long userId) {
        return userPreferenceRepository.findByUserId(userId).isEmpty();
    }
}