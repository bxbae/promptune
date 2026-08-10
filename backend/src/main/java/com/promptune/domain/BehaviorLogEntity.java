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

    public BehaviorLogEntity(Long userId, String element, String action) {
        this.userId = userId;
        this.element = element;
        this.action = action;
    }
}