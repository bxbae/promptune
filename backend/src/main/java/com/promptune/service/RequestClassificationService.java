package com.promptune.service;

import org.springframework.stereotype.Service;

@Service
public class RequestClassificationService {

    // 회사 키워드 사전(customDocumentKeyword) 로직 제거됨 — 관리자 개념이 없어져 채울 방법이 없던
    // 보조 조건이었음. 핵심 판단(업무유형이 _internal/application이면 필요)은 AI 진단 결과로 이미 충분.
    public boolean needsInternalDocs(boolean aiJudgment) {
        return aiJudgment;
    }
}
