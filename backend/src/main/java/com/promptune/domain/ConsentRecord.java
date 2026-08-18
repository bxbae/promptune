package com.promptune.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "consent_records")
public class ConsentRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "consent_type")
    private String consentType;

    @Column(name = "granted_at")
    private LocalDateTime grantedAt = LocalDateTime.now();

    @Column(name = "revoked_at")
    private LocalDateTime revokedAt;

    @Column(name = "receiver_profile_id")
    private Long receiverProfileId;

    protected ConsentRecord() {}

    // 전체(사용자 단위) 동의용 — 기존 그대로
    public ConsentRecord(Long userId, String consentType) {
        this.userId = userId;
        this.consentType = consentType;
    }

    // 수신자별 동의용 (신규)
    public ConsentRecord(Long userId, String consentType, Long receiverProfileId) {
        this.userId = userId;
        this.consentType = consentType;
        this.receiverProfileId = receiverProfileId;
    }

    public String getConsentType() { return consentType; }
    public LocalDateTime getRevokedAt() { return revokedAt; }
    public Long getReceiverProfileId() { return receiverProfileId; }
}