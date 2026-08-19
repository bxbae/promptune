package com.promptune.controller;

import com.promptune.dto.PipelineDtos.DiagnoseResult;
import com.promptune.dto.PipelineDtos.ImproveRequest;
import com.promptune.dto.PipelineDtos.ImproveResponse;
import com.promptune.dto.PipelineDtos.PreferenceResult;
import com.promptune.dto.PipelineDtos.PromptRuleResult;
import com.promptune.service.AiServiceClient;
import com.promptune.service.PreferenceResolutionService;

import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Phase 2-B 프롬프트 개선 준비 API.
 *
 * 흐름:
 * Authentication
 * → 사용자 Preference 조회
 * → V6 프롬프트 진단
 * → Prompt Rule 적용
 *
 * HyperCLOVA 기반 실제 개선 프롬프트 생성은 다음 Phase에서 연결한다.
 */
@RestController
@RequestMapping("/api")
public class ImproveController {

  private final AiServiceClient ai;
  private final PreferenceResolutionService preferenceResolutionService;

  public ImproveController(
      AiServiceClient ai,
      PreferenceResolutionService preferenceResolutionService) {
    this.ai = ai;
    this.preferenceResolutionService = preferenceResolutionService;
  }

  @PostMapping("/improve")
  public ImproveResponse improve(
      @RequestBody ImproveRequest req,
      Authentication authentication) {

    var preference = preferenceResolutionService.resolve(authentication);

    DiagnoseResult diagnose = ai.diagnose(req.text());

    PromptRuleResult promptRule = ai.promptRule(
        req.text(),
        diagnose.missing(),
        diagnose.taskType(),
        preference.speed(),
        preference.detail(),
        preference.preserve());

    PreferenceResult preferenceResult = new PreferenceResult(
        preference.speed(),
        preference.detail(),
        preference.preserve(),
        preference.fromLoggedInUser());

    return new ImproveResponse(
        preferenceResult,
        diagnose,
        promptRule);
  }
}