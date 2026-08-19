package com.promptune.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "user_preferences")
public class UserPreference {

    @Id
    @Column(name = "user_id")
    private Long userId;

    private String speed;      // 'fast' / 'accurate'
    private String detail;     // 'brief' / 'detailed'
    private String preserve;   // 'keep' / 'improve'

    protected UserPreference() {}   // JPA 기본 생성자

    public UserPreference(Long userId, String speed, String detail, String preserve) {
        this.userId = userId;
        this.speed = speed;
        this.detail = detail;
        this.preserve = preserve;
    }

    public Long getUserId() { return userId; }
    public String getSpeed() { return speed; }
    public String getDetail() { return detail; }
    public String getPreserve() { return preserve; }

    public void update(String speed, String detail, String preserve) {
        this.speed = speed;
        this.detail = detail;
        this.preserve = preserve;
    }
}
