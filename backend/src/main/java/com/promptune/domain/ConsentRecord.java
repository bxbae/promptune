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

    protected ConsentRecord() {}

    public ConsentRecord(Long userId, String consentType) {
        this.userId = userId;
        this.consentType = consentType;
    }

    public String getConsentType() { return consentType; }
    public LocalDateTime getRevokedAt() { return revokedAt; }
}