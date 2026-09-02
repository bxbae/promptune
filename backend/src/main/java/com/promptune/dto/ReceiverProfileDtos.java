package com.promptune.dto;

public class ReceiverProfileDtos {
    public record UpsertReceiverProfileRequest(String receiverName, String tone, Integer length) {}

    // 2026-09-02: department 추가 — MS 구성원 프로필 자동연동 시 이름+직함+부서를
    // 함께 저장하기 위함. relationship(사용자와의 관계)과는 의미가 다른 별도 정보.
    // 프론트가 relationship/department/preferredTone을 보냄 (avgLength, applyRate는 이 API로 수정 안 함)
    public record UpdateReceiverProfileRequest(String relationship, String department, String preferredTone, String receiverName) {}
}