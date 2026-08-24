package com.promptune.dto;

public class ReceiverProfileDtos {
    public record UpsertReceiverProfileRequest(String receiverName, String tone, Integer length) {}

    // ← 신규 추가: PATCH /api/receiver-profiles/{id} 요청 형식
    // 프론트가 relationship/preferredTone만 보냄 (avgLength, applyRate는 이 API로 수정 안 함)
    public record UpdateReceiverProfileRequest(String relationship, String preferredTone) {}
}