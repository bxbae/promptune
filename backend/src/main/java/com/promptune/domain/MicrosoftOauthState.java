package com.promptune.domain;

import jakarta.persistence.*;

import java.time.Instant;

@Entity
@Table(name = "microsoft_oauth_states")
public class MicrosoftOauthState {

    @Id
    @Column(length = 36)
    private String state;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    protected MicrosoftOauthState() {
    }

    public MicrosoftOauthState(
            String state,
            Long userId,
            Instant expiresAt
    ) {
        this.state = state;
        this.userId = userId;
        this.expiresAt = expiresAt;
    }

    @PrePersist
    void onCreate() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
    }

    public String getState() {
        return state;
    }

    public Long getUserId() {
        return userId;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getExpiresAt() {
        return expiresAt;
    }
}
