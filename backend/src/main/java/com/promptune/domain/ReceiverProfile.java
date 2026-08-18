package com.promptune.domain;

import java.math.BigDecimal;
import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "receiver_profile")
public class ReceiverProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "receiver_name", nullable = false)
    private String receiverName;

    private String relationship;

    @Column(name = "preferred_tone")
    private String preferredTone;

    @Column(name = "avg_length")
    private int avgLength;

    @Column(name = "apply_rate")
    private BigDecimal applyRate;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();

    protected ReceiverProfile() {}

    public ReceiverProfile(Long userId, String receiverName) {
        this.userId = userId;
        this.receiverName = receiverName;
    }

    public void setPreferredTone(String tone) { this.preferredTone = tone; this.updatedAt = LocalDateTime.now(); }
    public void setAvgLength(int length) { this.avgLength = length; }

    public Long getId() { return id; }
    public Long getUserId() { return userId; }
    public String getReceiverName() { return receiverName; }
    public String getRelationship() { return relationship; }
    public String getPreferredTone() { return preferredTone; }
    public int getAvgLength() { return avgLength; }
    public BigDecimal getApplyRate() { return applyRate; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
}
