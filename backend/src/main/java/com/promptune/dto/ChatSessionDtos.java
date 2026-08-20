package com.promptune.dto;

import java.time.LocalDateTime;

public class ChatSessionDtos {
    public record UpdateTitleRequest(String title) {}
    public record MessageResponse(Long id, String prompt, String aiResponse, String taskType, LocalDateTime createdAt, String satisfaction) {}
}
