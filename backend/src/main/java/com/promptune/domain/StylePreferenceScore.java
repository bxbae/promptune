package com.promptune.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "style_preference_score")
public class StylePreferenceScore {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false)
    private String field;

    @Column(nullable = false)
    private String value;

    @Column(name = "use_count")
    private int useCount = 0;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();

    protected StylePreferenceScore() {}

    public StylePreferenceScore(Long userId, String field, String value) {
        this.userId = userId;
        this.field = field;
        this.value = value;
    }

    public void incrementUse() {
        this.useCount++;
        this.updatedAt = LocalDateTime.now();
    }

    public Long getUserId() { return userId; }
    public String getField() { return field; }
    public String getValue() { return value; }
    public int getUseCount() { return useCount; }
}