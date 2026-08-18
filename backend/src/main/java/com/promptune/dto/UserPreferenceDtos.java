package com.promptune.dto;

public class UserPreferenceDtos {
    public record UpsertPreferenceRequest(String speed, String detail, String preserve) {}
}
