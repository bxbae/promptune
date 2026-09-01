package com.promptune.service;

import org.springframework.stereotype.Service;

/**
 * 문서 후속질문("그거 다시 설명해줘", "그 문서 요약해줘" 등)을 판별하는 로직.
 *
 * 2026-09-01: 원래 PipelineController 내부 private 메서드 3개
 * (looksLikeDocumentFollowup / isVerificationFollowup / isGenericDocumentReference)로
 * 흩어져 있던 걸 이 서비스로 통합. PipelineController(1298줄)에 판별 로직이
 * 너무 많이 몰려있어 서로 다른 기준으로 판단하다 예측 불가능한 조합이 생길
 * 수 있다는 점을 정리하기 위함. 로직 자체는 변경 없이 위치만 이동.
 */
@Service
public class DocumentFollowupClassifier {

    public boolean looksLikeDocumentFollowup(String prompt) {
        String text = prompt == null
                ? ""
                : prompt.trim().toLowerCase();

        if (text.isBlank()) {
            return false;
        }

        String[] markers = {
                "거기서",
                "그 문서",
                "그 파일",
                "그 이력서",
                "그 보고서",
                "해당 문서",
                "해당 파일",
                "아까 문서",
                "아까 파일",
                "아까 올린",
                "전에 올린",
                "이 문서",
                "이 파일",
                "이거",
                "이걸",
                "그거",
                "그걸",
                "그것",
                "저거",
                "방금",
                "무슨 내용",
                "각 항목",
                "각항목",
                "항목에",
                "항목은",
        };

        return containsAnyText(text, markers);
    }

    public boolean isVerificationFollowup(String prompt) {
        String text = prompt == null
                ? ""
                : prompt.trim().toLowerCase();

        return containsAnyText(
                text,
                "확실해",
                "확실한가",
                "맞아",
                "맞나요",
                "진짜야",
                "정말이야",
                "근거 있어",
                "근거있어",
                "출처 맞아",
                "출처가 맞아",
                "다시 확인",
                "재확인");
    }

    public boolean isGenericDocumentReference(String prompt) {
        String text = prompt == null ? "" : prompt.trim().toLowerCase();

        boolean hasGenericPronoun = containsAnyText(
                text,
                "이거", "이걸", "그거", "그걸", "그것", "저거");

        return hasGenericPronoun
                && !containsAnyText(
                        text,
                        "문서", "파일", "이력서", "보고서",
                        "거기서", "아까", "전에 올린",
                        "내용", "요약", "프로젝트", "경력");
    }

    private boolean containsAnyText(String text, String... markers) {
        for (String marker : markers) {
            if (text.contains(marker)) {
                return true;
            }
        }
        return false;
    }
}
