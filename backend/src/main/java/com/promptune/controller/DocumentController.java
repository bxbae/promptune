package com.promptune.controller;

import com.promptune.domain.Document;
import com.promptune.domain.DocumentChunk;
import com.promptune.domain.User;
import com.promptune.dto.DocumentDtos.UploadDocumentRequest;
import com.promptune.dto.DocumentDtos.UpdateDocumentRequest;
import com.promptune.repository.DocumentRepository;
import com.promptune.repository.DocumentChunkRepository;
import com.promptune.repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
@RequestMapping("/api/documents")
public class DocumentController {

    private final DocumentRepository documentRepository;
    private final DocumentChunkRepository documentChunkRepository;
    private final UserRepository userRepository;

    public DocumentController(DocumentRepository documentRepository,
                               DocumentChunkRepository documentChunkRepository,
                               UserRepository userRepository) {
        this.documentRepository = documentRepository;
        this.documentChunkRepository = documentChunkRepository;
        this.userRepository = userRepository;
    }

    @PostMapping
    public Document upload(@RequestBody UploadDocumentRequest req, Authentication authentication) {
        User user = currentUser(authentication);
        String tag = (req.tag() == null || req.tag().isBlank()) ? "일반" : req.tag();

        Document document = documentRepository.save(
                new Document(user.getId(), req.title(), tag, null, req.fileType()));

        // 임시: 청크 분할 없이 전체를 chunk 1개로 저장 (embedding은 비어있음)
        // 실제 청크 분할·임베딩 생성 로직으로 교체 필요
        documentChunkRepository.save(new DocumentChunk(document.getId(), 0, req.content()));

        return document;
    }

    @GetMapping
    public List<Document> myDocuments(Authentication authentication) {
        User user = currentUser(authentication);
        return documentRepository.findByOwnerUserId(user.getId());
    }

    @PatchMapping("/{id}")
    public Document update(@PathVariable Long id, @RequestBody UpdateDocumentRequest req, Authentication authentication) {
        User user = currentUser(authentication);
        Document document = documentRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "문서를 찾을 수 없습니다."));

        if (!document.getOwnerUserId().equals(user.getId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "본인 문서만 수정할 수 있습니다.");
        }

        // 제목·태그는 Document 자체를 그냥 고침 (조각 재분할 대상 아님)
        if (req.title() != null) document.setTitle(req.title());
        if (req.tag() != null) document.setTag(req.tag());

        // 참고: 이번 UpdateDocumentRequest는 title/tag만 받습니다.
        // 내용(content) 수정은 별도 API로 분리 예정
        // chunker.py 로직으로 다시 300~500자 단위로 쪼개서
        // documentChunkRepository.deleteAll(documentChunkRepository.findByDocumentId(id));
        // (재분할된 조각들을 chunk_index 0,1,2... 순서로 다시 저장)
        // 실제 재분할·재임베딩 연동 방식 확정 필요

        return documentRepository.save(document);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> delete(@PathVariable Long id, Authentication authentication) {
        User user = currentUser(authentication);
        Document document = documentRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "문서를 찾을 수 없습니다."));

        if (!document.getOwnerUserId().equals(user.getId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "본인 문서만 삭제할 수 있습니다.");
        }

        documentRepository.deleteById(id);  // document_chunks는 ON DELETE CASCADE로 자동 같이 삭제됨
        return ResponseEntity.ok().build();
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }
}
