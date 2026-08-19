package com.promptune.dto;

public class DocumentDtos {
    public record UpdateDocumentRequest(String title, String description, String documentType) {}
}
