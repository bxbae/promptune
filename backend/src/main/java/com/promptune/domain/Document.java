package com.promptune.domain;

import jakarta.persistence.*;

@Entity
@Table(name = "documents")
public class Document {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "owner_user_id", nullable = false)
    private Long ownerUserId;

    private String title;

    private String tag;   // '일반' 또는 '업무'

    @Column(name = "s3_key")
    private String s3Key;

    @Column(name = "file_type")
    private String fileType;

    protected Document() {}

    public Document(Long ownerUserId, String title, String tag, String s3Key, String fileType) {
        this.ownerUserId = ownerUserId;
        this.title = title;
        this.tag = tag;
        this.s3Key = s3Key;
        this.fileType = fileType;
    }

    public Long getId() { return id; }
    public Long getOwnerUserId() { return ownerUserId; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getTag() { return tag; }
    public void setTag(String tag) { this.tag = tag; }
    public String getS3Key() { return s3Key; }
    public String getFileType() { return fileType; }
}