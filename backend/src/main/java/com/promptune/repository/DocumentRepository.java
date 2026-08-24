package com.promptune.repository;

import com.promptune.domain.Document;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface DocumentRepository extends JpaRepository<Document, Long> {
    List<Document> findByOwnerUserId(Long ownerUserId);
    List<Document> findByPromptSessionId(Long promptSessionId);
}
