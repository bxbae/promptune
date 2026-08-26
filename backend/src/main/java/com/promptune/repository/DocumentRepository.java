package com.promptune.repository;

import com.promptune.domain.Document;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

public interface DocumentRepository extends JpaRepository<Document, Long> {
    List<Document> findByOwnerUserId(Long ownerUserId);

    // 메서드 이름은 기존 호출부 호환을 유지하되 실제 관계는
    // prompt_session_documents(N:M) 연결 테이블에서 읽는다.
    @Query(value = """
            SELECT d.*
            FROM documents d
            JOIN prompt_session_documents psd
              ON psd.document_id = d.id
            WHERE psd.prompt_session_id = :promptSessionId
            ORDER BY psd.id ASC
            """, nativeQuery = true)
    List<Document> findByPromptSessionId(
            @Param("promptSessionId") Long promptSessionId);

    @Modifying
    @Transactional
    @Query(value = """
            INSERT INTO prompt_session_documents(prompt_session_id, document_id)
            VALUES (:promptSessionId, :documentId)
            ON CONFLICT (prompt_session_id, document_id) DO NOTHING
            """, nativeQuery = true)
    void linkPromptSessionDocument(
            @Param("promptSessionId") Long promptSessionId,
            @Param("documentId") Long documentId);
}
