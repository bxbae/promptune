package com.promptune.dto;

public class UserDtos {
    public record UpdateCompanyRequest(String companyId) {}
    public record UpdateNameRequest(String name) {}
}