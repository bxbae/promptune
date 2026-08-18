package com.promptune.dto;

public class ConsentDtos {
    public record GrantConsentRequest(String consentType, Long receiverProfileId) {
        // consentType: "save"(저장 동의) / "no_save"(저장 안 함). receiverProfileId는 없으면 전체 동의.
    }
}
