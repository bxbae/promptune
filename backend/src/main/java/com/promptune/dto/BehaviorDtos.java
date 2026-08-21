package com.promptune.dto;

public class BehaviorDtos {

  public record BehaviorActionRequest(
      String element,
      String action,
      Long chatSessionId) {
  }

  private BehaviorDtos() {
  }
}