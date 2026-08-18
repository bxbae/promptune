package com.promptune.controller;

import com.promptune.domain.User;
import com.promptune.dto.ActivityLogDtos.ActivityLogEntry;
import com.promptune.repository.UserRepository;
import com.promptune.service.ActivityLogService;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
@RequestMapping("/api/activity-logs")
public class ActivityLogController {

    private final ActivityLogService activityLogService;
    private final UserRepository userRepository;

    public ActivityLogController(ActivityLogService activityLogService, UserRepository userRepository) {
        this.activityLogService = activityLogService;
        this.userRepository = userRepository;
    }

    // 히스토리 > 수정이력 화면 (전체/적용/거절/직접수정 필터)
    @GetMapping
    public List<ActivityLogEntry> list(@RequestParam(required = false) String filter, Authentication authentication) {
        User user = currentUser(authentication);
        return activityLogService.list(user.getId(), filter);
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}
