package com.promptune.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

/** 사용자 엔티티. users 테이블과 매핑. */
@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String email;

    @Column(name = "password_hash")
    private String passwordHash;      // BCrypt 해시 (로컬 로그인만)

    private String name;
    private String department;
    private String position;

    private String provider = "local";   // local / google / kakao / naver

    @Column(name = "provider_id")
    private String providerId;

    @Column(name = "company_id")
    private String companyId;             // 신규: 12번 요청분류에서 사용

    public String getCompanyId() { return companyId; }   // getter도 추가

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    protected User() {}   // JPA 기본 생성자

    public User(String email, String passwordHash, String name, String companyId) {
    this.email = email;
    this.passwordHash = passwordHash;
    this.name = name;
    this.provider = "local";
    this.companyId = (companyId == null || companyId.isBlank()) ? "default-company" : companyId;
}

    // getter
    public Long getId() { return id; }
    public String getEmail() { return email; }
    public String getPasswordHash() { return passwordHash; }
    public String getName() { return name; }
    public String getProvider() { return provider; }
    public void setCompanyId(String companyId) { this.companyId = companyId; }
}
