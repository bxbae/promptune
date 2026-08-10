package com.promptune.service;

import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Map;

/**
 * 0,4번 인증·업무맥락 (mock).
 *
 * TODO(승연): mock 세션·샘플 일정 → Spring Security OAuth2 + MS Graph API 실제 호출.
 *   getUserContext 반환 형식(department/position/upcomingEvents) 유지.
 */
@Service
public class GraphMockService {

    // 4번: 업무 맥락 조회 (직급·부서·가까운 일정)
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

    // 0번: 로그인 (mock 세션)
    public boolean isFirstVisit(Long userId) {
        // TODO(승연): 실제로는 DB에서 사용자 데이터 존재 여부 확인
        return userId == null || userId == 0L;
    }
}
