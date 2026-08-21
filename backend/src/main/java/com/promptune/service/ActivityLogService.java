package com.promptune.service;

import com.promptune.domain.BehaviorLogEntity;
import com.promptune.domain.PromptSession;
import com.promptune.domain.ResponseEdit;
import com.promptune.dto.ActivityLogDtos.ActivityLogEntry;
import com.promptune.repository.BehaviorLogRepository;
import com.promptune.repository.PromptSessionRepository;
import com.promptune.repository.ResponseEditRepository;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Service
public class ActivityLogService {

    private final BehaviorLogRepository behaviorLogRepository;
    private final ResponseEditRepository responseEditRepository;
    private final PromptSessionRepository promptSessionRepository;

    public ActivityLogService(BehaviorLogRepository behaviorLogRepository,
            ResponseEditRepository responseEditRepository,
            PromptSessionRepository promptSessionRepository) {
        this.behaviorLogRepository = behaviorLogRepository;
        this.responseEditRepository = responseEditRepository;
        this.promptSessionRepository = promptSessionRepository;
    }

    // filter: null(전체) / "applied" / "rejected" / "edited"
    public List<ActivityLogEntry> list(Long userId, String filter) {
        List<ActivityLogEntry> result = new ArrayList<>();

        if (filter == null || filter.equals("applied") || filter.equals("rejected")) {
            for (BehaviorLogEntity log : behaviorLogRepository.findByUserId(userId)) {

                String type;

                if (BehaviorLogService.isApplyAction(log.getAction())) {
                    type = "applied";
                } else if (BehaviorLogService.isRejectAction(log.getAction())) {
                    type = "rejected";
                } else {
                    continue;
                }

                if (filter != null && !filter.equals(type)) {
                    continue;
                }

                String label = "applied".equals(type)
                        ? log.getElement() + " 적용"
                        : log.getElement() + " 거절";

                result.add(new ActivityLogEntry(
                        type,
                        label,
                        log.getChatSessionId(),
                        log.getCreatedAt()));
            }
        }

        if (filter == null || filter.equals("edited")) {
            for (ResponseEdit edit : responseEditRepository.findByUserId(userId)) {
                Long chatSessionId = promptSessionRepository.findById(edit.getPromptSessionId())
                        .map(PromptSession::getChatSessionId)
                        .orElse(null);
                result.add(new ActivityLogEntry("edited", "직접수정", chatSessionId, edit.getCreatedAt()));
            }
        }

        result.sort(Comparator.comparing(ActivityLogEntry::occurredAt).reversed());
        return result;
    }
}
