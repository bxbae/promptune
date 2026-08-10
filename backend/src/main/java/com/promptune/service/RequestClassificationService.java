package com.promptune.service;

import com.promptune.domain.CustomDocumentKeyword;
import com.promptune.repository.CustomDocumentKeywordRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class RequestClassificationService {

    @Autowired
    private CustomDocumentKeywordRepository keywordRepository;

    public boolean needsInternalDocs(boolean aiJudgment, String userPrompt, String companyId) {
        if (aiJudgment) return true;
        return keywordRepository.findByCompanyId(companyId).stream()
                .map(CustomDocumentKeyword::getKeyword)
                .anyMatch(userPrompt::contains);
    }
}