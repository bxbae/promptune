package com.promptune.dto;

import java.time.LocalDateTime;

public class ActivityLogDtos {
    // type: "applied"(적용) / "rejected"(거절) / "edited"(직접수정)
    public record ActivityLogEntry(String type, String label, Long chatSessionId, LocalDateTime occurredAt) {}
}
