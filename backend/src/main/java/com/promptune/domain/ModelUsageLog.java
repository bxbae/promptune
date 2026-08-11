package com.promptune.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "model_usage_log")
public class ModelUsageLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String provider;
    private String endpoint;

    @Column(name = "response_time_ms")
    private int responseTimeMs;

    private String status;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    protected ModelUsageLog() {}

    public ModelUsageLog(String provider, String endpoint, int responseTimeMs, String status) {
        this.provider = provider;
        this.endpoint = endpoint;
        this.responseTimeMs = responseTimeMs;
        this.status = status;
    }
}