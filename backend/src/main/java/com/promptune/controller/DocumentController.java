package com.promptune.controller;

import com.promptune.domain.Document;
import com.promptune.domain.User;
import com.promptune.dto.DocumentDtos.UpdateDocumentRequest;
import com.promptune.repository.DocumentRepository;
import com.promptune.repository.UserRepository;
import com.promptune.service.S3StorageService;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Locale;

@RestController
@RequestMapping("/api/documents")
public class DocumentController {

    private final DocumentRepository documentRepository;
    private final UserRepository userRepository;
    private final S3StorageService s3StorageService;

    public DocumentController(DocumentRepository documentRepository,
                               UserRepository userRepository,
                               S3StorageService s3StorageService) {
        this.documentRepository = documentRepository;
        this.userRepository = userRepository;
        this.s3StorageService = s3StorageService;
    }

    // 실제 파일을 받아 S3(promptune-document 버킷)에 업로드하고, 메타데이터를 DB에 저장한다.
    // 내용(텍스트) 추출·청크 분할·임베딩 생성은 아직 이 단계의 범위가 아니라서
    // document_chunks는 생성하지 않는다 (추후 파싱 파이프라인 연동 시 추가 예정).
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Document upload(@RequestParam("file") MultipartFile file,
                            @RequestParam("title") String title,
                            @RequestParam(value = "tag", required = false) String tag,
                            Authentication authentication) {
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "파일이 비어있습니다.");
        }

        User user = currentUser(authentication);
        String resolvedTag = (tag == null || tag.isBlank()) ? "일반" : tag;
        String resolvedTitle = (title == null || title.isBlank())
                ? file.getOriginalFilename()
                : title;
        String fileType = extractExtension(file.getOriginalFilename());

        String s3Key = s3StorageService.uploadDocument(user.getId(), file);

        Document document = documentRepository.save(
                new Document(user.getId(), resolvedTitle, resolvedTag, s3Key, fileType));

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
        s3StorageService.delete(document.getS3Key());  // S3 객체도 같이 정리
        return ResponseEntity.ok().build();
    }

    private User currentUser(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."));
    }

    private String extractExtension(String filename) {
        if (filename == null) return null;
        int dot = filename.lastIndexOf('.');
        if (dot < 0 || dot == filename.length() - 1) return null;
        return filename.substring(dot + 1).toLowerCase(Locale.ROOT);
    }
}
