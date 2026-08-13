package com.promptune.dto;

public class DocumentDtos {
    public record UploadDocumentRequest(String title, String tag, String content, String fileType) {}
    public record UpdateDocumentRequest(String title, String tag) {}
}
