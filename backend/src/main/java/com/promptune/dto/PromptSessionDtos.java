package com.promptune.dto;

public class PromptSessionDtos {
    public record SubmitEditRequest(
        String generatedResult,
        String userFinalResult,
        String satisfaction   // "good" / "bad" / null, 선택사항
    ) {}
}
