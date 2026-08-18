package com.promptune.dto;

public class ReceiverProfileDtos {
    public record UpsertReceiverProfileRequest(String receiverName, String tone, Integer length) {}
}
