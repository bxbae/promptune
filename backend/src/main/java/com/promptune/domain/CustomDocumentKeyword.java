package com.promptune.domain;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "custom_document_keyword")
public class CustomDocumentKeyword {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "company_id", nullable = false)
    private String companyId;

    @Column(nullable = false)
    private String keyword;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    protected CustomDocumentKeyword() {}

    public String getKeyword() { return keyword; }
}