package com.promptune.repository;

import com.promptune.domain.CustomDocumentKeyword;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface CustomDocumentKeywordRepository extends JpaRepository<CustomDocumentKeyword, Long> {
    List<CustomDocumentKeyword> findByCompanyId(String companyId);
}