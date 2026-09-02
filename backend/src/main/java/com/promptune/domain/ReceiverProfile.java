package com.promptune.domain;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

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
    private String department;

    @Column(name = "preferred_tone")
    private String preferredTone;

    @Column(name = "avg_length")
    private int avgLength;

    @Column(name = "apply_rate")
    private BigDecimal applyRate;

    // MS 조직도에서 자동 동기화된 프로필인지. true면 department(및 이름)는 MS가 소스라
    // 히스토리 화면에서 사용자가 수정하지 못하게 막는다.
    @Column(name = "ms_synced", nullable = false)
    private boolean msSynced = false;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();

    protected ReceiverProfile() {}

    public ReceiverProfile(Long userId, String receiverName) {
        this.userId = userId;
        this.receiverName = receiverName;
    }

    public void setPreferredTone(String tone) { this.preferredTone = tone; this.updatedAt = LocalDateTime.now(); }
    public void setAvgLength(int length) { this.avgLength = length; }

    // ← 신규 추가: relationship 세터가 원래 없어서 못 고치고 있었음
    public void setRelationship(String relationship) { this.relationship = relationship; this.updatedAt = LocalDateTime.now(); }

    public Long getId() { return id; }
    public Long getUserId() { return userId; }
    public String getReceiverName() { return receiverName; }
    // ← 신규 추가: 동명이인 통합 시 더 완전한 이름(성+이름+직함)으로 갱신하는 용도.
    // updatedAt은 굳이 안 건드림 - 이름 정정일 뿐 학습 데이터가 바뀐 게 아니라서.
    public void setReceiverName(String receiverName) { this.receiverName = receiverName; }
    public String getRelationship() { return relationship; }
    public String getDepartment() { return department; }
    // department는 MS 조직도 동기화 값 — receiverName 정정과 같은 성격의
    // "사실 정보" 갱신이라 updatedAt(학습 시점)은 건드리지 않음.
    public void setDepartment(String department) { this.department = department; }
    public String getPreferredTone() { return preferredTone; }
    public int getAvgLength() { return avgLength; }
    public BigDecimal getApplyRate() { return applyRate; }
    public void setApplyRate(BigDecimal applyRate) { this.applyRate = applyRate; }
    public boolean isMsSynced() { return msSynced; }
    public void setMsSynced(boolean msSynced) { this.msSynced = msSynced; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
}
