package com.promptune.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "prompt_sessions")
public class PromptSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "original_text", nullable = false, columnDefinition = "TEXT")
    private String originalText;

    @Column(name = "final_text", columnDefinition = "TEXT")
    private String finalText;

    @Column(name = "task_type")
    private String taskType;

    @Column(name = "chat_session_id")
    private Long chatSessionId;

    @Column(name = "receiver_profile_id")
    private Long receiverProfileId;

    @Column(name = "retrieval_route")
    private String retrievalRoute;

    private String satisfaction;   // 'good' / 'bad' / null

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "ai_response_text", columnDefinition = "TEXT")
    private String aiResponseText;

    protected PromptSession() {}

    public PromptSession(Long userId, String originalText, String finalText, String taskType, Long chatSessionId) {
        this(userId, originalText, finalText, taskType, chatSessionId, null);
    }

    public PromptSession(Long userId, String originalText, String finalText, String taskType, Long chatSessionId, Long receiverProfileId) {
        this.userId = userId;
        this.originalText = originalText;
        this.finalText = finalText;
        this.taskType = taskType;
        this.chatSessionId = chatSessionId;
        this.receiverProfileId = receiverProfileId;
        this.createdAt = LocalDateTime.now();
    }

    public Long getId() { return id; }
    public Long getUserId() { return userId; }
    public Long getChatSessionId() { return chatSessionId; }
    public Long getReceiverProfileId() { return receiverProfileId; }
    public String getTaskType() { return taskType; }
    public String getSatisfaction() { return satisfaction; }
    public void setSatisfaction(String satisfaction) { this.satisfaction = satisfaction; }
    public String getOriginalText() { return originalText; }
    public String getFinalText() { return finalText; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public String getAiResponseText() { return aiResponseText; }
    public void setAiResponseText(String aiResponseText) { this.aiResponseText = aiResponseText; }
    public String getRetrievalRoute() { return retrievalRoute; }
    public void setRetrievalRoute(String retrievalRoute) { this.retrievalRoute = retrievalRoute; }
}
