package com.promptune.dto;

public class ReceiverProfileDtos {
    public record UpsertReceiverProfileRequest(String receiverName, String tone, Integer length) {}

    // ← 신규 추가: PATCH /api/receiver-profiles/{id} 요청 형식
    // 프론트가 relationship/preferredTone/receiverName을 보냄 (receiverName은 동명이인 통합
    // 시 더 완전한 이름으로 정정하는 용도로 신규 추가. avgLength, applyRate는 이 API로 수정 안 함)
    public record UpdateReceiverProfileRequest(String relationship, String preferredTone, String receiverName) {}
}