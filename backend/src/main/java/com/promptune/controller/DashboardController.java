package com.promptune.controller;

import com.promptune.domain.BehaviorLogEntity;
import com.promptune.domain.PersonalizationScore;
import com.promptune.domain.PromptSession;
import com.promptune.domain.User;
import com.promptune.repository.BehaviorLogRepository;
import com.promptune.repository.PersonalizationScoreRepository;
import com.promptune.repository.PromptSessionRepository;
import com.promptune.repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {

    private final PersonalizationScoreRepository personalizationScoreRepository;
    private final BehaviorLogRepository behaviorLogRepository;
    private final PromptSessionRepository promptSessionRepository;
    private final UserRepository userRepository;

    public DashboardController(PersonalizationScoreRepository personalizationScoreRepository,
                                BehaviorLogRepository behaviorLogRepository,
                                PromptSessionRepository promptSessionRepository,
                                UserRepository userRepository) {
        this.personalizationScoreRepository = personalizationScoreRepository;
        this.behaviorLogRepository = behaviorLogRepository;
        this.promptSessionRepository = promptSessionRepository;
        this.userRepository = userRepository;
    }

    // 8요소별 포함률 = accept / (accept + dismiss)
    @GetMapping("/element-coverage")
    public List<Map<String, Object>> elementCoverage(Authentication authentication) {
        User user = currentUser(authentication);
        return personalizationScoreRepository.findByUserId(user.getId()).stream()
                .map(this::toCoverageEntry)
                .collect(Collectors.toList());
    }

    private Map<String, Object> toCoverageEntry(PersonalizationScore s) {
        int total = s.getAcceptCount() + s.getDismissCount();
        double rate = total == 0 ? 0.0 : (double) s.getAcceptCount() / total;
        return Map.of(
                "element", s.getElement(),
                "acceptCount", s.getAcceptCount(),
                "dismissCount", s.getDismissCount(),
                "coverageRate", rate
        );
    }

    // 추천 적용률 = tab(적용) 로그 수 / 전체 로그 수
    @GetMapping("/apply-rate")
    public Map<String, Object> applyRate(Authentication authentication) {
        User user = currentUser(authentication);
        List<BehaviorLogEntity> logs = behaviorLogRepository.findByUserId(user.getId());
        long total = logs.size();
        long applied = logs.stream().filter(l -> "tab".equals(l.getAction())).count();
        double rate = total == 0 ? 0.0 : (double) applied / total;
        return Map.of("total", total, "applied", applied, "applyRate", rate);
    }

    // 주간 활동 추이 = 최근 7일 일별 프롬프트 세션 개수
    @GetMapping("/weekly-activity")
    public Map<String, Long> weeklyActivity(Authentication authentication) {
        User user = currentUser(authentication);
        LocalDateTime since = LocalDate.now().minusDays(6).atStartOfDay();
        return promptSessionRepository.findByUserId(user.getId()).stream()
                .filter(p -> p.getCreatedAt() != null && !p.getCreatedAt().isBefore(since))
                .collect(Collectors.groupingBy(
                        p -> p.getCreatedAt().toLocalDate().toString(),
                        Collectors.counting()
                ));
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}
