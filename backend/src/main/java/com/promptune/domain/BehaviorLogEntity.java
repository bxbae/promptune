package com.promptune.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "behavior_logs")
public class BehaviorLogEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    private String element;
    private String action;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    protected BehaviorLogEntity() {}

    @Column(name = "chat_session_id")
    private Long chatSessionId;

    public BehaviorLogEntity(Long userId, String element, String action) {
        this.userId = userId;
        this.element = element;
        this.action = action;
    }

    public BehaviorLogEntity(Long userId, String element, String action, Long chatSessionId) {
        this(userId, element, action);
        this.chatSessionId = chatSessionId;
    }

    public String getElement() { return element; }
    public String getAction() { return action; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public Long getChatSessionId() { return chatSessionId; }
}
