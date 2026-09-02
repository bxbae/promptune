package com.promptune.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "retrieval_pattern_score")
public class RetrievalPatternScore {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false)
    private String route;

    @Column(name = "use_count")
    private int useCount = 0;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();

    protected RetrievalPatternScore() {}

    public RetrievalPatternScore(Long userId, String route) {
        this.userId = userId;
        this.route = route;
    }

    public void incrementUse() {
        this.useCount++;
        this.updatedAt = LocalDateTime.now();
    }

    public Long getUserId() { return userId; }
    public String getRoute() { return route; }
    public int getUseCount() { return useCount; }
}
