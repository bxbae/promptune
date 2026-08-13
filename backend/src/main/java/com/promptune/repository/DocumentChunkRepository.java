package com.promptune.repository;

import com.promptune.domain.DocumentChunk;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface DocumentChunkRepository extends JpaRepository<DocumentChunk, Long> {
    List<DocumentChunk> findByDocumentId(Long documentId);
}