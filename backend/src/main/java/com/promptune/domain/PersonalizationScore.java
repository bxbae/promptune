package com.promptune.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "personalization_score")
public class PersonalizationScore {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false)
    private String element;

    @Column(name = "accept_count")
    private int acceptCount = 0;

    @Column(name = "dismiss_count")
    private int dismissCount = 0;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();

    protected PersonalizationScore() {}   // JPA 기본 생성자

    public PersonalizationScore(Long userId, String element) {
        this.userId = userId;
        this.element = element;
    }

    public void incrementAccept() { this.acceptCount++; this.updatedAt = LocalDateTime.now(); }
    public void incrementDismiss() { this.dismissCount++; this.updatedAt = LocalDateTime.now(); }

    public int getAcceptCount() { return acceptCount; }
    public int getDismissCount() { return dismissCount; }
}