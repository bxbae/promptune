package com.promptune.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;

import com.promptune.domain.Document;

public interface DocumentRepository extends JpaRepository<Document, Long> {
    List<Document> findByOwnerUserId(Long ownerUserId);

    // 히스토리 > 개인화 설정 "전체 초기화"에서 씀. S3 객체는 별도로 먼저 지워야 하므로
    // (여기서 DB row만 지우는 건) findByOwnerUserId로 목록을 먼저 가져와 S3를 정리한 뒤에 호출할 것.
    void deleteByOwnerUserId(Long ownerUserId);

    // 파일관리 화면 전용: 채팅으로 한 번이라도 실제 전송에 쓰인(prompt_session_documents에
    // 연결된) 문서는 제외하고 보여준다. 첨부만 하고 아직 전송 전인 문서는
    // 아직 이 테이블에 연결이 안 됐을 수 있어 잠깐 보일 수 있음(알려진 한계).
    @Query(value = """
            SELECT d.*
            FROM documents d
            WHERE d.owner_user_id = :ownerUserId
              AND NOT EXISTS (
                  SELECT 1 FROM prompt_session_documents psd
                  WHERE psd.document_id = d.id
              )
            ORDER BY d.id DESC
            """, nativeQuery = true)
    List<Document> findLibraryDocumentsByOwnerUserId(
            @Param("ownerUserId") Long ownerUserId);

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
